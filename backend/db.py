import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SubscriptionNotFoundError(Exception):
    """지정한 구독 ID가 DB에 존재하지 않을 때 발생하는 예외."""


# 모듈 수준에서 Supabase 클라이언트를 캐싱 (최초 호출 시 1회 생성)
_client: Client | None = None


def _get_client() -> Client:
    """캐싱된 Supabase 클라이언트를 반환한다. 최초 호출 시 생성."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


# Supabase 테이블명
TABLE = "subscriptions"


def add_subscription(email: str, topic: str, schedule_time: str, target_lang: str = "ko") -> dict:
    """새 구독을 추가한다.

    Args:
        email: 구독자 이메일 주소.
        topic: 뉴스 주제 / 키워드.
        schedule_time: 발송 시각 (HH:MM 형식).
        target_lang: 번역 언어 BCP-47 코드 (예: "ko", "en", "ja").

    Returns:
        삽입된 행(dict).

    Raises:
        ValueError: 동일한 email+topic 조합이 이미 존재하는 경우.
    """
    client = _get_client()

    # 중복 구독 여부 확인
    existing = (
        client.table(TABLE)
        .select("id")
        .eq("email", email)
        .eq("topic", topic)
        .execute()
    )
    if existing.data:
        raise ValueError(f"Subscription already exists for {email} + '{topic}'")

    result = (
        client.table(TABLE)
        .insert({"email": email, "topic": topic, "schedule_time": schedule_time, "target_lang": target_lang})
        .execute()
    )
    logger.info(f"Subscription added: {email} / {topic} / {schedule_time} / lang={target_lang}")
    return result.data[0]


def get_subscriptions() -> list[dict]:
    """모든 구독 목록을 반환한다."""
    client = _get_client()
    result = client.table(TABLE).select("*").execute()
    return result.data


def get_due_subscriptions(current_time: str) -> list[dict]:
    """지정 시각(HH:MM)과 일치하는 활성 구독 목록을 반환한다.

    Args:
        current_time: HH:MM 형식의 시각 문자열.
    """
    client = _get_client()
    result = (
        client.table(TABLE)
        .select("*")
        .eq("schedule_time", current_time)
        .eq("is_active", True)
        .execute()
    )
    return result.data


def get_due_subscriptions_for_hour(hour: str) -> list[dict]:
    """지정 시간대(HH) 내 모든 활성 구독을 반환한다.

    Args:
        hour: 두 자리 시간 문자열 (예: "07", "14").

    Returns:
        schedule_time이 HH:00 ~ HH:59 사이인 활성 구독 목록.
    """
    client = _get_client()
    result = (
        client.table(TABLE)
        .select("*")
        .gte("schedule_time", f"{hour}:00")
        .lte("schedule_time", f"{hour}:59")
        .eq("is_active", True)
        .execute()
    )
    return result.data


def deactivate_subscription(subscription_id: str) -> dict:
    """구독을 비활성화한다 (is_active=False).

    Raises:
        SubscriptionNotFoundError: 해당 ID의 구독이 존재하지 않는 경우.
    """
    client = _get_client()
    result = (
        client.table(TABLE)
        .update({"is_active": False})
        .eq("id", subscription_id)
        .execute()
    )
    # 업데이트 결과가 비어있으면 해당 ID가 없는 것
    if not result.data:
        raise SubscriptionNotFoundError(subscription_id)
    logger.info(f"Subscription deactivated: {subscription_id}")
    return result.data[0]


def activate_subscription(subscription_id: str) -> dict:
    """구독을 활성화한다 (is_active=True).

    Raises:
        SubscriptionNotFoundError: 해당 ID의 구독이 존재하지 않는 경우.
    """
    client = _get_client()
    result = (
        client.table(TABLE)
        .update({"is_active": True})
        .eq("id", subscription_id)
        .execute()
    )
    # 업데이트 결과가 비어있으면 해당 ID가 없는 것
    if not result.data:
        raise SubscriptionNotFoundError(subscription_id)
    logger.info(f"Subscription activated: {subscription_id}")
    return result.data[0]


def delete_subscription(subscription_id: str) -> None:
    """구독을 영구 삭제한다.

    Raises:
        SubscriptionNotFoundError: 해당 ID의 구독이 존재하지 않는 경우.
    """
    client = _get_client()
    # 삭제 전 존재 여부 확인 (없으면 예외 발생)
    existing = client.table(TABLE).select("id").eq("id", subscription_id).execute()
    if not existing.data:
        raise SubscriptionNotFoundError(subscription_id)
    client.table(TABLE).delete().eq("id", subscription_id).execute()
    logger.info(f"Subscription deleted: {subscription_id}")


def get_subscriptions_by_email(email: str) -> list[dict]:
    """특정 이메일의 모든 구독 목록을 반환한다."""
    client = _get_client()
    result = client.table(TABLE).select("*").eq("email", email).execute()
    return result.data


def deactivate_by_unsubscribe_token(token: str) -> dict:
    """unsubscribe_token으로 구독을 비활성화한다.

    이메일 본문의 구독 취소 링크에서 호출된다.
    토큰은 구독 생성 시 Supabase가 자동 생성한 UUID이다.

    Raises:
        SubscriptionNotFoundError: 토큰과 일치하는 활성 구독이 없는 경우.
    """
    client = _get_client()
    # 토큰으로 활성 구독을 조회한 뒤 비활성화
    result = (
        client.table(TABLE)
        .update({"is_active": False})
        .eq("unsubscribe_token", token)
        .eq("is_active", True)  # 이미 취소된 구독은 제외
        .execute()
    )
    if not result.data:
        raise SubscriptionNotFoundError(token)
    logger.info(f"Subscription cancelled via token: {token}")
    return result.data[0]
