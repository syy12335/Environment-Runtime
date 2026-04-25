from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runtime_adapter import ASSETS_ROOT

ROUND_ASSETS_ROOT = ASSETS_ROOT / "post_training" / "rounds"
ROUND_MANIFEST_NAME = "round_manifest.json"


def resolve_round_assets_root(root: Path | None = None) -> Path:
    return (root or ROUND_ASSETS_ROOT).resolve()


def resolve_round_dir(*, round_id: str, root: Path | None = None) -> Path:
    normalized = str(round_id).strip()
    if not normalized:
        raise ValueError("round_id is required")
    return resolve_round_assets_root(root) / normalized


def list_round_ids(root: Path | None = None) -> list[str]:
    rounds_root = resolve_round_assets_root(root)
    if not rounds_root.exists():
        return []
    round_ids: list[str] = []
    for item in sorted(rounds_root.iterdir(), key=lambda p: p.name):
        if not item.is_dir():
            continue
        if (item / ROUND_MANIFEST_NAME).exists():
            round_ids.append(item.name)
    return round_ids


def resolve_latest_round_id(root: Path | None = None) -> str:
    round_ids = list_round_ids(root)
    if not round_ids:
        raise ValueError(
            "no prepared round found under assets/post_training/rounds; run prepare_round first"
        )
    return round_ids[-1]


def resolve_round_manifest_path(
    *,
    round_id: str | None = None,
    manifest_path: Path | None = None,
    root: Path | None = None,
) -> Path:
    if manifest_path is not None:
        path = Path(manifest_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"round manifest not found: {path}")
        return path

    effective_round_id = round_id or resolve_latest_round_id(root)
    path = resolve_round_dir(round_id=effective_round_id, root=root) / ROUND_MANIFEST_NAME
    if not path.exists():
        raise FileNotFoundError(f"round manifest not found: {path}")
    return path


def load_round_manifest(
    *,
    round_id: str | None = None,
    manifest_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    path = resolve_round_manifest_path(round_id=round_id, manifest_path=manifest_path, root=root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"round manifest must be an object: {path}")
    payload["_manifest_path"] = str(path)
    payload["_round_dir"] = str(path.parent)
    return payload


def resolve_round_asset_path(manifest: dict[str, Any], key: str) -> Path:
    assets = manifest.get("assets", {})
    if not isinstance(assets, dict):
        raise ValueError("round_manifest.assets must be a mapping")
    payload = assets.get(key)
    if not isinstance(payload, dict):
        raise ValueError(f"round manifest missing asset: {key}")
    raw_path = str(payload.get("path", "")).strip()
    if not raw_path:
        raise ValueError(f"round manifest asset {key} missing path")
    path = Path(raw_path)
    if not path.is_absolute():
        manifest_path = Path(str(manifest.get("_manifest_path", ""))).resolve()
        path = (manifest_path.parent / path).resolve()
    else:
        path = path.resolve()
    return path
