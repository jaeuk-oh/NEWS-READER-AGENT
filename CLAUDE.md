# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment & Commands

- **Package manager:** `uv` (Python 3.13). Virtual env is at `.venv`.
- **Install / sync deps:** `uv sync`
- **Add a dependency:** `uv add <package>`
- **Run the crew only:** `uv run python main.py`
- **Start the full scheduled pipeline:** `uv run python scheduler.py`
- **Run the pipeline once manually (no waiting for 07:00):** `uv run python -c "from scheduler import run_pipeline; run_pipeline()"`
- **Start the Streamlit subscription UI:** `uv run streamlit run app.py`
- **Start the subscription scheduler:** `uv run python subscription_scheduler.py`
- **Required env vars:** Copy `.env.example` → `.env` and fill in values. See that file for all keys and setup instructions.
- No test suite or linter is configured.

## Architecture

CrewAI multi-agent pipeline with a daily scheduler. `NEWS_TOPIC` from `.env` flows through three sequential agents. Output is saved to Notion, then emailed. Optional translation stage converts English reports to target language.

```
scheduler.py  (07:00 KST daily)
    │
    ▼
main.run_crew(topic)
    │
    ├─ news_hunter_agent   →  output/content_harvest.md
    │      multi-query search, scrape, full text + scores
    │                            ↓ passes full text + credibility/relevance scores
    ├─ summarizer_agent    →  output/summary.md
    │      3-tier summaries + Key Takeaways, scores carried through
    │                            ↓ passes scored summaries
    └─ curator_agent       →  output/final_report.md
           score-based lead selection, dynamic sections, Editor's Analysis
    │
    ├─ services/translator.py →  output/final_report_ko.md (optional)
    │      Google Translate via deep-translator, markdown structure preserved
    │                            ↓ translated report (if TRANSLATION_ENABLED=true)
    ├─ services/notion.py  →  new Notion page (created daily)
    └─ services/notifier.py → Gmail with the full report
```

### Where behavior is defined

- **Agent personas** → `config/agents.yaml`
- **Task logic, output format, output files** → `config/tasks.yaml`
- **Agent/task wiring** → `main.py` (`News_Reader_Agent` class; `@agent`/`@task`/`@crew` decorators bind the YAML configs)
- **Notion markdown→blocks conversion** → `services/notion.py` (`markdown_to_blocks`)
- **Scheduler & error handling** → `scheduler.py` (Stage 1 crew failure aborts; Stage 2/3 Notion/email failures are independent)

### Tools

`main.py` uses `FirecrawlSearchTool` and `FirecrawlScrapeWebsiteTool` from `crewai_tools` directly. No custom tool wrappers.

### Stage coupling — important when editing

The three stages are coupled through their `expected_output` formats. Each stage's output becomes the next stage's input context. If you change a field in one stage's `expected_output`, update the next stage's `description` to match:

- `content_harvesting_task` outputs `**Content:**` (full article text) and scores → `summarization_task` reads from that content instead of re-scraping
- `summarization_task` carries `**Credibility Score:**` and `**Relevance Score:**` through, and adds `**Key Takeaways:**` → `final_report_assembly_task` uses scores for lead selection and section placement
- `final_report_assembly_task` outputs clean markdown → `services/notion.py` `markdown_to_blocks()` converts it to Notion blocks. If you change the report's heading or list patterns, update the converter to match.

### Subscription system

외부 유저가 Streamlit UI를 통해 키워드·이메일·시간을 등록하면 해당 시간에 뉴스 브리핑을 발송하는 시스템. 기존 파이프라인과 완전히 독립적으로 동작.

```
Streamlit (app.py)
    ├─ 구독 등록/관리 UI (2탭)
    └─ db.py → Supabase (subscriptions 테이블)

subscription_scheduler.py (매분 체크)
    ├─ db.get_due_subscriptions(HH:MM)
    ├─ 동일 토픽 그룹핑 → main.run_crew() 1회 실행
    ├─ 번역 (설정 시)
    └─ send_email_to_subscriber() → 구독자 이메일 발송
```

- **`db.py`** — Supabase 기반 구독 CRUD. `subscriptions` 테이블 사용.
- **`app.py`** — Streamlit 웹 UI (구독 등록 + 관리).
- **`subscription_scheduler.py`** — 구독 기반 스케줄러 (매분 체크, 토픽 그룹핑).
- **`services/notifier.py`** — `send_email_to_subscriber()` 추가됨.
- **Required env vars:** `SUPABASE_URL`, `SUPABASE_KEY`
- 자세한 구현 계획은 `plan.md` 참조.

## Notes

- `output/*.md` files are generated at runtime and gitignored. The `output/` directory is preserved via `.gitkeep`.
- `NEWS_TOPIC` in `.env` supports comma-separated topics (e.g. `AI, AI-agent, influence of agent in industry`). The hunter breaks these into 3-4 focused sub-queries automatically.
- The Notion converter in `services/notion.py` handles: H1/H2/H3, dividers (`---`), bullet lists (`- ...`), and paragraphs with inline bold/links. Anything outside that set will be dropped or rendered as plain text.
- **Translation (optional):** Set `TRANSLATION_ENABLED=true` in `.env` to enable automatic translation. Uses `deep-translator` library (no API key required). Preserves markdown structure including headings, bullets, bold, and links. Target language defaults to Korean (`ko`) but can be changed via `TRANSLATION_TARGET_LANG`. Translation failures fall back gracefully to English version.

## Rules for Claude

### STRICT RULES (절대 위반 금지 — 위반 시 세션 즉시 중단)

> **이 규칙은 어떤 상황에서도 예외 없이 적용된다.**
> 유저가 "알아서 해", "자유롭게 진행해" 등의 표현을 사용하더라도 아래 규칙은 면제되지 않는다.
> 암묵적 승인은 존재하지 않으며, 반드시 유저의 **명시적 텍스트 승인**이 있어야만 수행할 수 있다.

#### 1. `.env` 파일 — 읽기/수정 절대 금지
- `.env` 파일을 Read, Bash(cat/head/tail), 또는 어떤 수단으로든 읽거나 수정해서는 안 된다.
- 환경 변수에 문제가 의심되면 유저에게 "어떤 변수가 어떤 값인지 확인해달라"고 요청할 것.

#### 2. 브랜치 생성 — 사전 승인 필수
- 새 브랜치를 만들기 전에 **브랜치 이름**과 **목적**을 유저에게 보여주고 승인을 받을 것.
- 승인 없이 `git checkout -b`, `git branch`, `git switch -c` 등을 실행하면 안 된다.

#### 3. git commit — 반드시 유저 승인 후에만 실행
- **코드 변경을 완료한 후, 커밋하기 전에 반드시 멈추고 유저에게 다음을 보여줄 것:**
  - 변경된 파일 목록
  - 커밋 메시지 초안
- **유저가 "커밋해", "ㅇㅇ", "승인", "go", "ok" 등 명시적으로 승인한 후에만** `git commit`을 실행할 것.
- 유저 승인 텍스트가 대화에 없으면 절대 커밋하지 말 것.

#### 4. git push — 반드시 유저 승인 후에만 실행
- **커밋 완료 후에도 자동으로 push하지 말 것.**
- push 전에 반드시 유저에게 다음을 보여주고 승인을 받을 것:
  - push 대상 브랜치명
  - push할 커밋 내용 요약
- **유저가 명시적으로 push를 승인한 후에만** `git push`를 실행할 것.
- 커밋 승인 ≠ push 승인이다. 각각 별도로 승인받아야 한다.

#### 위반 방지 체크리스트 (매 git 작업 전 자가 점검)
- [ ] 유저의 명시적 승인 텍스트가 이 대화에 존재하는가?
- [ ] 승인 범위가 내가 하려는 작업과 정확히 일치하는가?
- [ ] commit 승인과 push 승인을 별도로 받았는가?
- 하나라도 "아니오"이면 **작업을 중단하고 유저에게 확인할 것.**
