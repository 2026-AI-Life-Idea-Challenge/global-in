"""Trusted backend review outcomes are separate from user profile claims.

The calling server must obtain these from an authenticated reviewer store after
verifying the underlying evidence. Never deserialize a user/LLM message into this
type. No real approvals are created by the knowledge release or its tests.
"""
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re


def facts_hash(profile):
    return hashlib.sha256(json.dumps(profile,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class VerifiedReviewDecision:
    requirement_id: str
    target_type: str
    target_id: str
    criterion_sha256: str
    case_profile_sha256: str
    authority_id: str
    outcome: str
    evidence_sha256: str
    verified_by_principal: str
    verified_at: date
    valid_until: date

    def __post_init__(self):
        for value in (self.criterion_sha256,self.case_profile_sha256,self.evidence_sha256):
            if type(value) is not str or not re.fullmatch('[0-9a-f]{64}',value):raise ValueError('Invalid evidence/facts/criterion hash')
        if type(self.verified_at) is not date or type(self.valid_until) is not date or self.verified_at>self.valid_until:raise ValueError('Invalid review date window')
        if self.outcome not in ('조건 충족','조건 미충족'):raise ValueError('Only verified substantive outcomes belong in this type')
        if self.target_type not in ('PROGRAM','SUPPORT_PROGRAM'):raise ValueError('Invalid target type')
        for value in (self.requirement_id,self.target_id,self.authority_id,self.verified_by_principal):
            if type(value) is not str or not value.strip():raise ValueError('Missing authenticated review identity')


def review_status(requirement,profile,as_of,records):
    """Records come from the trusted backend argument, never from profile JSON."""
    unknown='추가 확인 필요'
    protocol=requirement['expression']
    try:current_facts=facts_hash(profile)
    except (TypeError,ValueError):return unknown
    day=date.fromisoformat(as_of)
    outcomes=set()
    for record in records or ():
        if not isinstance(record,VerifiedReviewDecision):continue
        if record.requirement_id!=requirement['requirement_id']:continue
        if record.target_type!=requirement['target']['target_type'] or record.target_id!=requirement['target']['target_id']:continue
        if record.criterion_sha256!=protocol['criterion_sha256'] or record.case_profile_sha256!=current_facts:continue
        if record.authority_id!=protocol['authority_id'] or not record.verified_by_principal:continue
        if not record.verified_at<=day<=record.valid_until:continue
        if not re.fullmatch('[0-9a-f]{64}',record.evidence_sha256):continue
        if record.outcome in ('조건 충족','조건 미충족'):outcomes.add(record.outcome)
    return next(iter(outcomes)) if len(outcomes)==1 else unknown
