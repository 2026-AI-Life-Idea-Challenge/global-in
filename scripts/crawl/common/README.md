# 국가 공통 원문 수집

미국·일본 검토에 사용하는 공식 원문과 보충 법령·법원 명령을 수집한다. 프로젝트 루트에서 실행한다.

```powershell
pwsh -NoProfile -File scripts/crawl/common/collect_us_jp_review_sources.ps1
pwsh -NoProfile -File scripts/crawl/common/collect_us_jp_review_sources.ps1 -SupplementalOnly
pwsh -NoProfile -File scripts/crawl/common/collect_us_jp_review_sources.ps1 -ResolutionOnly
```

입력 스냅샷은 `data/processed/legal_review/inputs/`에, 원문과 수집 manifest는 `data/raw/legal_review/20261028/`에 저장한다. 기존 원문은 다시 내려받지 않고 재사용한다. 재실행이 새 시점의 원문 확인을 뜻하지 않는다. 새 다운로드가 기존 검토 시점과 다르면 해시 검증이 실패할 수 있으므로 기존 근거 해시를 임의로 바꾸지 않는다.

`data/raw/`는 Git 제외 대상이다. 공유용 원문 목록은 `data/processed/legal_review/source_manifest_20261028.json`에 있다. 원문 수집과 법적 효력 확인은 별도 단계다.
