"""병합 ±1일 경계 및 같은날 중복 축약 테스트."""
from __future__ import annotations

import datetime as dt

from src.merge import merge_events
from src.models import ReplacementEvent
from tests.conftest import make_config


def _ev(date, source, item="칼날 교체", line="CP1"):
    return ReplacementEvent(date, line, item, f"{source}-raw", source)


def test_merge_within_window_is_both():
    config = make_config(merge_window_days=1)
    prod = [_ev(dt.date(2026, 9, 10), "생산팀")]
    smes = [_ev(dt.date(2026, 9, 11), "전산")]
    merged = merge_events(prod, smes, config)
    assert len(merged) == 1
    assert merged[0].source == "양쪽"
    assert merged[0].date == dt.date(2026, 9, 11)  # 전산 발생일자 우선
    assert merged[0].need_check is False


def test_merge_outside_window_stays_separate():
    config = make_config(merge_window_days=1)
    prod = [_ev(dt.date(2026, 9, 10), "생산팀")]
    smes = [_ev(dt.date(2026, 9, 12), "전산")]
    merged = merge_events(prod, smes, config)
    assert len(merged) == 2
    assert {m.source for m in merged} == {"생산팀", "전산"}
    assert all(m.need_check for m in merged)


def test_same_day_same_item_collapsed():
    config = make_config()
    prod = [
        _ev(dt.date(2026, 9, 10), "생산팀"),
        _ev(dt.date(2026, 9, 10), "생산팀"),
    ]
    merged = merge_events(prod, [], config)
    assert len(merged) == 1


def test_single_source_marks_need_check():
    config = make_config()
    merged = merge_events([_ev(dt.date(2026, 9, 10), "생산팀")], [], config)
    assert merged[0].need_check is True
    assert merged[0].source == "생산팀"
