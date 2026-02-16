# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment & Commands

- **Package manager:** `uv` (Python 3.13). Virtual env is at `.venv`.
- **Install / sync deps:** `uv sync`
- **Add a dependency:** `uv add <package>`
- **Run the crew only:** `uv run python main.py`
- **Start the full scheduled pipeline:** `uv run python scheduler.py`
- **Run the pipeline once manually (no waiting for 07:00):** `uv run python -c "from scheduler import run_pipeline; run_pipeline()"`
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

### Subscription system (WIP)

- **`db.py`** — Supabase 기반 구독 CRUD. `subscriptions` 테이블 사용.
- **Required env vars:** `SUPABASE_URL`, `SUPABASE_KEY`
- 자세한 구현 계획은 `plan.md` 참조.

## Notes

- `output/*.md` files are generated at runtime and gitignored. The `output/` directory is preserved via `.gitkeep`.
- `NEWS_TOPIC` in `.env` supports comma-separated topics (e.g. `AI, AI-agent, influence of agent in industry`). The hunter breaks these into 3-4 focused sub-queries automatically.
- The Notion converter in `services/notion.py` handles: H1/H2/H3, dividers (`---`), bullet lists (`- ...`), and paragraphs with inline bold/links. Anything outside that set will be dropped or rendered as plain text.
- **Translation (optional):** Set `TRANSLATION_ENABLED=true` in `.env` to enable automatic translation. Uses `deep-translator` library (no API key required). Preserves markdown structure including headings, bullets, bold, and links. Target language defaults to Korean (`ko`) but can be changed via `TRANSLATION_TARGET_LANG`. Translation failures fall back gracefully to English version.

## Rules for Claude

### STRICT RULES (절대 위반 금지)

아래 3가지는 **반드시 사전 승인**을 받아야 하며, 무단으로 수행해서는 안 된다.

1. **`.env` 파일 — 읽기/수정 금지.** 환경 변수에 문제가 의심되면 유저에게 먼저 확인할 것.
2. **브랜치 생성 — 사전 승인 필수.** 새 브랜치를 만들기 전에 브랜치 이름과 목적을 유저에게 보여주고 승인을 받을 것.
3. **커밋 & 푸시 — 사전 승인 필수.** 커밋하기 전에 커밋 메시지를 유저에게 보여주고 승인을 받을 것. 푸시 대상 브랜치도 명시할 것.
