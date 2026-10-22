"""병합 모듈.

- 같은 날 같은 (호기, 항목)이 한 출처에 2회 이상 → 1건.
- 두 출처에 ±merge_window_days 이내 동일 (호기, 항목) → 1건으로 병합(출처='양쪽', 날짜는 전산 우선).
- 한쪽만 있으면 출처='생산팀'/'전산', 확인필요='Y'.
"""
from __future__ import annotations

import datetime as dt

from src.config import Config
from src.models import MergedEvent, ReplacementEvent


def _dedup_same_day(
    events: list[ReplacementEvent],
) -> dict[tuple[str, str, dt.date], ReplacementEvent]:
    collapsed: dict[tuple[str, str, dt.date], ReplacementEvent] = {}
    for ev in events:
        key = (ev.standard_line, ev.master_item, ev.date)
        if key not in collapsed:
            collapsed[key] = ev
    return collapsed


def merge_events(
    prod_events: list[ReplacementEvent],
    smes_events: list[ReplacementEvent],
    config: Config,
) -> list[MergedEvent]:
    prod_map = _dedup_same_day(prod_events)
    smes_map = _dedup_same_day(smes_events)

    window = dt.timedelta(days=config.merge_window_days)
    merged: list[MergedEvent] = []
    used_prod: set[tuple[str, str, dt.date]] = set()

    smes_by_item: dict[tuple[str, str], list[dt.date]] = {}
    for (line, item, date) in smes_map:
        smes_by_item.setdefault((line, item), []).append(date)

    used_smes: set[tuple[str, str, dt.date]] = set()

    for (line, item, p_date), p_ev in sorted(prod_map.items()):
        candidate_dates = sorted(
            d
            for d in smes_by_item.get((line, item), [])
            if (line, item, d) not in used_smes and abs(d - p_date) <= window
        )
        if candidate_dates:
            s_date = candidate_dates[0]
            used_smes.add((line, item, s_date))
            used_prod.add((line, item, p_date))
            s_ev = smes_map[(line, item, s_date)]
            merged.append(
                MergedEvent(
                    date=s_date,  # 전산 발생일자 우선
                    standard_line=line,
                    master_item=item,
                    source="양쪽",
                    need_check=False,
                    raw_text=f"[전산] {s_ev.raw_text} || [생산팀] {p_ev.raw_text}",
                )
            )

    for key, p_ev in sorted(prod_map.items()):
        if key in used_prod:
            continue
        merged.append(
            MergedEvent(
                date=p_ev.date,
                standard_line=p_ev.standard_line,
                master_item=p_ev.master_item,
                source="생산팀",
                need_check=True,
                raw_text=p_ev.raw_text,
            )
        )

    for key, s_ev in sorted(smes_map.items()):
        if key in used_smes:
            continue
        merged.append(
            MergedEvent(
                date=s_ev.date,
                standard_line=s_ev.standard_line,
                master_item=s_ev.master_item,
                source="전산",
                need_check=True,
                raw_text=s_ev.raw_text,
            )
        )

    merged.sort(key=lambda m: (m.standard_line, m.master_item, m.date))
    return merged
