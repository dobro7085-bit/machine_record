"""CLI 진입점.

실행 예:
  python -m src.main --date 2026-10-22 --prod data/01.xlsx --smes data/smes/ --master data/03.xlsx
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from src.config import load_config
from src.export import export_result
from src.extract import extract_prod, extract_smes
from src.judge import judge
from src.load_master import load_master
from src.load_prod import load_prod
from src.load_smes import load_smes
from src.merge import merge_events


def _build_coverage(prod_events, smes_events, config) -> dict:
    coverage: dict = {}
    prod_dates = [e.date for e in prod_events if e.date >= config.analysis_start]
    smes_dates = [e.date for e in smes_events if e.date >= config.analysis_start]
    coverage["생산팀"] = {
        "start": min(prod_dates) if prod_dates else None,
        "end": max(prod_dates) if prod_dates else None,
    }
    coverage["전산"] = {
        "start": min(smes_dates) if smes_dates else None,
        "end": max(smes_dates) if smes_dates else None,
    }
    p_end = coverage["생산팀"]["end"]
    s_end = coverage["전산"]["end"]
    if p_end and s_end and abs((p_end - s_end).days) >= config.coverage_gap_warn_days:
        coverage["gap_warning"] = (
            f"⚠ 경고: 두 출처 데이터 종료일 차이 {abs((p_end - s_end).days)}일 "
            f"(생산팀 {p_end.isoformat()} / 전산 {s_end.isoformat()}) — "
            f"{config.coverage_gap_warn_days}일 이상. 한쪽 소스 공백 구간 판정에 주의."
        )
    return coverage


def run(as_of: dt.date, prod_path: Path, smes_arg, master_path: Path,
        config_dir: Path, out_dir: Path) -> Path:
    config = load_config(config_dir)

    master_rows = load_master(master_path)
    prod_cells, prod_errors = load_prod(prod_path)
    smes_rows, smes_errors = load_smes(smes_arg, config)

    prod_events, prod_unmatched = extract_prod(prod_cells, config)
    smes_events, smes_unmatched = extract_smes(smes_rows, config)

    merged = merge_events(prod_events, smes_events, config)
    judgements = judge(master_rows, merged, as_of, config)

    coverage = _build_coverage(prod_events, smes_events, config)

    out_path = out_dir / f"result_{as_of.strftime('%Y%m%d')}.xlsx"
    export_result(
        out_path=out_path,
        judgements=judgements,
        master_rows=master_rows,
        unmatched=prod_unmatched + smes_unmatched,
        parse_errors=prod_errors + smes_errors,
        as_of=as_of,
        coverage=coverage,
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="세방전지 창원공장 극판(연속도장) 소모품 교체 준수 판정"
    )
    parser.add_argument("--date", required=True, help="분석 기준일 (YYYY-MM-DD)")
    parser.add_argument("--prod", required=True, type=Path, help="01 생산팀 교체이력 .xlsx")
    parser.add_argument(
        "--smes", required=True, nargs="+",
        help="02 SMES .xls 파일 또는 폴더 (복수 가능)",
    )
    parser.add_argument("--master", required=True, type=Path, help="03 소모품 교체주기 마스터 .xlsx")
    parser.add_argument("--config", type=Path, default=Path("config"), help="config 디렉터리")
    parser.add_argument("--out", type=Path, default=Path("output"), help="출력 디렉터리")
    args = parser.parse_args(argv)

    as_of = dt.date.fromisoformat(args.date)
    smes_arg = args.smes if len(args.smes) > 1 else args.smes[0]
    out_path = run(as_of, args.prod, smes_arg, args.master, args.config, args.out)
    print(f"완료: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
