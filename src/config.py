"""설정 로딩 모듈.

rules.yaml, equipment_alias.csv, part_keywords.csv, baseline_override.csv 를 읽어
코드 전역에서 사용할 설정 객체로 반환한다. 어떤 임계값/키워드/날짜도 코드에 하드코딩하지 않는다.
"""
from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _norm(text: str) -> str:
    """공백 제거 + 소문자화. 토큰 비교의 기준 정규화."""
    return "".join(str(text).split()).lower()


@dataclass(frozen=True)
class KeywordRule:
    """part_keywords.csv 의 한 행(= 마스터 항목 1개)."""

    master_item: str
    # include_tokens: OR 그룹들의 리스트. 각 그룹은 AND 로 묶인 토큰 리스트.
    #   예) [["칼날"], ["러그커터"], ["러그","커터"]]  => (칼날) OR (러그커터) OR (러그 AND 커터)
    include_groups: tuple[tuple[str, ...], ...]
    exclude_keywords: tuple[str, ...]
    review_needed: bool

    @property
    def max_token_count(self) -> int:
        """가장 토큰 수가 많은 그룹의 토큰 수(구체성 = 매칭 우선순위용)."""
        return max((len(g) for g in self.include_groups), default=0)


@dataclass
class Config:
    analysis_start: dt.date
    shift_boundary_hour: int
    tolerance_days: dict[str, int]
    early_counts_as_compliant: bool
    merge_window_days: int
    coverage_gap_warn_days: int
    match_mode: str
    require_token: str
    mold_change_markers: tuple[str, ...]

    keyword_rules: list[KeywordRule] = field(default_factory=list)
    smes_equip_to_line: dict[str, str] = field(default_factory=dict)
    smes_linecode_to_line: dict[str, str] = field(default_factory=dict)
    prod_label_to_line: dict[str, str] = field(default_factory=dict)
    baseline_override: dict[tuple[str, str], dt.date] = field(default_factory=dict)

    @property
    def require_token_norm(self) -> str:
        return _norm(self.require_token)

    @property
    def mold_markers_norm(self) -> tuple[str, ...]:
        return tuple(_norm(m) for m in self.mold_change_markers)


def _parse_date(value) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value).strip())


def load_rules(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_keyword_rules(path: Path) -> list[KeywordRule]:
    rules: list[KeywordRule] = []
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(_strip_comments(fh))
        for row in reader:
            item = (row.get("master_item") or "").strip()
            if not item:
                continue
            inc_raw = (row.get("include_tokens") or "").strip()
            groups: list[tuple[str, ...]] = []
            for grp in inc_raw.split("|"):
                grp = grp.strip()
                if not grp:
                    continue
                tokens = tuple(_norm(t) for t in grp.split("+") if t.strip())
                if tokens:
                    groups.append(tokens)
            exc_raw = (row.get("exclude_keywords") or "").strip()
            excludes = tuple(
                _norm(e) for e in exc_raw.split("|") if e.strip()
            )
            review = (row.get("검토필요") or "0").strip() in ("1", "true", "True")
            rules.append(
                KeywordRule(
                    master_item=item,
                    include_groups=tuple(groups),
                    exclude_keywords=excludes,
                    review_needed=review,
                )
            )
    return rules


def _strip_comments(lines):
    """'#' 로 시작하는 주석 줄과 빈 줄을 건너뛴 이터레이터.

    CSV 헤더 앞의 설명 주석을 허용하기 위함. (셀 값 안의 '#' 은 보존되어야 하므로
    줄 '시작'이 '#' 인 경우에만 주석으로 간주한다.)
    """
    for line in lines:
        stripped = line.lstrip("\ufeff")
        if stripped.startswith("#"):
            continue
        yield line


def _load_equipment_alias(path: Path, config: Config) -> None:
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(_strip_comments(fh))
        for row in reader:
            line = (row.get("standard_line") or "").strip()
            if not line:
                continue
            prod_label = (row.get("prod_label") or "").strip()
            equip = (row.get("smes_equipment") or "").strip()
            linecode = (row.get("smes_linecode") or "").strip()
            if prod_label:
                config.prod_label_to_line[prod_label] = line
            if equip:
                config.smes_equip_to_line[equip] = line
            if linecode:
                config.smes_linecode_to_line[linecode] = line


def _load_baseline_override(path: Path, config: Config) -> None:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(_strip_comments(fh))
        for row in reader:
            line = (row.get("standard_line") or "").strip()
            item = (row.get("master_item") or "").strip()
            date_raw = (row.get("baseline_date") or "").strip()
            if line and item and date_raw:
                config.baseline_override[(line, item)] = _parse_date(date_raw)


def load_config(config_dir: Path) -> Config:
    """config/ 디렉터리에서 모든 설정을 로드."""
    config_dir = Path(config_dir)
    rules = load_rules(config_dir / "rules.yaml")

    config = Config(
        analysis_start=_parse_date(rules["analysis_start"]),
        shift_boundary_hour=int(rules.get("shift_boundary_hour", 8)),
        tolerance_days={str(k): int(v) for k, v in rules["tolerance_days"].items()},
        early_counts_as_compliant=bool(rules.get("early_counts_as_compliant", True)),
        merge_window_days=int(rules.get("merge_window_days", 1)),
        coverage_gap_warn_days=int(rules.get("coverage_gap_warn_days", 7)),
        match_mode=str(rules.get("match_mode", "token_and")),
        require_token=str(rules.get("require_token", "교체")),
        mold_change_markers=tuple(rules.get("mold_change_markers", []) or []),
    )
    config.keyword_rules = _load_keyword_rules(config_dir / "part_keywords.csv")
    _load_equipment_alias(config_dir / "equipment_alias.csv", config)
    _load_baseline_override(config_dir / "baseline_override.csv", config)
    return config
