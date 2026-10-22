"""날짜 파싱 테스트 (생산팀 3형식, SMES ISO)."""
from __future__ import annotations

import datetime as dt

from src.load_prod import parse_prod_date
from src.load_smes import _parse_smes_date


def test_prod_date_datetime():
    assert parse_prod_date(dt.datetime(2026, 1, 2)) == dt.date(2026, 1, 2)


def test_prod_date_string_yymmdd():
    assert parse_prod_date("260401") == dt.date(2026, 4, 1)


def test_prod_date_int_yymmdd():
    assert parse_prod_date(260909) == dt.date(2026, 9, 9)


def test_prod_date_invalid_returns_none():
    assert parse_prod_date("여름 휴가") is None
    assert parse_prod_date(None) is None
    assert parse_prod_date("2026-13-40") is None


def test_smes_date_iso():
    assert _parse_smes_date("2026-10-01") == dt.date(2026, 10, 1)
    assert _parse_smes_date("총부동시간") is None
