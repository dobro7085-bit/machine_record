"""도메인 공통 데이터 구조."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass
class ReplacementEvent:
    """키워드 매칭으로 인정된 소모품 교체 1건(병합 전, 출처별 원시 이벤트)."""

    date: dt.date
    standard_line: str
    master_item: str
    raw_text: str
    source: str  # '생산팀' | '전산'


@dataclass
class MergedEvent:
    """병합 후 교체 이벤트(= 최종 판정 단위)."""

    date: dt.date
    standard_line: str
    master_item: str
    source: str  # '생산팀' | '전산' | '양쪽'
    need_check: bool
    raw_text: str


@dataclass
class ParseError:
    """날짜 파싱 실패 등으로 보류된 행."""

    source: str
    location: str
    reason: str
    raw: str


@dataclass
class UnmatchedFragment:
    """'교체'는 포함하나 마스터 어느 항목에도 매칭되지 않은 조각."""

    source: str
    date: dt.date | None
    standard_line: str
    raw_text: str
