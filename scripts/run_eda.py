# scripts/run_eda.py
"""
Entry script to run EDA.

This script assumes:
- src layout is used
- package is installed in editable mode: pip install -e .
- core logic lives in extract_rain_to_excel.eda (run_eda)

Run from project root:
    python scripts/run_eda.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EDA for forecast rainfall vs 30-year normal"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.yaml",
        help="Path to config YAML (default: configs/config.yaml)",
    )
    parser.add_argument(
        "--init-month",
        type=str,
        default=None,
        help="Override run.init_month (YYYYMM)",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency: PyYAML. Install with `pip install pyyaml`"
        ) from e

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise RuntimeError(f"Config root must be a mapping/dict: {path}")

    return data


def apply_overrides(cfg: Dict[str, Any], init_month: str | None) -> None:
    if init_month:
        run_cfg = cfg.setdefault("run", {})
        if not isinstance(run_cfg, dict):
            raise RuntimeError("config.run must be a mapping/dict")
        run_cfg["init_month"] = init_month


def main() -> int:
    print("RUN_EDA SCRIPT STARTED")

    args = parse_args()

    try:
        cfg = load_yaml(Path(args.config))
        apply_overrides(cfg, args.init_month)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    run_cfg = cfg.get("run", {})
    init_month = run_cfg.get("init_month") if isinstance(run_cfg, dict) else None

    out_cfg = cfg.get("output", {})
    eda_dir = Path(out_cfg.get("eda_dir", "outputs/eda"))
    eda_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] EDA runner starting")
    print(f"[INFO] Config     : {Path(args.config).resolve()}")
    print(f"[INFO] init_month: {init_month}")
    print(f"[INFO] Output dir : {eda_dir.resolve()}")

    # ---- import core EDA logic (must exist!)
    try:
        from extract_rain_to_excel.eda import run_eda
    except Exception as e:
        print(
            "[ERROR] Failed to import run_eda from extract_rain_to_excel.eda\n"
            "Check that:\n"
            "  - src/extract_rain_to_excel/eda.py exists\n"
            "  - it defines: def run_eda(cfg)\n"
            "  - package is installed: pip install -e .\n"
            f"Details: {e}",
            file=sys.stderr,
        )
        return 3

    # ---- run EDA
    try:
        report_path = run_eda(cfg)
    except Exception as e:
        print(f"[ERROR] EDA failed: {e}", file=sys.stderr)
        return 4

    print(f"[INFO] EDA completed successfully")
    print(f"[INFO] Report written to: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
