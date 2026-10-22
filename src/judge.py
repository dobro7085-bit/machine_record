"""판정 모듈.

항목×호기별로 analysis_start 이후 교체 이력을 시간순으로 보며:
- 첫 교체 = '기준설정'(판정 제외),
- 이후 각 교체 = 예상일(직전교체일+주기) 대비 조기/정시/지연 판정,
- 마지막 교체 이후 --date 가 예상일+허용오차를 지났으면 '미교체'(초과 진행중) 1행 추가,
- 교체 이력이 전혀 없으면 '기록없음' 1행.
baseline_override 가 있으면 데이터상 첫 교체일보다 우선한다.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from src.config import Config
from src.load_master import MasterRow
from src.models import MergedEvent

VERDICT_EARLY = "조기"
VERDICT_ONTIME = "정시"
VERDICT_LATE = "지연"
VERDICT_NOT_REPLACED = "미교체"
VERDICT_BASELINE = "기준설정"
VERDICT_NO_RECORD = "기록없음"

COMPLIANT = {VERDICT_EARLY, VERDICT_ONTIME}
NON_COMPLIANT = {VERDICT_LATE, VERDICT_NOT_REPLACED}
EXCLUDED_FROM_RATE = {VERDICT_BASELINE, VERDICT_NO_RECORD}


@dataclass
class Judgement:
    standard_line: str
    process: str
    master_item: str
    grade: str
    cycle_days: int
    prev_date: dt.date | None
    expected_date: dt.date | None
    actual_date: dt.date | None
    deviation_days: int | None
    verdict: str
    source: str
    need_check: str
    raw_text: str


def _tolerance(grade: str, config: Config) -> int:
    return config.tolerance_days.get(grade, max(config.tolerance_days.values(), default=0))


def judge(
    master_rows: list[MasterRow],
    merged: list[MergedEvent],
    as_of: dt.date,
    config: Config,
) -> list[Judgement]:
    events_by_key: dict[tuple[str, str], list[MergedEvent]] = {}
    for ev in merged:
        if ev.date < config.analysis_start:
            continue
        events_by_key.setdefault((ev.standard_line, ev.master_item), []).append(ev)

    results: list[Judgement] = []
    for mrow in master_rows:
        key = (mrow.standard_line, mrow.item)
        tol = _tolerance(mrow.grade, config)
        events = sorted(events_by_key.get(key, []), key=lambda e: e.date)

        override = config.baseline_override.get(key)
        if override is not None:
            events = [e for e in events if e.date >= override]

        if not events and override is None:
            results.append(
                _no_record(mrow)
            )
            continue

        prev_date: dt.date | None = override
        for i, ev in enumerate(events):
            if i == 0 and override is None:
                results.append(_baseline(mrow, ev))
                prev_date = ev.date
                continue
            expected = prev_date + dt.timedelta(days=mrow.cycle_days) if prev_date else None
            deviation = (ev.date - expected).days if expected else None
            verdict = _classify(deviation, tol, config)
            results.append(
                Judgement(
                    standard_line=mrow.standard_line,
                    process=mrow.process,
                    master_item=mrow.item,
                    grade=mrow.grade,
                    cycle_days=mrow.cycle_days,
                    prev_date=prev_date,
                    expected_date=expected,
                    actual_date=ev.date,
                    deviation_days=deviation,
                    verdict=verdict,
                    source=ev.source,
                    need_check="Y" if ev.need_check else "",
                    raw_text=ev.raw_text,
                )
            )
            prev_date = ev.date

        _append_overdue_if_any(results, mrow, prev_date, as_of, tol, config)

    return results


def _classify(deviation: int | None, tol: int, config: Config) -> str:
    if deviation is None:
        return VERDICT_BASELINE
    if deviation < -tol:
        return VERDICT_EARLY
    if deviation > tol:
        return VERDICT_LATE
    return VERDICT_ONTIME


def _append_overdue_if_any(
    results: list[Judgement],
    mrow: MasterRow,
    prev_date: dt.date | None,
    as_of: dt.date,
    tol: int,
    config: Config,
) -> None:
    if prev_date is None:
        return
    expected = prev_date + dt.timedelta(days=mrow.cycle_days)
    if as_of > expected + dt.timedelta(days=tol):
        results.append(
            Judgement(
                standard_line=mrow.standard_line,
                process=mrow.process,
                master_item=mrow.item,
                grade=mrow.grade,
                cycle_days=mrow.cycle_days,
                prev_date=prev_date,
                expected_date=expected,
                actual_date=None,
                deviation_days=(as_of - expected).days,
                verdict=VERDICT_NOT_REPLACED,
                source="",
                need_check="",
                raw_text="",
            )
        )


def _baseline(mrow: MasterRow, ev: MergedEvent) -> Judgement:
    return Judgement(
        standard_line=mrow.standard_line,
        process=mrow.process,
        master_item=mrow.item,
        grade=mrow.grade,
        cycle_days=mrow.cycle_days,
        prev_date=None,
        expected_date=None,
        actual_date=ev.date,
        deviation_days=None,
        verdict=VERDICT_BASELINE,
        source=ev.source,
        need_check="Y" if ev.need_check else "",
        raw_text=ev.raw_text,
    )


def _no_record(mrow: MasterRow) -> Judgement:
    return Judgement(
        standard_line=mrow.standard_line,
        process=mrow.process,
        master_item=mrow.item,
        grade=mrow.grade,
        cycle_days=mrow.cycle_days,
        prev_date=None,
        expected_date=None,
        actual_date=None,
        deviation_days=None,
        verdict=VERDICT_NO_RECORD,
        source="",
        need_check="",
        raw_text="",
    )
