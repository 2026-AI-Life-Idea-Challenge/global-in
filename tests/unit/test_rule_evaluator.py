"""
tests/unit/test_rule_evaluator.py

자격조건 검토 에이전트 — 규칙 평가기 단위 테스트
DB 없이 release JSON 표현식(expression)을 직접 사용하여
evaluator.evaluate() + checker.check_eligibility()를 검증합니다.

실행:
    cd <project-root>
    pytest tests/unit/test_rule_evaluator.py -v
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# ── 프로젝트 루트를 sys.path에 추가 ─────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rules.evaluator import evaluate  # noqa: E402
from app.agent.eligibility.checker import (  # noqa: E402
    check_eligibility,
    EligibilityResult,
)
from app.agent.eligibility.fetcher import RuleSet, RequirementRecord  # noqa: E402
from app.agent.eligibility.demo_profile_schema import (  # noqa: E402
    demo_profile_ca_iec_wh_pass,
    demo_profile_ca_iec_wh_fail_funds,
    demo_profile_ca_iec_wh_unknown_insurance,
    demo_profile_au_186_de,
)


# ── 테스트 픽스처: Release JSON 로드 ────────────────────────────────────────

RELEASE_DIR = (
    PROJECT_ROOT
    / "data/processed/knowledge/20261028/releases"
    / "knowledge-v1-20261028-0e63b144b983"
)
RELEASE_JSON = RELEASE_DIR / "knowledge_release.json"


@pytest.fixture(scope="module")
def release_data() -> dict[str, Any]:
    assert RELEASE_JSON.exists(), f"Release JSON 없음: {RELEASE_JSON}"
    with open(RELEASE_JSON, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ca_iec_expressions(release_data) -> dict[str, dict]:
    """CA:iec_working_holiday 요건 ID → expression 매핑"""
    reqs = release_data["requirements"]
    return {
        r["requirement_id"]: r["expression"]
        for r in reqs
        if r.get("target", {}).get("target_id") == "CA:iec_working_holiday"
    }


@pytest.fixture(scope="module")
def au_186_de_expressions(release_data) -> dict[str, dict]:
    """AU:subclass_186_direct_entry 요건 ID → expression 매핑"""
    reqs = release_data["requirements"]
    return {
        r["requirement_id"]: r["expression"]
        for r in reqs
        if r.get("target", {}).get("target_id") == "AU:subclass_186_direct_entry"
    }


# ── helpers ──────────────────────────────────────────────────────────────────

def _eval(expression: dict, profile: dict, as_of: str = "2026-10-28") -> str:
    """evaluator.evaluate() 호출 래퍼 — outcome 문자열만 반환."""
    pending: list = []
    trusted_context = [expression, as_of, [], profile, pending]
    return evaluate(expression, profile, trusted_context)


def _make_rule_set(target_id: str, complete: bool = False) -> RuleSet:
    return RuleSet(
        rule_set_id=f"RS_{target_id}",
        target_type="PROGRAM",
        target_id=target_id,
        coverage_complete=complete,
        definition={},
        release_id="v1",
    )


def _make_req(req_id: str, target_id: str, expression: dict, judgeability: str = "conditional") -> RequirementRecord:
    return RequirementRecord(
        requirement_id=req_id,
        target_type="PROGRAM",
        target_id=target_id,
        judgeability=judgeability,
        definition=expression,
        release_id="v1",
    )


# ════════════════════════════════════════════════════════════════════════════
# 1. 개별 expression 평가 테스트
# ════════════════════════════════════════════════════════════════════════════

class TestCAIECExpressionsDirect:
    """evaluator.evaluate()를 release JSON expression으로 직접 호출."""

    def test_pol_01_pass_profile_is_unknown(self, ca_iec_expressions):
        """POL_01: 국적+여권 충족 → manual_check 자식 때문에 UNKNOWN."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_01"]
        result = _eval(expr, demo_profile_ca_iec_wh_pass())
        assert result == "UNKNOWN", (
            f"POL_01은 all 안에 manual_check 자식이 있으므로 UNKNOWN이어야 함. got={result}"
        )

    def test_pol_01_missing_nationality_is_fail(self, ca_iec_expressions):
        """POL_01: 국적 필드 없음 → contains UNKNOWN, all → UNKNOWN (not FAIL)."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_01"]
        profile = demo_profile_ca_iec_wh_pass()
        del profile["nationalities"]
        result = _eval(expr, profile)
        # 필드 누락 → UNKNOWN (evaluator는 missing field를 UNKNOWN으로 처리)
        assert result in ("UNKNOWN", "FAIL")

    def test_pol_01_non_korean_is_fail(self, ca_iec_expressions):
        """POL_01: 한국 국적 아님 → contains FAIL → all FAIL."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_01"]
        profile = demo_profile_ca_iec_wh_pass()
        profile["nationalities"] = ["US"]
        result = _eval(expr, profile)
        assert result == "FAIL", f"한국 국적 없으면 FAIL이어야 함. got={result}"

    def test_pol_02_pass_profile_is_unknown(self, ca_iec_expressions):
        """POL_02: 참여 0회 충족 → manual_check 자식 때문에 UNKNOWN."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_02"]
        result = _eval(expr, demo_profile_ca_iec_wh_pass())
        assert result == "UNKNOWN"

    def test_pol_02_over_limit_is_fail(self, ca_iec_expressions):
        """POL_02: 참여 2회 → lt(2) FAIL → all FAIL."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_02"]
        profile = demo_profile_ca_iec_wh_pass()
        profile["iec_actual_work_permit_participations"] = 2
        result = _eval(expr, profile)
        assert result == "FAIL"

    def test_pol_03_pass_profile_is_pass(self, ca_iec_expressions):
        """POL_03: 자금·항공권·은행증명서 전부 충족 → manual_check 없음 → PASS."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_03"]
        result = _eval(expr, demo_profile_ca_iec_wh_pass())
        assert result == "PASS", f"POL_03 충족 프로필은 PASS여야 함. got={result}"

    def test_pol_03_insufficient_funds_is_fail(self, ca_iec_expressions):
        """POL_03: 자금 CAD 1500 (< 2500) → FAIL."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_03"]
        result = _eval(expr, demo_profile_ca_iec_wh_fail_funds())
        assert result == "FAIL", f"자금 부족이면 FAIL. got={result}"

    def test_pol_03_no_return_ticket_or_funds_is_fail(self, ca_iec_expressions):
        """POL_03: 귀국 항공권·자금 둘 다 없음 → any FAIL → all FAIL."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_03"]
        profile = demo_profile_ca_iec_wh_pass()
        profile["return_ticket_available"] = False
        profile["separate_return_ticket_funds_available"] = False
        result = _eval(expr, profile)
        assert result == "FAIL"

    def test_pol_03_bank_statement_too_old_is_fail(self, ca_iec_expressions):
        """POL_03: 은행증명서 8일 → lte(7) FAIL → all FAIL."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_03"]
        profile = demo_profile_ca_iec_wh_pass()
        profile["bank_statement_age_days_at_departure"] = 8
        result = _eval(expr, profile)
        assert result == "FAIL"

    def test_pol_04_pass_profile_is_unknown(self, ca_iec_expressions):
        """POL_04: 보험 전부 충족 → manual_check 자식 때문에 UNKNOWN."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_04"]
        result = _eval(expr, demo_profile_ca_iec_wh_pass())
        assert result == "UNKNOWN"

    def test_pol_04_missing_insurance_fields_is_unknown(self, ca_iec_expressions):
        """POL_04: 보험 필드 없음 → UNKNOWN."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_04"]
        result = _eval(expr, demo_profile_ca_iec_wh_unknown_insurance())
        assert result == "UNKNOWN"

    def test_pol_05_is_unknown(self, ca_iec_expressions):
        """POL_05: manual_check → 항상 UNKNOWN."""
        expr = ca_iec_expressions["REVIEW:POLICY:CA_IEC_WH_POL_05"]
        result = _eval(expr, demo_profile_ca_iec_wh_pass())
        assert result == "UNKNOWN"


class TestAU186DEExpressionsDirect:
    """AU subclass_186_direct_entry POL_06 age_range 테스트."""

    def test_pol_06_young_applicant_is_pass(self, au_186_de_expressions):
        """POL_06: 1990년생 → 36세 → age_range(0~44) PASS → any PASS."""
        expr = au_186_de_expressions["REVIEW:POLICY:AU_186_DE_POL_06"]
        result = _eval(expr, demo_profile_au_186_de())
        assert result == "PASS", f"44세 이하면 PASS. got={result}"

    def test_pol_06_boundary_44_is_pass(self, au_186_de_expressions):
        """POL_06: 정확히 44세(경계) → PASS."""
        expr = au_186_de_expressions["REVIEW:POLICY:AU_186_DE_POL_06"]
        profile = {"date_of_birth": "1982-10-28", "application_date": "2026-10-28"}
        result = _eval(expr, profile)
        assert result == "PASS"

    def test_pol_06_over_45_is_unknown(self, au_186_de_expressions):
        """POL_06: 45세 초과 → age_range FAIL, manual_check UNKNOWN → any UNKNOWN."""
        expr = au_186_de_expressions["REVIEW:POLICY:AU_186_DE_POL_06"]
        profile = {"date_of_birth": "1980-01-01", "application_date": "2026-10-28"}
        result = _eval(expr, profile)
        # any: FAIL+UNKNOWN → UNKNOWN (manual_check 면제 가능성)
        assert result in ("UNKNOWN", "FAIL")


# ════════════════════════════════════════════════════════════════════════════
# 2. check_eligibility() end-to-end 테스트 (DB 없이 mock RuleSet/Requirement)
# ════════════════════════════════════════════════════════════════════════════

class TestCheckEligibilityCAIEC:
    """check_eligibility()로 CA IEC WH 전체 파이프라인 검증."""

    @pytest.fixture(scope="class")
    def ca_iec_reqs(self, ca_iec_expressions):
        return [
            _make_req(req_id, "CA:iec_working_holiday", expr)
            for req_id, expr in ca_iec_expressions.items()
        ]

    @pytest.fixture(scope="class")
    def rule_set(self):
        return _make_rule_set("CA:iec_working_holiday", complete=False)

    def test_pass_profile_overall_unknown(self, rule_set, ca_iec_reqs):
        """충족 프로필도 manual_check 요건 때문에 overall=UNKNOWN."""
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=demo_profile_ca_iec_wh_pass(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == "UNKNOWN"
        assert result.target_id == "CA:iec_working_holiday"
        # POL_03만 PASS
        pol03 = next(r for r in result.requirements if "POL_03" in r.requirement_id)
        assert pol03.outcome == "PASS"

    def test_fail_funds_overall_fail(self, rule_set, ca_iec_reqs):
        """자금 부족 프로필 → POL_03 FAIL → overall FAIL."""
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=demo_profile_ca_iec_wh_fail_funds(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == "FAIL"
        pol03 = next(r for r in result.requirements if "POL_03" in r.requirement_id)
        assert pol03.outcome == "FAIL"

    def test_unknown_insurance_overall_unknown(self, rule_set, ca_iec_reqs):
        """보험 정보 없음 → POL_04 UNKNOWN → overall UNKNOWN."""
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=demo_profile_ca_iec_wh_unknown_insurance(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == "UNKNOWN"

    def test_missing_info_populated_when_unknown(self, rule_set, ca_iec_reqs):
        """UNKNOWN 요건의 pending_reviews가 missing_info_reviews에 포함됨."""
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=demo_profile_ca_iec_wh_pass(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert len(result.missing_info_reviews) > 0, "UNKNOWN 요건의 pending_reviews 누락"

    def test_non_korean_national_overall_fail(self, rule_set, ca_iec_reqs):
        """미국 국적 → POL_01 FAIL → overall FAIL."""
        profile = demo_profile_ca_iec_wh_pass()
        profile["nationalities"] = ["US"]
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == "FAIL"


class TestCheckEligibilityAU186DE:
    """check_eligibility()로 AU 186 DE POL_06 파이프라인 검증."""

    @pytest.fixture(scope="class")
    def au_186_reqs(self, au_186_de_expressions):
        return [
            _make_req(req_id, "AU:subclass_186_direct_entry", expr)
            for req_id, expr in au_186_de_expressions.items()
        ]

    @pytest.fixture(scope="class")
    def rule_set(self):
        return _make_rule_set("AU:subclass_186_direct_entry", complete=False)

    def test_young_applicant_overall_unknown(self, rule_set, au_186_reqs):
        """44세 이하 → POL_06 PASS, 나머지 manual_check → overall UNKNOWN."""
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=au_186_reqs,
            profile=demo_profile_au_186_de(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == "UNKNOWN"
        pol06 = next(r for r in result.requirements if "POL_06" in r.requirement_id)
        assert pol06.outcome == "PASS"

    def test_over_age_pol06_unknown_or_fail(self, rule_set, au_186_reqs):
        """46세 → POL_06 age_range FAIL + manual_check UNKNOWN → any → UNKNOWN."""
        profile = {"date_of_birth": "1980-01-01", "application_date": "2026-10-28"}
        result: EligibilityResult = check_eligibility(
            rule_set=rule_set,
            requirements=au_186_reqs,
            profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        pol06 = next(r for r in result.requirements if "POL_06" in r.requirement_id)
        assert pol06.outcome in ("UNKNOWN", "FAIL")


# ════════════════════════════════════════════════════════════════════════════
# 3. 에이전트 상태 집계 로직 검증 (aggregate 단위)
# ════════════════════════════════════════════════════════════════════════════

class TestAggregateLogic:
    """_aggregate: FAIL > UNKNOWN > PASS, 빈 목록 → UNKNOWN."""

    def _run(self, outcomes: list[str]) -> str:
        from app.agent.eligibility.checker import _aggregate
        return _aggregate(outcomes)

    def test_empty_is_unknown(self):
        assert self._run([]) == "UNKNOWN"

    def test_all_pass_is_pass(self):
        assert self._run(["PASS", "PASS"]) == "PASS"

    def test_fail_dominates_unknown(self):
        assert self._run(["PASS", "UNKNOWN", "FAIL"]) == "FAIL"

    def test_unknown_dominates_pass(self):
        assert self._run(["PASS", "UNKNOWN"]) == "UNKNOWN"

    def test_single_fail_is_fail(self):
        assert self._run(["FAIL"]) == "FAIL"
