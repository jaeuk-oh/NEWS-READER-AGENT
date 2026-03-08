from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend import db

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


_VALID_LANGS = {"ko", "en", "ja", "zh-CN", "es", "fr", "de"}


class SubscriptionCreate(BaseModel):
    email: EmailStr
    topic: str = Field(min_length=1, max_length=200)
    schedule_time: str
    target_lang: str = "ko"

    @field_validator("schedule_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not _TIME_RE.match(v):
            raise ValueError("schedule_time must be HH:MM format")
        hh, mm = int(v[:2]), int(v[3:])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError("schedule_time out of range")
        return v

    @field_validator("target_lang")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        if v not in _VALID_LANGS:
            raise ValueError(f"target_lang must be one of {sorted(_VALID_LANGS)}")
        return v


class SubscriptionUpdate(BaseModel):
    is_active: bool


@router.post("", status_code=201)
def create_subscription(body: SubscriptionCreate) -> dict:
    try:
        return db.add_subscription(body.email, body.topic, body.schedule_time, body.target_lang)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("")
def list_subscriptions(
    email: Annotated[str | None, Query()] = None,
) -> list[dict]:
    if email:
        return db.get_subscriptions_by_email(email)
    return db.get_subscriptions()


@router.patch("/{subscription_id}")
def update_subscription(subscription_id: str, body: SubscriptionUpdate) -> dict:
    try:
        if body.is_active:
            return db.activate_subscription(subscription_id)
        return db.deactivate_subscription(subscription_id)
    except (IndexError, Exception) as e:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {e}")


@router.delete("/{subscription_id}", status_code=204)
def remove_subscription(subscription_id: str) -> None:
    db.delete_subscription(subscription_id)
