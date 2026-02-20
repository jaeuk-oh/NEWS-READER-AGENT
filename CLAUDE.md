# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소의 코드를 다룰 때 참고하는 지침서이다.

## 환경 및 명령어

- **패키지 매니저:** `uv` (Python 3.13). 가상환경 경로는 `.venv`.
- **의존성 설치/동기화:** `uv sync`
- **의존성 추가:** `uv add <package>`
- **크루만 실행:** `uv run python main.py`
- **구독 스케줄러 시작:** `uv run python subscription_scheduler.py`
- **구독 파이프라인 1회 수동 실행:** `uv run python -c "from subscription_scheduler import run_once; run_once()"`
- **Streamlit UI 실행:** `uv run streamlit run app.py`
- **필수 환경변수:** `.env.example`을 `.env`로 복사한 뒤 값을 채운다. 모든 키와 설정 방법은 해당 파일 참조.
- 테스트 스위트나 린터는 설정되어 있지 않다.

## 아키텍처

구독 기반 CrewAI 멀티 에이전트 뉴스 파이프라인. 유저가 Streamlit UI로 토픽·이메일·시간을 등록하면, 스케줄러가 해당 시간에 크루를 실행하고 이메일로 리포트를 발송한다.

```
Streamlit (app.py)
    ├─ 구독 등록/관리 UI (2탭)
    └─ db.py → Supabase (subscriptions 테이블)

subscription_scheduler.py (매분 체크)
    ├─ db.get_due_subscriptions(HH:MM)
    ├─ 동일 토픽 그룹핑 → main.run_crew() 1회 실행
    │       │
    │       ├─ news_hunter_agent   →  output/content_harvest.md
    │       │      멀티 쿼리 검색, 스크래핑, 전문 + 점수
    │       ├─ summarizer_agent    →  output/summary.md
    │       │      3단계 요약 + 핵심 시사점, 점수 유지
    │       └─ curator_agent       →  output/final_report.md
    │              점수 기반 리드 선정, 동적 섹션, 에디터 분석
    ├─ 번역 (설정 시) → services/translator.py
    └─ send_email_to_subscriber() → 구독자 이메일 발송
```

### 동작이 정의된 위치

- **에이전트 페르소나** → `config/agents.yaml`
- **태스크 로직, 출력 형식, 출력 파일** → `config/tasks.yaml`
- **에이전트/태스크 연결** → `main.py` (`News_Reader_Agent` 클래스; `@agent`/`@task`/`@crew` 데코레이터가 YAML 설정을 바인딩)
- **구독 DB** → `db.py` (Supabase CRUD)
- **구독 UI** → `app.py` (Streamlit 웹 UI)
- **스케줄러** → `subscription_scheduler.py` (매분 체크, 토픽 그룹핑, 크루 실행 → 이메일 발송)

### 도구

`main.py`는 `crewai_tools`의 `FirecrawlSearchTool`과 `FirecrawlScrapeWebsiteTool`을 직접 사용한다. 커스텀 도구 래퍼는 없다.

### 스테이지 간 결합 — 수정 시 주의

세 스테이지는 `expected_output` 형식을 통해 결합되어 있다. 각 스테이지의 출력이 다음 스테이지의 입력 컨텍스트가 된다. 한 스테이지의 `expected_output` 필드를 변경하면, 다음 스테이지의 `description`도 맞춰서 수정해야 한다:

- `content_harvesting_task`는 `**Content:**` (기사 전문)과 점수를 출력 → `summarization_task`는 재스크래핑 없이 해당 내용을 읽음
- `summarization_task`는 `**Credibility Score:**`와 `**Relevance Score:**`를 유지하고 `**Key Takeaways:**`를 추가 → `final_report_assembly_task`가 점수를 리드 선정 및 섹션 배치에 활용

## Notes

- `output/*.md` 파일은 런타임에 생성되며 gitignore 처리되어 있다. `output/` 디렉토리는 `.gitkeep`으로 유지된다.
- 구독자의 토픽이 쉼표로 구분된 다중 주제를 지원한다 (예: `AI, AI-agent, influence of agent in industry`). 헌터가 이를 3~4개의 집중 서브쿼리로 자동 분리한다.
- **번역 (선택):** `.env`에서 `TRANSLATION_ENABLED=true`로 설정하면 자동 번역이 활성화된다. `deep-translator` 라이브러리를 사용하며 API 키가 불필요하다. 제목, 글머리 기호, 볼드, 링크 등 마크다운 구조가 유지된다. 대상 언어 기본값은 한국어 (`ko`)이며 `TRANSLATION_TARGET_LANG`으로 변경 가능하다. 번역 실패 시 영문 버전으로 자동 대체된다.

## Claude 규칙

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
