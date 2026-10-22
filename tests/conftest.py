"""테스트 공용 픽스처: 최소 Config 를 코드로 구성."""
from __future__ import annotations

import datetime as dt

from src.config import Config, KeywordRule


def make_config(**overrides) -> Config:
    config = Config(
        analysis_start=dt.date(2026, 9, 1),
        shift_boundary_hour=8,
        tolerance_days={"A": 2, "B": 3, "C": 5},
        early_counts_as_compliant=True,
        merge_window_days=1,
        coverage_gap_warn_days=7,
        match_mode="token_and",
        require_token="교체",
        mold_change_markers=("형명", "금형"),
    )
    config.keyword_rules = [
        KeywordRule("스틸벨트 교체", (("스틸벨트",), ("스틸밸트",)), ("스크래퍼",), False),
        KeywordRule(
            "칼날 교체",
            (("칼날",), ("러그커터",), ("러그", "커터")),
            (),
            False,
        ),
        KeywordRule("호퍼 교체", (("호퍼",),), ("베어링", "청소"), False),
        KeywordRule("호퍼 베어링 교체", (("호퍼", "베어링"),), (), False),
    ]
    config.smes_equip_to_line = {"CONPASTE 1호기": "CP1"}
    config.smes_linecode_to_line = {"P1321P0001": "CP1", "P1321P0002": "CP2"}
    config.prod_label_to_line = {"CP1호": "CP1"}
    for key, value in overrides.items():
        setattr(config, key, value)
    return config
