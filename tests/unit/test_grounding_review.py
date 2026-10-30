from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError
from app.models.rag import RagDraft, RagLLMError
from app.services import grounding_review as review
from app.services.rag_llm import build_citation_spans
from app.services.rag_llm import _request_rag_draft
from app.services import rag_llm
from app.models.rag import DraftItem, RagResponseValidationError
from app.services import request_budget

def test_decimal_and_legal_sections_are_not_truncated():
    text='IELTS 4.5 이상과 3.5cm 사진, Migration Regulations 5.17을 확인한다.'
    spans=build_citation_spans([dict(chunk_id='x',body=text)])
    assert len(spans)==1 and next(iter(spans.values())).quote==text

def test_reviewer_preserves_supported_claim_and_withholds_overclaim(monkeypatch):
    draft=RagDraft.model_validate(dict(items=[dict(question_part='급여',answer='45세 이하가 대상입니다.',citation_ids=['p1.s1']),
        dict(question_part='나이',answer='원칙적으로 45세 미만입니다.',citation_ids=['p1.s2'])]))
    verdict=review.Review(items=[review.Verdict(item_index=0,supported=False,reason='연령 방향 반전'),review.Verdict(item_index=1,supported=True,reason='일치')])
    response=SimpleNamespace(status='completed',output_parsed=verdict)
    client=MagicMock();client.__enter__.return_value.responses.parse.return_value=response
    monkeypatch.setattr(review,'OpenAI',lambda **kwargs:client)
    result=review.review_draft(draft,{'retrieved_passages':[{'citation_spans':[dict(id='p1.s1',text='45세를 채운 뒤이면 급여 기준 적용'),dict(id='p1.s2',text='원칙적으로 45세 미만')]}]},'synthetic-model')
    assert result.items[0].answer is None and result.items[0].citation_ids==[]
    assert result.items[1]==draft.items[1]
    assert draft.items[0].answer is not None  # Input not mutated.

def test_grounding_context_does_not_leak_between_calls(monkeypatch):
    assert not review.enabled.get()
    @review.with_grounding_review
    def fails():
        assert review.enabled.get()
        raise RuntimeError('synthetic')
    with pytest.raises(RuntimeError): fails()
    assert not review.enabled.get()

def test_missing_review_items_fail_closed(monkeypatch):
    client=MagicMock();client.__enter__.return_value.responses.parse.return_value=SimpleNamespace(status='completed',output_parsed=review.Review(items=[]))
    monkeypatch.setattr(review,'OpenAI',lambda **kwargs:client)
    draft=RagDraft.model_validate(dict(items=[dict(question_part='요건',answer='조건',citation_ids=['p1.s1'])]))
    with pytest.raises(ValueError,match='coverage'):
        review.review_draft(draft,{},'synthetic')

def test_remaining_request_budget_applies_to_each_network_stage(monkeypatch):
    monkeypatch.setattr(request_budget.time,'monotonic',lambda:10)
    token=request_budget.deadline.set(15)
    try:
        assert request_budget.timeout()==5
        monkeypatch.setattr(request_budget.time,'monotonic',lambda:16)
        with pytest.raises(TimeoutError):request_budget.timeout()
    finally:request_budget.deadline.reset(token)

def test_consultation_structural_retry_is_bounded_and_revalidated(monkeypatch):
    try:DraftItem.model_validate(dict(question_part='접수',answer=None,citation_ids=['p1.s1']))
    except ValidationError as error:invalid=error
    good=RagDraft.model_validate(dict(items=[dict(question_part='접수',answer=None,citation_ids=[])]))
    response=SimpleNamespace(status='completed',output=[],output_parsed=good,model='synthetic')
    client=MagicMock();transport=client.__enter__.return_value.responses.parse
    transport.side_effect=[invalid,response]
    monkeypatch.setattr(rag_llm,'OpenAI',lambda **kwargs:client)
    monkeypatch.setattr(review,'review_draft',lambda draft,*args:draft)
    token=review.enabled.set(True)
    try:
        result=_request_rag_draft({},system_prompt='검증',draft_type=RagDraft,model='synthetic',effort=None)
        assert result.draft==good and transport.call_count==2
        transport.reset_mock();transport.side_effect=[invalid,invalid,invalid]
        with pytest.raises(RagResponseValidationError):
            _request_rag_draft({},system_prompt='검증',draft_type=RagDraft,model='synthetic',effort=None)
        assert transport.call_count==2
    finally:review.enabled.reset(token)
