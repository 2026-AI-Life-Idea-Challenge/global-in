"""
tests/unit/test_recheck.py

⑤ 재검토 — recheck_with_updated_profile() 단위 테스트
사용자가 프로필 정보를 보완한 뒤 재평가할 때 결과가 올바르게 바뀌는지 검증합니다.
DB 없이 release JSON expression을 직접 사용합니다.

실행:
    pytest tests/unit/test_recheck.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.rules.evaluator import PASS, FAIL, UNKNOWN
from app.agent.eligibility.checker import (
    check_eligibility,
    recheck_with_updated_profile,
    EligibilityResult,
)
from app.agent.eligibility.fetcher import RuleSet, RequirementRecord
from app.agent.eligibility.demo_profile_schema import (
    demo_profile_ca_iec_wh_pass,
    demo_profile_ca_iec_wh_fail_funds,
)

# ── 픽스처 ───────────────────────────────────────────────────────────────────

RELEASE_JSON = (
    PROJECT_ROOT
    / "data/processed/knowledge/20261028/releases"
    / "knowledge-v1-20261028-0e63b144b983"
    / "knowledge_release.json"
)


@pytest.fixture(scope="module")
def ca_iec_reqs() -> list[RequirementRecord]:
    with open(RELEASE_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return [
        RequirementRecord(
            requirement_id=r["requirement_id"],
            target_type="PROGRAM",
            target_id="CA:iec_working_holiday",
            judgeability=r["judgeability"],
            definition=r["expression"],
            release_id="v1",
        )
        for r in data["requirements"]
        if r.get("target", {}).get("target_id") == "CA:iec_working_holiday"
    ]


@pytest.fixture(scope="module")
def rule_set() -> RuleSet:
    return RuleSet(
        rule_set_id="RS_CA_IEC",
        target_type="PROGRAM",
        target_id="CA:iec_working_holiday",
        coverage_complete=False,
        definition={},
        release_id="v1",
    )


# ── 테스트 ───────────────────────────────────────────────────────────────────

class TestRecheckFundsSufficiency:
    """자금 부족 → 보완 → 재검토 시나리오."""

    def test_initial_fail_due_to_funds(self, rule_set, ca_iec_reqs):
        """초기 프로필: 자금 부족 → overall FAIL."""
        result = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=demo_profile_ca_iec_wh_fail_funds(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == FAIL
        pol03 = next(r for r in result.requirements if "POL_03" in r.requirement_id)
        assert pol03.outcome == FAIL

    def test_recheck_after_funds_updated(self, rule_set, ca_iec_reqs):
        """자금 보완 후 재검토 → POL_03 PASS, overall UNKNOWN (manual_check 잔여)."""
        updated = demo_profile_ca_iec_wh_fail_funds()
        updated["initial_settlement_funds_cad"] = 3000.0  # 2500 이상으로 보완

        result = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            updated_profile=updated,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == UNKNOWN  # FAIL 해소 → manual_check만 남음
        pol03 = next(r for r in result.requirements if "POL_03" in r.requirement_id)
        assert pol03.outcome == PASS

    def test_recheck_result_is_independent_of_initial(self, rule_set, ca_iec_reqs):
        """재검토 결과가 이전 check_eligibility 결과에 영향받지 않음."""
        _ = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=demo_profile_ca_iec_wh_fail_funds(),
            as_of="2026-10-28",
            verified_reviews=[],
        )
        updated = demo_profile_ca_iec_wh_fail_funds()
        updated["initial_settlement_funds_cad"] = 3000.0

        result = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            updated_profile=updated,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall != FAIL


class TestRecheckReturnTicket:
    """귀국 항공권 없음 → 보완 → 재검토."""

    def test_fail_without_return_ticket(self, rule_set, ca_iec_reqs):
        profile = demo_profile_ca_iec_wh_pass()
        profile["return_ticket_available"] = False
        profile["separate_return_ticket_funds_available"] = False
        result = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == FAIL

    def test_pass_after_ticket_provided(self, rule_set, ca_iec_reqs):
        profile = demo_profile_ca_iec_wh_pass()
        profile["return_ticket_available"] = False
        profile["separate_return_ticket_funds_available"] = False

        profile["return_ticket_available"] = True  # 항공권 보완
        result = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            updated_profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        pol03 = next(r for r in result.requirements if "POL_03" in r.requirement_id)
        assert pol03.outcome == PASS
        assert result.overall == UNKNOWN  # manual_check 잔여

    def test_pass_after_separate_funds_provided(self, rule_set, ca_iec_reqs):
        """별도 자금 보완 (항공권 대신)."""
        profile = demo_profile_ca_iec_wh_pass()
        profile["return_ticket_available"] = False
        profile["separate_return_ticket_funds_available"] = True  # 자금으로 대체

        result = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            updated_profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        pol03 = next(r for r in result.requirements if "POL_03" in r.requirement_id)
        assert pol03.outcome == PASS


class TestRecheckNationality:
    """국적 변경 시나리오 (불가능한 케이스 확인)."""

    def test_non_korean_stays_fail_after_recheck(self, rule_set, ca_iec_reqs):
        """미국 국적은 재검토해도 FAIL 유지."""
        profile = demo_profile_ca_iec_wh_pass()
        profile["nationalities"] = ["US"]

        initial = check_eligibility(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert initial.overall == FAIL

        # 재검토해도 국적은 여전히 US
        recheck = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            updated_profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert recheck.overall == FAIL

    def test_nationality_correction_changes_result(self, rule_set, ca_iec_reqs):
        """국적 KR로 수정 → POL_01 FAIL 해소 → overall UNKNOWN."""
        profile = demo_profile_ca_iec_wh_pass()
        profile["nationalities"] = ["US"]

        # 실수로 US 입력했다가 KR로 수정
        profile["nationalities"] = ["KR"]
        result = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=ca_iec_reqs,
            updated_profile=profile,
            as_of="2026-10-28",
            verified_reviews=[],
        )
        assert result.overall == UNKNOWN


class TestRecheckIdempotent:
    """동일 프로필로 여러 번 재검토해도 결과가 일정함."""

    def test_same_profile_same_result(self, rule_set, ca_iec_reqs):
        profile = demo_profile_ca_iec_wh_pass()
        r1 = recheck_with_updated_profile(
            rule_set=rule_set, requirements=ca_iec_reqs,
            updated_profile=profile, as_of="2026-10-28", verified_reviews=[],
        )
        r2 = recheck_with_updated_profile(
            rule_set=rule_set, requirements=ca_iec_reqs,
            updated_profile=profile, as_of="2026-10-28", verified_reviews=[],
        )
        assert r1.overall == r2.overall
        for req1, req2 in zip(r1.requirements, r2.requirements):
            assert req1.requirement_id == req2.requirement_id
            assert req1.outcome == req2.outcome
