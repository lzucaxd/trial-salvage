from __future__ import annotations

from pathlib import Path

import yaml


def load_asset_config(path: str | Path) -> dict:
    """Load an asset YAML and resolve relative file paths against the repo root."""
    path = Path(path)
    cfg = yaml.safe_load(path.read_text())
    root = _repo_root(path)
    for k, v in cfg.get("curated", {}).items():
        cfg["curated"][k] = str((root / v).resolve())
    cfg["_root"] = str(root)
    return cfg


def _repo_root(cfg_path: Path) -> Path:
    for p in [cfg_path.resolve()] + list(cfg_path.resolve().parents):
        if (p / "pyproject.toml").exists():
            return p
    return Path.cwd()
