# News Reader Agent

구독 기반 AI 뉴스 브리핑 시스템. 이메일·주제·발송 시각을 입력하면 CrewAI 멀티 에이전트 파이프라인이 뉴스를 자동으로 수집·요약·큐레이션하여 이메일로 발송한다.

---

## Agent Pipeline

### 전체 흐름 개요

```
[User]
  email + topic + schedule_time 입력
          │
          ▼
[FastAPI] POST /subscriptions
  Supabase subscriptions 테이블에 저장
          │
          ▼
[subscription_scheduler.py]  ← 매 30초마다 schedule.run_pending() 호출
  check_and_run() — 매분 실행
  now_hhmm = datetime.now().strftime("%H:%M")
  due = db.get_due_subscriptions(now_hhmm)
          │
          ├─ due가 비어있으면 → 종료 (아무것도 하지 않음)
          │
          ▼
  동일 topic끼리 그룹핑 (itertools.groupby)
  → 같은 topic 구독자가 여럿이어도 CrewAI 파이프라인은 1회만 실행
          │
          ▼
[CrewAI Pipeline]  run_crew(topic)
  ┌─────────────────────────────────────┐
  │  1. news_hunter_agent               │
  │     content_harvesting_task         │
  ├─────────────────────────────────────┤
  │  2. summarizer_agent                │
  │     summarization_task              │
  ├─────────────────────────────────────┤
  │  3. curator_agent                   │
  │     final_report_assembly_task      │
  └─────────────────────────────────────┘
          │
          ├─ 파이프라인 예외 → _run_for_topic() returns None → 해당 topic 건너뜀
          │
          ▼
  결과 검증 (_run_for_topic)
  ① content_harvest.md에 "Articles after filtering: 0" 포함 여부 확인
  ② final_report.md 존재 여부 확인
  ③ 리포트 길이 < 300자 여부 확인
  → 검증 실패 시 None 반환, 이메일 발송 건너뜀
          │
          ▼
  구독자별 번역 + 이메일 발송
  (target_lang != "en" → translate_to_TargetLang)
          │
          ▼
[Notifier]  send_email_to_subscriber()
  Resend API → 구독자 이메일 수신
```

---

### 1단계 — Scheduler: 구독 트리거

`subscription_scheduler.py`는 두 가지 실행 모드를 가진다.

| 모드 | 함수 | 용도 |
|---|---|---|
| 상시 구동 | `check_and_run()` | 매분 HH:MM 정확 매칭 |
| 일회성 | `run_once()` | GitHub Actions 등에서 시간대(HH) 단위 실행 |

**예외 처리:**
- `db.get_due_subscriptions()` 실패 시 예외가 스케줄러 루프 밖으로 전파되지 않도록 `check_and_run` 전체가 `schedule` 라이브러리의 잡 단위로 격리됨
- 특정 topic 파이프라인 실패 시 `continue`로 다음 topic으로 넘어감 — 한 topic 오류가 다른 구독자에게 영향을 주지 않음

---

### 2단계 — CrewAI Pipeline: 3-Agent 순차 파이프라인

#### Agent 1: `news_hunter_agent` — 콘텐츠 수집

**역할:** 주제를 3~4개의 독립 검색 쿼리로 분해하고, 각 쿼리 결과에서 실제 기사 URL만 선별하여 본문을 수집한다.

```
topic 입력
    │
    ▼
쿼리 분해 (3~4개)
    │
    ▼
web_search_tool(query) — Tavily API 호출
    │
    ├─ TAVILY_API_KEY 미설정 → "Error: TAVILY_API_KEY is not set." 반환
    ├─ 네트워크/API 오류   → "Error: search request failed — {e}. Do not retry." 반환
    ├─ 결과 없음           → "No articles found for this query." 반환
    └─ 정상               → 기사 목록 반환 (최대 max_results=3개)
         │
         ▼
    각 기사 처리 (tools.py)
    ├─ raw_content 또는 content 추출
    ├─ 연속 줄바꿈 정리 (re.sub)
    ├─ 1500단어 초과 시 truncate
    └─ 개별 기사 처리 실패 시 continue (다음 기사로)
```

**URL 필터링 기준 (LLM 판단):**
- ❌ `/tag/`, `/topic/`, `/hub/`, `/section/`, `/category/` 포함 URL 제외
- ❌ 200단어 미만 기사 제외
- ❌ 48시간 초과 기사 제외 (단, 진행 중인 사안은 예외)
- ✅ 최종 7개 이하만 선택

**Fallback 전략 (수집 기사 < 3개인 경우 순서대로 시도):**

```
Step A: 쿼리 단순화 — 수식어 제거 후 핵심어만 재검색
    │ 실패
    ▼
Step B: 영어 쿼리 — 비영어 토픽을 영어로 변환 후 재검색
    │ 실패
    ▼
Step C: 시간 범위 확장 — 48시간 → 7일, 해당 기사에 "[older context]" 레이블 부착
    │ 실패
    ▼
0건 확정 → content_harvest.md에 "Articles after filtering: 0" 기록 후 중단
           (절대 콘텐츠를 조작하거나 없는 기사를 만들지 않음)
```

**출력:** `output/content_harvest.md` — 기사별 Credibility Score(1~10) + Relevance Score(1~10) 포함

---

#### Agent 2: `summarizer_agent` — 3단계 요약

**역할:** harvest 결과를 Relevance Score 내림차순으로 처리하고 각 기사를 3개 계층의 요약으로 변환한다.

```
content_harvest.md 수신 (context_carryover)
    │
    ▼
Relevance Score 내림차순 정렬
    │
    ▼
각 기사 요약 (3-tier)
  ├─ Headline Summary (≤280자) — 트위터 스타일, 핵심 수치 포함
  ├─ Executive Summary (150~200단어) — 사실 기반, 객관적
  └─ Comprehensive Summary (400~600단어) — 배경·맥락·전망 포함
       │
       └─ 기사 본문이 누락되거나 truncate된 경우에만 web_search_tool 재호출
          (fallback, 기본 경로가 아님)
    │
    ▼
각 기사 끝에 Key Takeaways 3개 bullet 추가
```

**출력:** `output/summary.md`

---

#### Agent 3: `curator_agent` — 최종 리포트 조합

**역할:** 요약 결과를 하나의 이메일 발송용 뉴스 브리핑으로 편집한다.

```
summary.md 수신
    │
    ▼
Lead Story 선정
  기준: (Relevance + Credibility) 합산 최고점
  동점 시: Relevance 우선
    │
    ▼
"Today at a Glance" 작성 — 기사당 1줄 요약
    │
    ▼
나머지 기사를 콘텐츠 테마에 따라 동적 섹션 분류
  (미리 정해진 카테고리 없음 — 실제 기사 내용에서 섹션 도출)
    │
    ▼
각 섹션에 편집자 도입 문장 작성 (2~3문장)
    │
    ▼
"Analysis and Outlook" 작성
  — 200~300단어 단일 단락
  — 크로스 스토리 테마 종합 + 향후 전망
    │
    ▼
출력 형식 강제 규칙
  ✅ 반드시 "# Daily News Briefing: {topic}" 으로 시작
  ✅ 표준 마크다운 헤딩만 사용 (##, ###)
  ❌ 코드 펜스 사용 금지
  ❌ 메타 텍스트·설명문 포함 금지
  ❌ Further Reading 섹션 추가 금지
  ❌ 이모지 사용 금지
```

**리소스 제한 (LLM 컨텍스트 오버플로 방지):**
- `max_iter=8` — LLM 반복 상한
- `max_retry_limit=1` — 오류 시 재시도 최대 1회

**출력:** `output/final_report.md`

---

### 3단계 — 결과 검증 (`_run_for_topic`)

CrewAI 파이프라인 완료 후 이메일 발송 전에 3단계 가드를 통과해야 한다.

```
① 제로 기사 가드
   content_harvest.md에 "Articles after filtering: 0" 포함?
   → True : 이메일 건너뜀 (⚠️ WARNING 로그)
   → False: 다음 단계

② 리포트 파일 존재 가드
   output/final_report.md 파일 없음?
   → True : 이메일 건너뜀 (❌ ERROR 로그)
   → False: 다음 단계

③ 리포트 최소 길이 가드
   report 길이 < 300자?
   → True : 이메일 건너뜀 (❌ ERROR 로그)
   → False: report_md 반환 → 이메일 발송 진행
```

---

### 4단계 — 번역 (선택적)

`target_lang != "en"` 인 구독자에 대해서만 실행된다.

```
report_md (영어)
    │
    ▼
_protect_urls() — 마크다운 링크의 URL을 플레이스홀더로 치환
  ([text](https://...) → [text](URLPLACEHOLDER0))
    │
    ▼
_split_into_chunks() — 4500자 단위로 분할
  (Google Translate API 5000자 제한 대응)
    │
    ▼
GoogleTranslator.translate(chunk) — 청크별 번역
    ├─ 빈 번역 반환 → 원문 유지 (⚠️ WARNING)
    └─ 예외 발생  → 해당 청크 원문 유지 후 계속
    │
    ▼
_restore_urls() — 플레이스홀더를 원본 URL로 복원
    │
    ▼
번역 실패 전체 예외 발생 시
→ scheduler에서 catch → translation skipped 경고 로그
→ 영어 원문으로 이메일 발송 진행
```

---

### 5단계 — 이메일 발송 (`send_email_to_subscriber`)

```
report_md (번역 완료 또는 영어 원문)
    │
    ▼
markdown2.markdown() → HTML 변환
  extras: fenced-code-blocks, tables, header-ids
    │
    ▼
_build_html() — inline CSS HTML 이메일 템플릿 조합
  헤더: 주제 + 날짜
  본문: 변환된 HTML
  푸터: 구독 취소 링크
    │
    ▼
resend.Emails.send()
  headers:
    List-Unsubscribe: <{unsubscribe_url}>
    List-Unsubscribe-Post: List-Unsubscribe=One-Click  ← RFC 8058 원클릭 수신거부
    │
    ├─ 성공 → ✅ INFO 로그
    └─ 실패 → ❌ ERROR 로그, 다음 구독자 계속 처리
```

---

## 아키텍처

```
Next.js (frontend/)
    └─ 구독 폼 → FastAPI 백엔드

FastAPI (api/)
    ├─ POST /subscriptions       구독 생성
    ├─ GET  /subscriptions       이메일로 목록 조회
    ├─ PATCH /subscriptions/{id} 활성화/비활성화
    ├─ DELETE /subscriptions/{id}
    └─ GET /subscriptions/unsubscribe?token= 수신거부

subscription_scheduler.py (매분 체크)
    ├─ db.get_due_subscriptions(HH:MM)
    ├─ 동일 토픽 그룹핑 → main.run_crew() 1회 실행
    └─ 번역(선택) → 이메일 발송

Supabase (PostgreSQL)
    └─ subscriptions 테이블
```

---

## 빠른 시작

**1. 의존성 설치**

```bash
uv sync
```

**2. 환경변수 설정**

`.env` 파일을 생성하고 아래 환경변수 섹션을 참고해 값을 채운다.

**3. FastAPI 서버 실행**

```bash
uv run uvicorn api.main:app --reload
```

**4. 구독 스케줄러 실행** (별도 터미널)

```bash
uv run python subscription_scheduler.py
```

**5. 프론트엔드 실행** (별도 터미널)

```bash
cd frontend && npm run dev
```

---

## 환경변수

| 변수명 | 설명 | 필수 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 (CrewAI LLM 백엔드) | ✅ |
| `FIRECRAWL_API_KEY` | Firecrawl API 키 (웹 검색·스크래핑) | ✅ |
| `SUPABASE_URL` | Supabase 프로젝트 URL | ✅ |
| `SUPABASE_KEY` | Supabase **service_role** 키 (서버 전용) | ✅ |
| `GMAIL_SENDER` | 발신자 Gmail 주소 | ✅ |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (16자리) | ✅ |
| `NEWS_TOPIC` | `main.py` 직접 실행 시 기본 토픽 | 선택 |

### 프론트엔드 환경변수 (`frontend/.env.local`)

| 변수명 | 값 |
|---|---|
| `NEXT_PUBLIC_API_URL` | FastAPI 서버 URL (로컬: `http://localhost:8000`) |

---

## 유용한 명령어

```bash
# 파이프라인 1회 수동 실행
uv run python main.py

# 구독 파이프라인 1회 수동 실행 (스케줄러 없이)
uv run python -c "from subscription_scheduler import run_once; run_once()"

# 테스트 실행
uv run pytest tests/
```

---

## Render 배포 시 주의사항

### ★ SMTP 불가 → Resend API 사용
Render는 스팸 방지 목적으로 아웃바운드 SMTP 포트(25, 465, 587)를 전부 차단한다. `smtplib`로 어떤 포트를 써도 `[Errno 101] Network is unreachable` 또는 `timed out` 에러가 발생한다.

**해결:** `smtplib` 대신 Resend SDK 사용. Resend는 `api.resend.com`에 HTTPS(443) 요청을 보내므로 Render에서 차단되지 않는다.

필요한 환경변수:
- `RESEND_API_KEY`: Resend 대시보드에서 발급
- `RESEND_SENDER`: 인증된 도메인의 발신자 주소 (예: `noreply@yourdomain.com`)

### ★ CrewAI tracing 프롬프트 hang
CrewAI는 초기 실행 시 tracing 설정 파일(`~/.config/crewai/settings.json`)이 없으면 사용자 입력을 기다린다. Render의 백그라운드 스레드(non-TTY) 환경에서는 이 프롬프트가 무한 대기 상태가 된다. 새 컨테이너 빌드 시마다 설정 파일이 초기화되므로 코드에서 직접 비활성화해야 한다.

```python
# pipeline/run.py — crewai import 전에 설정
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
```

### ★ LLM 컨텍스트 128K 초과
`content_harvesting_task`는 3~4개 쿼리를 실행하고 각 쿼리마다 여러 기사를 스크래핑한다. 각 tool 호출 결과가 LLM conversation history에 누적되기 때문에, **기사 본문을 LLM에게 짧게 출력하라고 지시해도 소용없다** — tool 반환값 자체가 이미 context를 소비한다.

예: 4쿼리 × 5결과 × 1500단어 ≈ 40000토큰. 시스템 프롬프트·task 설명 누적 → 128K 초과.

**해결:** tool 레벨(`web_search_tool`)에서 반환 전에 직접 truncate.
- `max_results=3` (쿼리당 결과 수)
- 기사 본문 최대 **1500단어** 제한
- tasks.yaml: 최종 선택 기사 최대 **7개**

이렇게 하면 최악의 경우 4쿼리 × 3결과 × 1500단어 ≈ 24000토큰으로 제한된다.

---

## 기술 선택 이유

### 왜 CrewAI인가
뉴스 처리는 수집 → 요약 → 큐레이션의 독립적인 3단계로 분리된다. 단일 LLM 호출로 세 작업을 한 번에 처리하면 컨텍스트가 너무 길어져 품질이 떨어진다. CrewAI는 각 단계를 전용 Agent에 위임하고 결과물을 파이프라인으로 연결하기 때문에, 각 Agent가 하나의 역할에만 집중할 수 있다.

### 왜 Supabase인가
PostgreSQL 기반의 managed DB를 프리티어에서 즉시 사용할 수 있다. Row Level Security(RLS)로 데이터 접근 제어를 DB 레벨에서 처리할 수 있고, 직접 PostgreSQL 서버를 운영하는 것보다 설정 비용이 낮다.

### 왜 FastAPI 서버를 별도로 두는가
Supabase `service_role` 키(RLS 우회 권한)를 브라우저에 노출하지 않기 위해서다. FastAPI를 중간에 두면 민감한 키는 서버에만 존재하고, 비즈니스 로직(구독 중복 검사, 스케줄러 트리거 등)을 한 곳에서 관리할 수 있다.

### 왜 Resend인가 (이메일 발송)
Render 서버는 아웃바운드 SMTP 포트를 전부 차단하기 때문에 `smtplib`(Gmail SMTP)으로 이메일을 보낼 수 없다. Resend는 HTTPS API 기반이라 포트 제한 없이 동작하고, 도메인 인증 후 자체 도메인 주소로 발송할 수 있다.

### 왜 이메일 발송인가
뉴스 브리핑은 정해진 시각에 푸시되어야 하는 비동기 콘텐츠다. 이메일은 수신자가 오프라인이어도 전달되고, 별도 앱 설치 없이 모든 기기에서 읽을 수 있다.

### 왜 스케줄러가 필요한가
구독자마다 설정 시각이 다르고, 서버가 재시작돼도 예약이 유지되어야 한다. DB에 `schedule_time`을 저장하고 매분 체크하는 방식은 외부 큐(Celery, SQS 등) 없이도 동작하며, 스케일이 작은 MVP 단계에서 가장 단순한 구현이다.

### 왜 Next.js + TypeScript인가
FastAPI 백엔드가 타입이 있는 Pydantic 모델을 쓰기 때문에, 프론트도 TypeScript로 맞추면 API 응답 타입을 공유할 수 있다. Next.js App Router의 Server Components를 쓰면 클라이언트 waterfall 없이 서버에서 직접 fetch하여 초기 렌더링 속도를 높인다.

### 왜 Render인가 (백엔드 배포)
FastAPI + 스케줄러를 함께 돌리려면 상시 구동 서버가 필요하다. Vercel은 서버리스(함수 단위)라 스케줄러 상시 실행이 불가능하다. Render의 Web Service는 컨테이너를 상시 유지하므로 `subscription_scheduler.py`가 계속 실행된다.
