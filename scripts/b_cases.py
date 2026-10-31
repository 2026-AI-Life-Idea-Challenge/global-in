"""B 답변 형식 점검: 테스트 질문을 실제로 실행해 저장하고, 저장된 결과로 HTML 리포트를 만든다.

  실행(DB·OpenAI 호출):  python -B -m scripts.b_cases run [--cases FILE] [--only id,id] [--dev]
  다시 그리기(호출 없음): python -B -m scripts.b_cases render RESULTS.json [--compare OTHER.json]

run은 결과를 logs/b_cases/YYYYMMDD-HHMMSS/results.json에 저장하고 같은 폴더에 report.html을 만든다.
render는 저장된 반환값을 **현재** 화면 렌더러(scripts/rag_cli.py)로 다시 그린다. 화면 형식만 바꿨다면
render로 바로 확인하고, 생성 지침(프롬프트)을 바꿨다면 run을 다시 실행한다.
자동 점검은 형식만 본다(내부 용어 노출, 어투, 출처 누락, 질문 개수 등). 사실 정확성은 판단하지 않는다.
자동 재시도는 하지 않는다.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import difflib
import html
import json
from pathlib import Path
import re
import sys
import time

from scripts import rag_cli as cli

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests" / "cases" / "b_answer_cases.json"
OUT_DIR = ROOT / "logs" / "b_cases"
LONG_ANSWER = 1200
INTERNAL_TERMS = (
    "chunk", "program_id", "support_program_id", "development_only", "release_mode", "answer_approved",
    "content_review_status", "insufficient_evidence", "evidence", "UNKNOWN", "None", "null", "개발 검증",
    "[1]", "p1.s",
)
# 마침표·물음표로 끝나는 문장의 해요체·반말 어미. 공식 어투(~합니다)만 허용한다.
# '나이: 만 18~35세'처럼 문장부호 없는 값 줄은 검사하지 않는다.
INFORMAL_ENDING = re.compile(r"(?:요|야|어|지|네|죠|해|돼|래)[.?!~]+$")
CHECK_LABELS = {
    "error": "실행 오류", "empty": "빈 답변", "internal_terms": "내부 용어 노출", "informal_tone": "공식 어투 아님",
    "no_source": "출처 없음", "missing_link": "링크 없는 출처", "multiple_questions": "질문 2개 이상",
    "long": "답변이 김", "must_include": "필수 문구 없음", "must_not_include": "금지 문구 포함",
}


# ---------------------------------------------------------------- 케이스

def load_cases(path=CASES_PATH, only=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data["cases"]
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and i.strip() for i in ids):
        raise ValueError("케이스 id는 비어 있지 않고 서로 달라야 합니다.")
    for case in cases:
        turns = case.get("turns")
        if not isinstance(turns, list) or not turns or not all(isinstance(t, str) and t.strip() for t in turns):
            raise ValueError(f"{case['id']}: turns는 비어 있지 않은 질문 목록이어야 합니다.")
        checks = case.get("checks") or {}
        if set(checks) - {"must_include", "must_not_include"}:
            raise ValueError(f"{case['id']}: checks에는 must_include/must_not_include만 쓸 수 있습니다.")
    if only:
        wanted = set(only)
        unknown = wanted - set(ids)
        if unknown:
            raise ValueError("없는 케이스 id: " + ", ".join(sorted(unknown)))
        cases = [case for case in cases if case["id"] in wanted]
    return cases


# ---------------------------------------------------------------- 실행

def _plain(value):
    """저장 가능한 JSON 값으로 바꾼다(date 등은 문자열)."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def run_cases(cases, *, mode="production", today=None, session_factory=None, write=print):
    """케이스마다 새 세션으로 질문한다. 설정 오류는 즉시 중단, 다른 오류는 기록 후 다음 케이스."""
    from app.models.rag import RagConfigurationError
    if session_factory is None:
        from app.services.b_question_router import BQuestionSession
        session_factory = BQuestionSession
    today = today or date.today()
    results = {"version": 1, "created_at": datetime.now().isoformat(timespec="seconds"), "mode": mode,
               "today": today.isoformat(), "cases": []}
    for number, case in enumerate(cases, 1):
        write(f"[{number}/{len(cases)}] {case['id']}")
        session = session_factory(mode=mode, today=today)
        turns, failed = [], False
        for question in case["turns"]:
            record = {"question": question, "reply": None, "rendered": None, "error": None, "seconds": None}
            if failed:
                record["error"] = "이전 질문 오류로 실행하지 않았습니다."
                turns.append(record)
                continue
            started = time.monotonic()
            try:
                reply = session.ask(question)
                record["reply"] = _plain(reply)
                record["rendered"] = cli.render_reply(reply, today=today)
            except RagConfigurationError:
                raise
            except Exception as exc:
                record["error"] = cli.render_error(exc)
                record["error_type"] = type(exc).__name__
                # 응답 검증 오류는 코드·필드 경로만 남긴다(응답 원문·키 없음).
                if isinstance(getattr(exc, "issues", None), list):
                    record["error_issues"] = exc.issues
                failed = True
            record["seconds"] = round(time.monotonic() - started, 2)
            turns.append(record)
        results["cases"].append({key: case.get(key) for key in ("id", "category", "note", "checks")} | {"turns": turns})
    return results


# ---------------------------------------------------------------- 점검

def _body_lines(text):
    return [line for line in text.splitlines() if line.strip() and not line.startswith("출처:")]


def check_turn(reply, text, checks=None):
    """화면 답변의 형식 점검. [(종류, 설명)]."""
    found = []
    if not text or not text.strip():
        return [("empty", "답변이 비어 있습니다.")]
    body = "\n".join(_body_lines(text))
    terms = [term for term in INTERNAL_TERMS if term in body]
    if terms:
        found.append(("internal_terms", ", ".join(terms)))
    informal = []
    for line in _body_lines(text):
        for sentence in re.split(r"(?<=[.?!])\s+", line.strip()):
            if INFORMAL_ENDING.search(sentence.strip()):
                informal.append(sentence.strip())
    if informal:
        found.append(("informal_tone", " / ".join(informal[:3])))
    kind = (reply or {}).get("kind")
    has_content = (kind == "rag" and (reply.get("result") or {}).get("claims")) or \
                  (kind == "support_list" and reply.get("supports"))
    if has_content and "출처:" not in text:
        found.append(("no_source", "근거가 있는 답변인데 출처 줄이 없습니다."))
    if "(링크 미기록)" in text:
        found.append(("missing_link", "출처 링크가 없는 항목이 있습니다."))
    if text.count("?") > 1:
        found.append(("multiple_questions", f"물음표 {text.count('?')}개"))
    if len(text) > LONG_ANSWER:
        found.append(("long", f"{len(text)}자"))
    for phrase in (checks or {}).get("must_include", []):
        if phrase not in text:
            found.append(("must_include", phrase))
    for phrase in (checks or {}).get("must_not_include", []):
        if phrase in text:
            found.append(("must_not_include", phrase))
    return found


def _meta(reply):
    if not reply:
        return ""
    kind = reply.get("kind")
    if kind == "rag":
        result = reply.get("result") or {}
        parts = [f"상태 {result.get('status')}", f"주장 {len(result.get('claims') or [])}",
                 f"미답변 {len(result.get('unanswered_parts') or [])}", f"근거 {len(result.get('evidence') or [])}",
                 f"표시 {result.get('layout', 'default')}"]
        if result.get("model"):
            parts.append(f"모델 {result['model']}")
        return "rag · " + " · ".join(parts)
    if kind == "support_list":
        return f"support_list · 제도 {len(reply.get('supports') or [])}"
    return str(kind)


# ---------------------------------------------------------------- 리포트

def rerender(results, today=None):
    """저장된 반환값을 현재 렌더러로 다시 그린다. {(id, 턴): (화면, 디버그)}."""
    today = today or date.fromisoformat(results["today"])
    rendered = {}
    for case in results["cases"]:
        for index, turn in enumerate(case["turns"]):
            reply = turn.get("reply")
            if reply is None:
                rendered[(case["id"], index)] = (None, None)
                continue
            rendered[(case["id"], index)] = (cli.render_reply(reply, today=today),
                                             cli.render_reply(reply, details=True, today=today))
    return rendered


def _diff(old, new):
    lines = []
    for line in difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), lineterm="", n=1):
        if line.startswith(("---", "+++")):
            continue
        css = "add" if line.startswith("+") else "del" if line.startswith("-") else "ctx"
        lines.append(f'<span class="{css}">{html.escape(line)}</span>')
    return "\n".join(lines)


def build_report(results, *, compare=None, compare_label=None):
    """케이스별 질문·화면 답변·형식 점검·변경점을 담은 단일 HTML."""
    current = rerender(results)
    if compare is not None:
        baseline = {key: value[0] for key, value in rerender(compare).items()}
        baseline_label = compare_label or "비교 실행"
    else:
        baseline = {(c["id"], i): t.get("rendered") for c in results["cases"] for i, t in enumerate(c["turns"])}
        baseline_label = "실행 당시 화면"
    totals, cards, changed_count = {}, [], 0
    for case in results["cases"]:
        turns_html, case_flags = [], []
        for index, turn in enumerate(case["turns"]):
            text, debug = current[(case["id"], index)]
            last = index == len(case["turns"]) - 1
            error = turn.get("error")
            if error and turn.get("error_issues"):
                error += " " + json.dumps(turn["error_issues"], ensure_ascii=False)
            flags = [("error", error)] if error else \
                check_turn(turn.get("reply"), text, case.get("checks") if last else None)
            case_flags += flags
            for kind, _ in flags:
                totals[kind] = totals.get(kind, 0) + 1
            old = baseline.get((case["id"], index))
            changed = old is not None and text is not None and old != text
            changed_count += changed
            badges = "".join(f'<span class="badge {k}" title="{html.escape(str(d))}">{CHECK_LABELS[k]}</span>'
                             for k, d in flags) or '<span class="badge ok">형식 점검 통과</span>'
            flag_list = "".join(f"<li><b>{CHECK_LABELS[k]}</b> {html.escape(str(d))}</li>" for k, d in flags)
            meta = " · ".join(part for part in (_meta(turn.get("reply")),
                               f"{turn['seconds']}초" if turn.get("seconds") is not None else "") if part)
            turns_html.append(f"""
      <div class="turn">
        <div class="q"><span class="who">나</span>{html.escape(turn['question'])}</div>
        <div class="meta">{html.escape(meta)}</div>
        <pre class="a">{html.escape(text if text is not None else turn.get('error') or '')}</pre>
        <div class="badges">{badges}{'<span class="badge changed">변경됨</span>' if changed else ''}</div>
        {f'<ul class="flags">{flag_list}</ul>' if flags else ''}
        {f'<details><summary>{html.escape(baseline_label)} 대비 변경점</summary><pre class="diff">{_diff(old, text)}</pre></details>' if changed else ''}
        {f'<details><summary>디버그 보기</summary><pre class="debug">{html.escape(debug)}</pre></details>' if debug else ''}
      </div>""")
        warn = "warn" if case_flags else "clean"
        note = f'<p class="note">{html.escape(case["note"])}</p>' if case.get("note") else ""
        cards.append(f"""
    <section class="case {warn}" id="{html.escape(case['id'])}">
      <h2><span class="cat">{html.escape(case.get('category') or '')}</span>{html.escape(case['id'])}</h2>
      {note}{''.join(turns_html)}
    </section>""")
    summary = "".join(f'<li><span class="badge {k}">{CHECK_LABELS[k]}</span> {n}건</li>'
                      for k, n in sorted(totals.items(), key=lambda item: -item[1])) or "<li>형식 경고 없음</li>"
    index = "".join(f'<a href="#{html.escape(c["id"])}">{html.escape(c["id"])}</a>' for c in results["cases"])
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>B 답변 점검</title>
<style>
:root{{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--muted:#6b6b66;--line:#e3e2dc;--warn:#b54708;--warnbg:#fef0e6;
--err:#b42318;--errbg:#fde8e7;--ok:#067647;--okbg:#e7f6ee;--chg:#3538cd;--chgbg:#eef0ff;--code:#f1f0ec}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--card:#1f1f1d;--fg:#ecebe6;--muted:#a3a29b;--line:#34332f;
--warn:#f5a25d;--warnbg:#3a2614;--err:#f97066;--errbg:#3d1714;--ok:#47cd89;--okbg:#10301f;--chg:#a4bcfd;--chgbg:#1e2240;--code:#262623}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
main{{max-width:920px;margin:0 auto;padding:24px 16px 64px}}h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:var(--muted);margin:0 0 16px}}.summary{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:12px}}
.summary ul{{list-style:none;padding:0;margin:8px 0 0;display:flex;flex-wrap:wrap;gap:8px 16px}}
.index{{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}}.index a{{font-size:12px;color:var(--muted);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:2px 6px}}
label.filter{{display:inline-flex;gap:6px;align-items:center;font-size:14px;color:var(--muted)}}
.case{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:12px 0}}
.case h2{{font-size:16px;margin:0 0 4px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.cat{{font-size:12px;font-weight:500;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:1px 6px}}
.note{{color:var(--muted);font-size:13px;margin:0 0 8px}}.turn{{border-top:1px solid var(--line);padding-top:12px;margin-top:12px}}
.q{{font-weight:600}}.who{{font-size:12px;color:var(--muted);margin-right:8px}}.meta{{font-size:12px;color:var(--muted);margin:2px 0 8px}}
pre{{white-space:pre-wrap;word-break:break-word;margin:0;font:inherit}}pre.a{{background:var(--code);border-radius:8px;padding:12px}}
pre.debug,pre.diff{{font:12px/1.5 ui-monospace,Menlo,monospace;background:var(--code);border-radius:8px;padding:10px;max-height:420px;overflow:auto}}
.badges{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}.badge{{font-size:12px;border-radius:999px;padding:1px 8px;background:var(--warnbg);color:var(--warn)}}
.badge.error,.badge.must_include,.badge.must_not_include,.badge.no_source{{background:var(--errbg);color:var(--err)}}
.badge.ok{{background:var(--okbg);color:var(--ok)}}.badge.changed{{background:var(--chgbg);color:var(--chg)}}
.flags{{font-size:13px;margin:6px 0 0;padding-left:18px;color:var(--muted)}}details{{margin-top:8px}}summary{{cursor:pointer;font-size:13px;color:var(--muted)}}
.add{{color:var(--ok)}}.del{{color:var(--err)}}.ctx{{color:var(--muted)}}
body.only-warn .case.clean{{display:none}}
</style></head><body><main>
<h1>B 답변 점검</h1>
<p class="sub">실행 {html.escape(results['created_at'])} · 모드 {html.escape(results['mode'])} · 기준일 {html.escape(results['today'])} ·
케이스 {len(results['cases'])}개 · 비교 기준: {html.escape(baseline_label)} · 변경된 답변 {changed_count}개</p>
<div class="summary"><b>자동 형식 점검</b> (사실 정확성은 판단하지 않음)<ul>{summary}</ul></div>
<label class="filter"><input type="checkbox" onchange="document.body.classList.toggle('only-warn', this.checked)"> 경고 있는 케이스만 보기</label>
<nav class="index">{index}</nav>
{''.join(cards)}
</main></body></html>"""


def save_report(results_path, *, compare_path=None, out=None):
    results = json.loads(Path(results_path).read_text(encoding="utf-8"))
    compare = json.loads(Path(compare_path).read_text(encoding="utf-8")) if compare_path else None
    out = Path(out) if out else Path(results_path).with_name("report.html")
    out.write_text(build_report(results, compare=compare,
                                compare_label=str(compare_path) if compare_path else None), encoding="utf-8")
    return out


# ---------------------------------------------------------------- CLI

def main(argv=None, write=print):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="질문을 실제로 실행하고 결과·리포트 저장(DB·OpenAI 호출)")
    run.add_argument("--cases", default=str(CASES_PATH))
    run.add_argument("--only", help="쉼표로 구분한 케이스 id만 실행")
    run.add_argument("--dev", action="store_true", help="개발 검증 모드로 실행")
    render = sub.add_parser("render", help="저장된 결과로 리포트만 다시 생성(호출 없음)")
    render.add_argument("results")
    render.add_argument("--compare", help="비교할 다른 results.json")
    render.add_argument("--out")
    args = parser.parse_args(argv)

    if args.command == "render":
        write(f"리포트: {save_report(args.results, compare_path=args.compare, out=args.out)}")
        return 0
    cases = load_cases(args.cases, args.only.split(",") if args.only else None)
    turns = sum(len(case["turns"]) for case in cases)
    write(f"케이스 {len(cases)}개, 질문 {turns}개를 실행합니다. 질문마다 질문 해석 1회와 답변 생성 최대 1회 OpenAI 호출이 있습니다.")
    cli.configure_environment()
    results = run_cases(cases, mode="development" if args.dev else "production", write=write)
    folder = OUT_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    write(f"결과: {path}")
    write(f"리포트: {save_report(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
