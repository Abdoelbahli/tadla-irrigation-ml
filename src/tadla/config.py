"""Load config.yaml and resolve repository-relative paths."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    """Read config.yaml (default: repository root)."""
    path = Path(path) if path else REPO_ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def repo_path(rel: str | Path) -> Path:
    """Absolute path for a repository-relative path from the config."""
    p = Path(rel)
    return p if p.is_absolute() else REPO_ROOT / p


def gcp_project(cfg: dict) -> str:
    """Earth Engine project id, read from .env (never hard-coded, never committed)."""
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    var = cfg["project"]["gcp_project_env"]
    value = os.environ.get(var)
    if not value:
        raise RuntimeError(f"{var} is not set (expected in {REPO_ROOT / '.env'})")
    return value
