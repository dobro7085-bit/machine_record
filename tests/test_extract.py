"""extract(키워드 매칭) 테스트."""
from __future__ import annotations

from src.extract import match_item, split_fragments
from tests.conftest import make_config


def test_mold_change_excluded():
    config = make_config()
    assert match_item("L6H -> L3H 형명 교체", config) is None
    assert match_item("금형교체 (ESP65→ESP200)", config) is None


def test_steelbelt_scraper_excluded():
    config = make_config()
    assert match_item("스틸벨트 교체", config) == "스틸벨트 교체"
    assert match_item("스틸벨트 스크래퍼 교체", config) is None


def test_whitespace_insensitive_token_and():
    config = make_config()
    assert match_item("디바이더 좌측 칼날 2개 교체", config) == "칼날 교체"
    assert match_item("칼날교체", config) == "칼날 교체"
    assert match_item("러그 커터 교체", config) == "칼날 교체"


def test_require_token_missing_returns_none():
    config = make_config()
    assert match_item("칼날 점검", config) is None


def test_more_specific_item_wins():
    config = make_config()
    assert match_item("호퍼 베어링 이상으로 인한 호퍼 교체 완료", config) == "호퍼 베어링 교체"
    assert match_item("호퍼 교체 진행", config) == "호퍼 교체"


def test_split_fragments():
    assert split_fragments("A 교체\nB 교체, C/D") == ["A 교체", "B 교체", "C", "D"]
