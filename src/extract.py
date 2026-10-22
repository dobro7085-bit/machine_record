"""키워드 매칭(추출) 모듈.

생산팀 셀/SMES 행의 자유텍스트를 조각으로 분리하고, part_keywords.csv 규칙으로
마스터 34항목 중 하나로 매칭한다. 매칭 방식은 token_and(토큰 모두 포함 + require_token).
매칭 실패하지만 '교체'를 포함한 조각은 UnmatchedFragment 로 수집한다(형명/금형 제외).
"""
from __future__ import annotations

import re

from src.config import Config, KeywordRule, _norm
from src.load_prod import ProdCell
from src.load_smes import SmesRow
from src.models import ReplacementEvent, UnmatchedFragment

_SPLIT_RE = re.compile(r"[\n,/]")


def split_fragments(text: str) -> list[str]:
    return [p.strip() for p in _SPLIT_RE.split(text) if p.strip()]


def _group_matches(norm_text: str, group: tuple[str, ...]) -> bool:
    return all(token in norm_text for token in group)


def match_item(fragment: str, config: Config) -> str | None:
    """조각 → 마스터 항목명. 매칭 없으면 None.

    토큰 AND 매칭 + require_token 공통 요구. 여러 항목이 매칭되면
    include 그룹 토큰 수가 많은(더 구체적인) 항목을 우선한다.
    (예: '호퍼 베어링 교체' → 호퍼+베어링 2토큰 항목이 호퍼 1토큰 항목보다 우선)
    """
    norm_text = _norm(fragment)
    if config.require_token_norm and config.require_token_norm not in norm_text:
        return None
    if any(marker in norm_text for marker in config.mold_markers_norm):
        return None

    candidates: list[tuple[int, KeywordRule]] = []
    for rule in config.keyword_rules:
        if any(exc in norm_text for exc in rule.exclude_keywords):
            continue
        matched_group = next(
            (g for g in rule.include_groups if _group_matches(norm_text, g)), None
        )
        if matched_group is not None:
            candidates.append((len(matched_group), rule))

    if not candidates:
        return None
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[0][1].master_item


def is_mold_change(fragment: str, config: Config) -> bool:
    norm_text = _norm(fragment)
    return any(marker in norm_text for marker in config.mold_markers_norm)


def extract_prod(
    cells: list[ProdCell], config: Config
) -> tuple[list[ReplacementEvent], list[UnmatchedFragment]]:
    events: list[ReplacementEvent] = []
    unmatched: list[UnmatchedFragment] = []
    for cell in cells:
        for fragment in split_fragments(cell.raw_text):
            item = match_item(fragment, config)
            if item is not None:
                events.append(
                    ReplacementEvent(
                        date=cell.date,
                        standard_line=cell.standard_line,
                        master_item=item,
                        raw_text=fragment,
                        source="생산팀",
                    )
                )
            elif config.require_token in fragment and not is_mold_change(fragment, config):
                unmatched.append(
                    UnmatchedFragment(
                        source="생산팀",
                        date=cell.date,
                        standard_line=cell.standard_line,
                        raw_text=fragment,
                    )
                )
    return events, unmatched


def extract_smes(
    rows: list[SmesRow], config: Config
) -> tuple[list[ReplacementEvent], list[UnmatchedFragment]]:
    events: list[ReplacementEvent] = []
    unmatched: list[UnmatchedFragment] = []
    for row in rows:
        item = match_item(row.combined_text, config)
        if item is not None:
            events.append(
                ReplacementEvent(
                    date=row.date,
                    standard_line=row.standard_line,
                    master_item=item,
                    raw_text=row.combined_text,
                    source="전산",
                )
            )
        elif config.require_token in row.combined_text and not is_mold_change(
            row.combined_text, config
        ):
            unmatched.append(
                UnmatchedFragment(
                    source="전산",
                    date=row.date,
                    standard_line=row.standard_line,
                    raw_text=row.combined_text,
                )
            )
    return events, unmatched
