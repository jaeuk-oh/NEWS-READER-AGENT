# News Reader Agent

구독 기반 AI 뉴스 브리핑 시스템. 이메일·주제·발송 시각을 입력하면 CrewAI 멀티 에이전트 파이프라인이 뉴스를 자동으로 수집·요약·큐레이션하여 이메일로 발송한다.

---

## Agent Pipeline

```
[User] email + topic + schedule_time 입력
          ↓
[Scheduler] 매분 DB 확인 → 설정 시각에 트리거
          ↓
[news_hunter_agent]   멀티 쿼리 검색 + 웹 스크래핑 + 점수 산정
          ↓
[summarizer_agent]    3단계 요약 + 핵심 시사점 추출
          ↓
[curator_agent]       점수 기반 리드 선정 + 동적 섹션 구성 + 최종 리포트
          ↓
[Notifier] 이메일 발송 (HTML 템플릿 + 수신거부 링크)
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

### ★ SMTP 포트 + IPv4 강제
Render 서버는 아웃바운드 포트 587(STARTTLS)이 차단되어 있다. `smtplib.SMTP_SSL` + 포트 465를 사용해야 한다.

추가로 Render 컨테이너는 IPv6 라우팅이 없는 경우가 있어, Python이 `smtp.gmail.com`을 IPv6로 resolve하면 `[Errno 101] Network is unreachable`이 발생한다. `socket.getaddrinfo(AF_INET)`으로 IPv4 주소를 명시적으로 선택해야 한다.

```python
ipv4 = socket.getaddrinfo(SMTP_HOST, SMTP_PORT, socket.AF_INET)[0][4][0]
with smtplib.SMTP_SSL(ipv4, SMTP_PORT, timeout=30) as server:
    ...
```

### ★ CrewAI tracing 프롬프트 hang
CrewAI는 초기 실행 시 tracing 설정 파일(`~/.config/crewai/settings.json`)이 없으면 사용자 입력을 기다린다. Render의 백그라운드 스레드(non-TTY) 환경에서는 이 프롬프트가 무한 대기 상태가 된다. 새 컨테이너 빌드 시마다 설정 파일이 초기화되므로 코드에서 직접 비활성화해야 한다.

```python
# pipeline/run.py — crewai import 전에 설정
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
```

### ★ LLM 컨텍스트 128K 초과
`content_harvesting_task`가 기사 전문을 제한 없이 수집하면 `summarization_task` 입력이 128K 토큰을 초과한다. CrewAI 내부 폴백(자동 요약)이 실행되어 수십 분이 소요되거나 Render가 프로세스를 종료한다. 기사 수와 본문 길이를 제한해야 한다.

- 기사 최대 **7개** 선택
- 기사 본문 최대 **1500단어** 제한

---

## 기술 선택 이유

### 왜 CrewAI인가
뉴스 처리는 수집 → 요약 → 큐레이션의 독립적인 3단계로 분리된다. 단일 LLM 호출로 세 작업을 한 번에 처리하면 컨텍스트가 너무 길어져 품질이 떨어진다. CrewAI는 각 단계를 전용 Agent에 위임하고 결과물을 파이프라인으로 연결하기 때문에, 각 Agent가 하나의 역할에만 집중할 수 있다.

### 왜 Supabase인가
PostgreSQL 기반의 managed DB를 프리티어에서 즉시 사용할 수 있다. Row Level Security(RLS)로 데이터 접근 제어를 DB 레벨에서 처리할 수 있고, 직접 PostgreSQL 서버를 운영하는 것보다 설정 비용이 낮다.

### 왜 FastAPI 서버를 별도로 두는가
Supabase `service_role` 키(RLS 우회 권한)를 브라우저에 노출하지 않기 위해서다. FastAPI를 중간에 두면 민감한 키는 서버에만 존재하고, 비즈니스 로직(구독 중복 검사, 스케줄러 트리거 등)을 한 곳에서 관리할 수 있다.

### 왜 이메일 발송인가
뉴스 브리핑은 정해진 시각에 푸시되어야 하는 비동기 콘텐츠다. 이메일은 수신자가 오프라인이어도 전달되고, 별도 앱 설치 없이 모든 기기에서 읽을 수 있다.

### 왜 스케줄러가 필요한가
구독자마다 설정 시각이 다르고, 서버가 재시작돼도 예약이 유지되어야 한다. DB에 `schedule_time`을 저장하고 매분 체크하는 방식은 외부 큐(Celery, SQS 등) 없이도 동작하며, 스케일이 작은 MVP 단계에서 가장 단순한 구현이다.

### 왜 Next.js + TypeScript인가
FastAPI 백엔드가 타입이 있는 Pydantic 모델을 쓰기 때문에, 프론트도 TypeScript로 맞추면 API 응답 타입을 공유할 수 있다. Next.js App Router의 Server Components를 쓰면 클라이언트 waterfall 없이 서버에서 직접 fetch하여 초기 렌더링 속도를 높인다.

### 왜 Render인가 (백엔드 배포)
FastAPI + 스케줄러를 함께 돌리려면 상시 구동 서버가 필요하다. Vercel은 서버리스(함수 단위)라 스케줄러 상시 실행이 불가능하다. Render의 Web Service는 컨테이너를 상시 유지하므로 `subscription_scheduler.py`가 계속 실행된다.
