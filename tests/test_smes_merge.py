"""SMES 복수 파일 병합·중복 제거 테스트 (실제 샘플 .xls 를 두 번 전달)."""
from __future__ import annotations

from src.load_smes import load_smes
from tests.conftest import make_config

SAMPLE = "data_sample/02_전산_교체이력_샘플.xls"


def test_single_file_loads():
    config = make_config()
    rows, errors = load_smes(SAMPLE, config)
    assert len(rows) > 0
    assert errors == []


def test_duplicate_files_are_deduped():
    config = make_config()
    single, _ = load_smes([SAMPLE], config)
    doubled, _ = load_smes([SAMPLE, SAMPLE], config)
    assert len(doubled) == len(single)


def test_false_report_rows_excluded():
    config = make_config()
    rows, _ = load_smes(SAMPLE, config)
    for row in rows:
        assert "오신고" not in row.combined_text or row.combined_text != "오신고"
