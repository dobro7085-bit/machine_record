"""02 전산(SMES 설비이상조회) 로더.

월별 복수 .xls 파일(폴더 또는 파일목록)을 모두 읽어 세로로 합치고 중복을 제거한다.
- 2행(총부동시간 합계행) 제외, 상태='오신고' 제외.
- 발생일자(YYYY-MM-DD)를 생산일로 사용. 신고시간은 날짜 계산에 쓰지 않음.
- 작업자 컬럼은 읽지 않음(개인정보).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import xlrd

from src.config import Config
from src.models import ParseError

SUMMARY_MARKER = "총부동시간"
STATUS_FALSE_REPORT = "오신고"

DEDUP_KEYS = ("발생일자", "설비코드", "신고시간", "라인정지내용")

TEXT_FIELDS = ("라인정지내용", "최종상태", "의견")


@dataclass
class SmesRow:
    date: dt.date
    standard_line: str
    equipment: str
    linecode: str
    combined_text: str


def _iter_xls_files(smes_arg: list[str] | str | Path) -> list[Path]:
    if isinstance(smes_arg, (str, Path)):
        args: list = [smes_arg]
    else:
        args = list(smes_arg)
    files: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            files.extend(sorted(p.glob("*.xls")))
        elif p.exists():
            files.append(p)
    return files


def _resolve_line(equipment: str, linecode: str, config: Config) -> str:
    if linecode in config.smes_linecode_to_line:
        return config.smes_linecode_to_line[linecode]
    if equipment in config.smes_equip_to_line:
        return config.smes_equip_to_line[equipment]
    return equipment


def load_smes(
    smes_arg: list[str] | str | Path, config: Config
) -> tuple[list[SmesRow], list[ParseError]]:
    files = _iter_xls_files(smes_arg)
    rows: list[SmesRow] = []
    errors: list[ParseError] = []
    seen: set[tuple] = set()

    for path in files:
        wb = xlrd.open_workbook(str(path))
        sheet = wb.sheet_by_index(0)
        if sheet.nrows < 2:
            continue
        header = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
        idx = {name: i for i, name in enumerate(header)}

        for key in DEDUP_KEYS + TEXT_FIELDS + ("상태", "설비명", "라인코드", "라인명"):
            if key not in idx:
                raise ValueError(
                    f"SMES 파일 '{path.name}' 헤더에 '{key}' 컬럼이 없습니다."
                )

        for r in range(1, sheet.nrows):
            def cell(name: str) -> str:
                return str(sheet.cell_value(r, idx[name])).strip()

            if cell("라인명") == SUMMARY_MARKER or cell("발생일자") == SUMMARY_MARKER:
                continue

            if cell("상태") == STATUS_FALSE_REPORT:
                continue

            date_raw = cell("발생일자")
            if date_raw == "":
                continue
            parsed = _parse_smes_date(date_raw)
            if parsed is None:
                errors.append(
                    ParseError(
                        source="전산",
                        location=f"{path.name}!row{r + 1}",
                        reason="발생일자 파싱 실패",
                        raw=date_raw,
                    )
                )
                continue

            dedup = tuple(cell(k) for k in DEDUP_KEYS)
            if dedup in seen:
                continue
            seen.add(dedup)

            equipment = cell("설비명")
            linecode = cell("라인코드")
            combined = " ".join(cell(f) for f in TEXT_FIELDS)
            rows.append(
                SmesRow(
                    date=parsed,
                    standard_line=_resolve_line(equipment, linecode, config),
                    equipment=equipment,
                    linecode=linecode,
                    combined_text=combined,
                )
            )
    return rows, errors


def _parse_smes_date(raw: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
