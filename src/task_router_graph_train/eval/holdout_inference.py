from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

import requests

from ..dataset import read_jsonl, render_controller_prompt, write_jsonl

DEFAULT_CHART_METRICS = (
    ("semantic_pass_rate", "语义通过率"),
    ("parse_valid_rate", "解析通过率"),
    ("schema_valid_rate", "Schema 通过率"),
    ("protocol_valid_rate", "协议通过率"),
)


def build_holdout_prediction_jobs(
    *,
    record_path: Path,
    max_samples: int | None = None,
) -> list[dict[str, Any]]:
    records = read_jsonl(Path(record_path).resolve())
    jobs: list[dict[str, Any]] = []
    limit = None if max_samples is None or int(max_samples) <= 0 else int(max_samples)
    for row in records:
        sample_id = str(row.get("sample_id", "")).strip()
        state_input = row.get("state_input", {}) if isinstance(row.get("state_input", {}), dict) else {}
        if not sample_id or not state_input:
            continue
        jobs.append(
            {
                "sample_id": sample_id,
                "state_input": state_input,
                "prompt_text": render_controller_prompt(state_input),
            }
        )
        if limit is not None and len(jobs) >= limit:
            break
    return jobs


def generate_holdout_predictions(
    *,
    record_path: Path,
    output_path: Path,
    base_url: str,
    api_key_env: str,
    model: str,
    timeout_sec: float,
    max_tokens: int,
    temperature: float,
    max_samples: int | None = None,
) -> dict[str, Any]:
    resolved_output = Path(output_path).resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    jobs = build_holdout_prediction_jobs(record_path=record_path, max_samples=max_samples)
    if not jobs:
        raise ValueError(f"no holdout prediction jobs resolved from: {Path(record_path).resolve()}")

    api_key = os.environ.get(str(api_key_env).strip(), "").strip()
    if not api_key:
        raise ValueError(f"missing holdout inference API key env: {api_key_env}")

    rows: list[dict[str, Any]] = []
    for job in jobs:
        response_text = _request_openai_compatible_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            prompt_text=str(job["prompt_text"]),
            timeout_sec=float(timeout_sec),
            max_tokens=int(max_tokens),
            temperature=float(temperature),
        )
        rows.append(
            {
                "sample_id": str(job["sample_id"]),
                "response": response_text,
            }
        )

    for row in rows:
        if not str(row.get("sample_id", "")).strip():
            raise ValueError(f"prediction row missing sample_id: {resolved_output}")
    write_jsonl(resolved_output, rows)
    return {
        "record_path": str(Path(record_path).resolve()),
        "output_path": str(resolved_output),
        "model": str(model),
        "base_url": str(base_url),
        "count": len(rows),
        "max_samples": None if max_samples is None else int(max_samples),
    }


def render_metrics_summary_chart_html(
    metrics_summary: dict[str, Any],
    *,
    title: str = "Holdout Evaluation Summary",
) -> str:
    if not isinstance(metrics_summary, dict) or not metrics_summary:
        return (
            '<div style="padding:12px;border:1px solid #d0d7de;border-radius:12px;'
            'font-family:system-ui,sans-serif;">暂无可视化数据。</div>'
        )

    row_count = int(metrics_summary.get("row_count", 0) or 0)
    semantic_failed = int(metrics_summary.get("semantic_failed_count", 0) or 0)
    metric_rows = []
    for key, label in DEFAULT_CHART_METRICS:
        raw_value = metrics_summary.get(key, 0.0)
        try:
            value = max(0.0, min(1.0, float(raw_value)))
        except (TypeError, ValueError):
            value = 0.0
        metric_rows.append((key, label, value))

    svg_height = 84 + (len(metric_rows) * 54)
    bar_left = 170
    bar_width = 360
    segments: list[str] = [
        f'<div style="font-family:system-ui,sans-serif;border:1px solid #d0d7de;border-radius:16px;'
        f'padding:16px 18px;background:#fff;color:#111827;max-width:620px;">',
        f'<div style="font-size:18px;font-weight:700;margin-bottom:4px;">{html.escape(title)}</div>',
        (
            '<div style="font-size:13px;color:#4b5563;margin-bottom:12px;">'
            f'样本数 {row_count} · 未通过 {semantic_failed}'
            "</div>"
        ),
        f'<svg width="560" height="{svg_height}" viewBox="0 0 560 {svg_height}" role="img" '
        'aria-label="holdout evaluation chart">',
        '<rect x="0" y="0" width="560" height="{0}" rx="12" fill="#f8fafc"></rect>'.format(svg_height),
    ]
    for index, (_key, label, value) in enumerate(metric_rows):
        top = 34 + (index * 54)
        width = max(0.0, min(bar_width, bar_width * value))
        percent_text = f"{value * 100:.1f}%"
        segments.extend(
            [
                f'<text x="20" y="{top}" font-size="13" fill="#111827">{html.escape(label)}</text>',
                f'<rect x="{bar_left}" y="{top - 12}" width="{bar_width}" height="18" rx="9" fill="#e5e7eb"></rect>',
                f'<rect x="{bar_left}" y="{top - 12}" width="{width:.2f}" height="18" rx="9" fill="#0f766e"></rect>',
                f'<text x="{bar_left + bar_width + 12}" y="{top + 2}" font-size="12" fill="#111827">{percent_text}</text>',
            ]
        )
    segments.append("</svg></div>")
    return "".join(segments)


def _request_openai_compatible_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt_text: str,
    timeout_sec: float,
    max_tokens: int,
    temperature: float,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=float(timeout_sec),
    )
    if response.status_code >= 400:
        snippet = response.text[:300]
        raise RuntimeError(
            f"holdout inference request failed: base_url={base_url} model={model} "
            f"status={response.status_code} body={snippet}"
        )
    payload_obj = response.json()
    if not isinstance(payload_obj, dict):
        raise ValueError(f"holdout inference response must be object: {url}")
    choices = payload_obj.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"holdout inference response missing choices: {url}")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message", {}) if isinstance(first, dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    if isinstance(content, list):
        content = "\n".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content).strip()
