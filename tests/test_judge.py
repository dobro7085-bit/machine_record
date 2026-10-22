"""판정 6종 + 허용오차 경계값 테스트."""
from __future__ import annotations

import datetime as dt

from src.judge import (
    VERDICT_BASELINE,
    VERDICT_EARLY,
    VERDICT_LATE,
    VERDICT_NO_RECORD,
    VERDICT_NOT_REPLACED,
    VERDICT_ONTIME,
    judge,
)
from src.load_master import MasterRow
from src.models import MergedEvent
from tests.conftest import make_config


def _master(cycle=10, grade="A", line="CP1", item="칼날 교체"):
    return MasterRow(no=1, grade=grade, process="디바이더", item=item,
                     cycle_days=cycle, standard_line=line)


def _merged(date, line="CP1", item="칼날 교체", source="생산팀", need_check=True):
    return MergedEvent(date, line, item, source, need_check, "raw")


def _by_verdict(results):
    return [r.verdict for r in results]


def test_baseline_then_ontime():
    config = make_config(tolerance_days={"A": 2})
    master = [_master(cycle=10)]
    events = [_merged(dt.date(2026, 9, 1)), _merged(dt.date(2026, 9, 11))]
    results = judge(master, events, dt.date(2026, 9, 12), config)
    verdicts = _by_verdict(results)
    assert verdicts[0] == VERDICT_BASELINE
    assert VERDICT_ONTIME in verdicts


def test_early_verdict():
    config = make_config(tolerance_days={"A": 2})
    master = [_master(cycle=10)]
    # 기준 9/1, 예상 9/11, 실제 9/5 → 편차 -6 < -2 → 조기
    events = [_merged(dt.date(2026, 9, 1)), _merged(dt.date(2026, 9, 5))]
    results = judge(master, events, dt.date(2026, 9, 6), config)
    assert VERDICT_EARLY in _by_verdict(results)


def test_late_verdict():
    config = make_config(tolerance_days={"A": 2})
    master = [_master(cycle=10)]
    # 예상 9/11, 실제 9/15 → 편차 +4 > +2 → 지연
    events = [_merged(dt.date(2026, 9, 1)), _merged(dt.date(2026, 9, 15))]
    results = judge(master, events, dt.date(2026, 9, 16), config)
    assert VERDICT_LATE in _by_verdict(results)


def test_ontime_boundary():
    config = make_config(tolerance_days={"A": 2})
    master = [_master(cycle=10)]
    # 예상 9/11, 실제 9/13 → 편차 +2 == 허용오차 → 정시(경계 포함)
    events = [_merged(dt.date(2026, 9, 1)), _merged(dt.date(2026, 9, 13))]
    results = judge(master, events, dt.date(2026, 9, 14), config)
    ontime = [r for r in results if r.verdict == VERDICT_ONTIME]
    assert ontime and ontime[0].deviation_days == 2


def test_late_boundary():
    config = make_config(tolerance_days={"A": 2})
    master = [_master(cycle=10)]
    # 예상 9/11, 실제 9/14 → 편차 +3 > 2 → 지연(경계 바로 밖)
    events = [_merged(dt.date(2026, 9, 1)), _merged(dt.date(2026, 9, 14))]
    results = judge(master, events, dt.date(2026, 9, 15), config)
    assert any(r.verdict == VERDICT_LATE and r.deviation_days == 3 for r in results)


def test_not_replaced_overdue():
    config = make_config(tolerance_days={"A": 2})
    master = [_master(cycle=10)]
    # 기준 9/1 뒤 교체 없음, 예상 9/11+2=9/13 지남 → --date 9/30 → 미교체
    events = [_merged(dt.date(2026, 9, 1))]
    results = judge(master, events, dt.date(2026, 9, 30), config)
    overdue = [r for r in results if r.verdict == VERDICT_NOT_REPLACED]
    assert overdue and overdue[0].deviation_days == (dt.date(2026, 9, 30) - dt.date(2026, 9, 11)).days


def test_no_record():
    config = make_config()
    master = [_master(cycle=10)]
    results = judge(master, [], dt.date(2026, 9, 30), config)
    assert _by_verdict(results) == [VERDICT_NO_RECORD]
    assert results[0].expected_date is None


def test_pre_analysis_start_ignored():
    config = make_config()
    master = [_master(cycle=10)]
    events = [_merged(dt.date(2026, 8, 1)), _merged(dt.date(2026, 9, 1))]
    results = judge(master, events, dt.date(2026, 9, 2), config)
    # 8/1 은 analysis_start 이전 → 무시, 9/1 이 기준설정
    baselines = [r for r in results if r.verdict == VERDICT_BASELINE]
    assert baselines and baselines[0].actual_date == dt.date(2026, 9, 1)


def test_baseline_override_hook():
    config = make_config()
    config.baseline_override[("CP1", "칼날 교체")] = dt.date(2026, 9, 1)
    master = [_master(cycle=10)]
    # override 기준 9/1, 실제 교체 9/11 → 기준설정 행 없이 바로 판정
    events = [_merged(dt.date(2026, 9, 11))]
    results = judge(master, events, dt.date(2026, 9, 12), config)
    assert VERDICT_BASELINE not in _by_verdict(results)
    assert any(r.prev_date == dt.date(2026, 9, 1) for r in results)
