from __future__ import annotations

import re
import uuid
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend import db
from backend.db import SubscriptionNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# HH:MM 형식 검증용 정규식
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")

# 지원하는 번역 언어 목록 (BCP-47 코드)
_VALID_LANGS = {"ko", "en", "ja", "zh-CN", "es", "fr", "de"}


class SubscriptionCreate(BaseModel):
    """구독 생성 요청 스키마."""

    email: EmailStr
    topic: str = Field(min_length=1, max_length=200)
    schedule_time: str
    target_lang: str = "ko"  # 기본값: 한국어

    @field_validator("schedule_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        """발송 시각이 HH:MM 형식이고 유효한 범위인지 검증."""
        if not _TIME_RE.match(v):
            raise ValueError("schedule_time must be HH:MM format")
        hh, mm = int(v[:2]), int(v[3:])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError("schedule_time out of range")
        return v

    @field_validator("target_lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        """target_lang이 지원 목록에 있는지 검증."""
        if v not in _VALID_LANGS:
            raise ValueError(f"target_lang must be one of {sorted(_VALID_LANGS)}")
        return v


class SubscriptionUpdate(BaseModel):
    """구독 활성화 상태 변경 요청 스키마."""

    is_active: bool


@router.post("", status_code=201)
def create_subscription(body: SubscriptionCreate) -> dict:
    """새 구독을 생성한다.

    - 동일한 email+topic 조합이 이미 존재하면 409 반환.
    """
    try:
        return db.add_subscription(body.email, body.topic, body.schedule_time, body.target_lang)
    except ValueError as e:
        # 중복 구독 → 409 Conflict
        raise HTTPException(status_code=409, detail=str(e))


@router.get("")
def list_subscriptions(
    email: Annotated[str | None, Query()] = None,
) -> list[dict]:
    """구독 목록을 반환한다.

    - email 쿼리 파라미터가 있으면 해당 이메일의 구독만 반환.
    - 없으면 전체 구독 목록 반환.
    """
    if email:
        return db.get_subscriptions_by_email(email)
    return db.get_subscriptions()


class InstantRequest(BaseModel):
    """일회성 즉시 발송 요청 스키마."""

    email: EmailStr
    topic: str = Field(min_length=1, max_length=200)
    target_lang: str = "ko"

    @field_validator("target_lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in _VALID_LANGS:
            raise ValueError(f"target_lang must be one of {sorted(_VALID_LANGS)}")
        return v


def _run_instant_pipeline(email: str, topic: str, target_lang: str) -> None:
    """파이프라인을 즉시 실행하고 결과를 이메일로 발송한다."""
    from pipeline.run import run_crew
    from backend.services.notifier import send_email_to_subscriber
    from backend.services.translator import translate_to_TargetLang

    try:
        report_path = run_crew(topic)
        with open(report_path, "r", encoding="utf-8") as f:
            report_md = f.read()

        if target_lang != "en":
            report_md = translate_to_TargetLang(report_md, target_lang)

        token = str(uuid.uuid4())
        send_email_to_subscriber(email, topic, report_md, token)
        logger.info(f"Instant briefing sent to {email} (topic={topic})")
    except Exception as e:
        logger.error(f"Instant pipeline failed for {email}: {e}")


# 정적 경로는 반드시 파라미터 경로 /{id} 보다 앞에 선언해야 FastAPI가 올바르게 매칭함
@router.post("/instant", status_code=202)
def instant_briefing(body: InstantRequest, background_tasks: BackgroundTasks) -> dict:
    """파이프라인을 즉시 실행하고 완료 후 이메일을 발송한다.

    - 파이프라인 실행은 백그라운드에서 처리되며 즉시 202를 반환.
    - 완료까지 수 분이 소요될 수 있음.
    """
    background_tasks.add_task(_run_instant_pipeline, body.email, body.topic, body.target_lang)
    return {"message": "요청을 접수했습니다. 파이프라인 완료 후 이메일로 발송됩니다."}


@router.get("/unsubscribe")
def unsubscribe(token: Annotated[str, Query(min_length=1)]) -> dict:
    """이메일 본문의 구독 취소 링크 처리 엔드포인트.

    - 유효한 토큰 → 구독 비활성화 후 확인 메시지 반환
    - 유효하지 않거나 이미 취소된 토큰 → 404
    """
    try:
        sub = db.deactivate_by_unsubscribe_token(token)
        return {"message": "구독이 취소되었습니다.", "email": sub["email"], "topic": sub["topic"]}
    except SubscriptionNotFoundError:
        # 토큰 불일치 또는 이미 비활성화된 구독
        raise HTTPException(status_code=404, detail="유효하지 않거나 이미 취소된 구독입니다.")


@router.patch("/{subscription_id}")
def update_subscription(subscription_id: str, body: SubscriptionUpdate) -> dict:
    """구독의 활성화 상태를 변경한다 (활성화/비활성화).

    - 존재하지 않는 ID → 404
    - DB 오류 등 서버 내부 문제 → 500
    """
    try:
        if body.is_active:
            return db.activate_subscription(subscription_id)
        return db.deactivate_subscription(subscription_id)
    except SubscriptionNotFoundError:
        # 존재하지 않는 구독 ID → 404
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
    except Exception as e:
        # DB 연결 오류 등 서버 내부 문제 → 500
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.delete("/{subscription_id}", status_code=204)
def remove_subscription(subscription_id: str) -> None:
    """구독을 영구 삭제한다.

    - 존재하지 않는 ID → 404
    """
    try:
        db.delete_subscription(subscription_id)
    except SubscriptionNotFoundError:
        # 존재하지 않는 구독 ID → 404
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
