from __future__ import annotations

from typing import Any


TOKEN_USAGE_BUCKETS: tuple[str, ...] = (
    "controller",
    "executor",
    "reply",
    "failure_analysis",
    "context_compression",
    "history_rollup",
)


def _empty_bucket_summary() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "call_count": 0,
        "calls_with_usage": 0,
        "calls_without_usage": 0,
    }


def empty_token_usage_summary() -> dict[str, Any]:
    by_bucket = {bucket: _finalize_bucket_summary(_empty_bucket_summary()) for bucket in TOKEN_USAGE_BUCKETS}
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "call_count": 0,
        "calls_with_usage": 0,
        "calls_without_usage": 0,
        "is_complete": True,
        "by_bucket": by_bucket,
    }


def _coerce_usage_summary(payload: Any) -> dict[str, Any]:
    data = _as_mapping(payload)
    if data is None:
        return empty_token_usage_summary()

    out = empty_token_usage_summary()
    out["input_tokens"] = int(_safe_int(data.get("input_tokens")) or 0)
    out["output_tokens"] = int(_safe_int(data.get("output_tokens")) or 0)
    out["total_tokens"] = int(_safe_int(data.get("total_tokens")) or 0)
    out["call_count"] = int(_safe_int(data.get("call_count")) or 0)
    out["calls_with_usage"] = int(_safe_int(data.get("calls_with_usage")) or 0)
    out["calls_without_usage"] = int(_safe_int(data.get("calls_without_usage")) or 0)

    by_bucket = _as_mapping(data.get("by_bucket"))
    if by_bucket is None:
        return out

    out_by_bucket = out.get("by_bucket", {})
    if not isinstance(out_by_bucket, dict):
        out_by_bucket = {}
        out["by_bucket"] = out_by_bucket

    for bucket in TOKEN_USAGE_BUCKETS:
        raw_bucket = _as_mapping(by_bucket.get(bucket))
        if raw_bucket is None:
            continue
        out_by_bucket[bucket] = {
            "input_tokens": int(_safe_int(raw_bucket.get("input_tokens")) or 0),
            "output_tokens": int(_safe_int(raw_bucket.get("output_tokens")) or 0),
            "total_tokens": int(_safe_int(raw_bucket.get("total_tokens")) or 0),
            "call_count": int(_safe_int(raw_bucket.get("call_count")) or 0),
            "calls_with_usage": int(_safe_int(raw_bucket.get("calls_with_usage")) or 0),
            "calls_without_usage": int(_safe_int(raw_bucket.get("calls_without_usage")) or 0),
            "is_complete": int(_safe_int(raw_bucket.get("calls_without_usage")) or 0) == 0,
        }
    return out


def merge_token_usage_summary(base: Any, delta: Any) -> dict[str, Any]:
    left = _coerce_usage_summary(base)
    right = _coerce_usage_summary(delta)
    merged = empty_token_usage_summary()

    for field in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "call_count",
        "calls_with_usage",
        "calls_without_usage",
    ):
        merged[field] = int(left.get(field, 0) or 0) + int(right.get(field, 0) or 0)
    merged["is_complete"] = int(merged.get("calls_without_usage", 0) or 0) == 0

    merged_by_bucket = merged.get("by_bucket", {})
    left_by_bucket = left.get("by_bucket", {})
    right_by_bucket = right.get("by_bucket", {})
    if not isinstance(merged_by_bucket, dict):
        merged_by_bucket = {}
        merged["by_bucket"] = merged_by_bucket

    for bucket in TOKEN_USAGE_BUCKETS:
        left_bucket = _as_mapping(left_by_bucket.get(bucket)) if isinstance(left_by_bucket, dict) else None
        right_bucket = _as_mapping(right_by_bucket.get(bucket)) if isinstance(right_by_bucket, dict) else None
        bucket_summary = {}
        for field in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "call_count",
            "calls_with_usage",
            "calls_without_usage",
        ):
            bucket_summary[field] = int((left_bucket or {}).get(field, 0) or 0) + int((right_bucket or {}).get(field, 0) or 0)
        bucket_summary["is_complete"] = int(bucket_summary.get("calls_without_usage", 0) or 0) == 0
        merged_by_bucket[bucket] = bucket_summary

    return merged


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, int(value))
    except Exception:
        return None


def _as_mapping(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if payload is None:
        return None
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump()
        except Exception:
            dumped = None
        if isinstance(dumped, dict):
            return dumped
    as_dict = getattr(payload, "dict", None)
    if callable(as_dict):
        try:
            dumped = as_dict()
        except Exception:
            dumped = None
        if isinstance(dumped, dict):
            return dumped
    raw = getattr(payload, "__dict__", None)
    if isinstance(raw, dict):
        return raw
    return None


def normalize_usage_payload(payload: Any) -> dict[str, int] | None:
    data = _as_mapping(payload)
    if data is None:
        return None

    input_tokens = _safe_int(data.get("input_tokens", data.get("prompt_tokens")))
    output_tokens = _safe_int(data.get("output_tokens", data.get("completion_tokens")))
    total_tokens = _safe_int(data.get("total_tokens"))

    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    if input_tokens is None and total_tokens is not None and output_tokens is not None:
        input_tokens = max(0, total_tokens - output_tokens)
    if output_tokens is None and total_tokens is not None and input_tokens is not None:
        output_tokens = max(0, total_tokens - input_tokens)

    return {
        "input_tokens": input_tokens or 0,
        "output_tokens": output_tokens or 0,
        "total_tokens": total_tokens or 0,
    }


def extract_token_usage(response: Any) -> dict[str, int] | None:
    usage = normalize_usage_payload(getattr(response, "usage_metadata", None))
    if usage is not None:
        return usage

    response_metadata = _as_mapping(getattr(response, "response_metadata", None))
    if response_metadata is not None:
        usage = normalize_usage_payload(response_metadata.get("token_usage"))
        if usage is not None:
            return usage
        usage = normalize_usage_payload(response_metadata.get("usage"))
        if usage is not None:
            return usage

    usage = normalize_usage_payload(getattr(response, "usage", None))
    if usage is not None:
        return usage

    return None


def _finalize_bucket_summary(summary: dict[str, int]) -> dict[str, int | bool]:
    return {
        "input_tokens": int(summary.get("input_tokens", 0) or 0),
        "output_tokens": int(summary.get("output_tokens", 0) or 0),
        "total_tokens": int(summary.get("total_tokens", 0) or 0),
        "call_count": int(summary.get("call_count", 0) or 0),
        "calls_with_usage": int(summary.get("calls_with_usage", 0) or 0),
        "calls_without_usage": int(summary.get("calls_without_usage", 0) or 0),
        "is_complete": int(summary.get("calls_without_usage", 0) or 0) == 0,
    }


class TokenUsageRecorder:
    def __init__(self) -> None:
        self._bucket_summaries: dict[str, dict[str, int]] = {
            bucket: _empty_bucket_summary() for bucket in TOKEN_USAGE_BUCKETS
        }

    def record_response(self, *, bucket: str, response: Any) -> dict[str, int] | None:
        if bucket not in self._bucket_summaries:
            raise ValueError(f"unsupported token usage bucket: {bucket}")

        summary = self._bucket_summaries[bucket]
        summary["call_count"] += 1

        usage = extract_token_usage(response)
        if usage is None:
            summary["calls_without_usage"] += 1
            return None

        summary["calls_with_usage"] += 1
        summary["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
        summary["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
        summary["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
        return usage

    def summary(self) -> dict[str, Any]:
        out = empty_token_usage_summary()
        by_bucket: dict[str, dict[str, int | bool]] = {}

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        call_count = 0
        calls_with_usage = 0
        calls_without_usage = 0

        for bucket in TOKEN_USAGE_BUCKETS:
            bucket_summary = _finalize_bucket_summary(self._bucket_summaries[bucket])
            by_bucket[bucket] = bucket_summary
            input_tokens += int(bucket_summary["input_tokens"])
            output_tokens += int(bucket_summary["output_tokens"])
            total_tokens += int(bucket_summary["total_tokens"])
            call_count += int(bucket_summary["call_count"])
            calls_with_usage += int(bucket_summary["calls_with_usage"])
            calls_without_usage += int(bucket_summary["calls_without_usage"])

        out.update(
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "call_count": call_count,
                "calls_with_usage": calls_with_usage,
                "calls_without_usage": calls_without_usage,
                "is_complete": calls_without_usage == 0,
                "by_bucket": by_bucket,
            }
        )
        return out


def invoke_with_usage(
    *,
    llm: Any,
    messages: Any,
    config: dict[str, Any] | None = None,
    usage_recorder: TokenUsageRecorder | None = None,
    bucket: str,
) -> Any:
    response = llm.invoke(messages, config=config)
    if usage_recorder is not None:
        usage_recorder.record_response(bucket=bucket, response=response)
    return response
