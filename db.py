import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_client: Client | None = None


def _get_client() -> Client:
    """Return a cached Supabase client (created on first call)."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


TABLE = "subscriptions"


def add_subscription(email: str, topic: str, schedule_time: str) -> dict:
    """Add a new subscription.

    Args:
        email: Subscriber email address.
        topic: News topic / keywords.
        schedule_time: Delivery time in "HH:MM" format.

    Returns:
        The inserted row as a dict.

    Raises:
        ValueError: If the same email+topic combination already exists.
    """
    client = _get_client()

    # Duplicate check
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
        .insert({"email": email, "topic": topic, "schedule_time": schedule_time})
        .execute()
    )
    logger.info(f"Subscription added: {email} / {topic} / {schedule_time}")
    return result.data[0]


def get_subscriptions() -> list[dict]:
    """Return all subscriptions."""
    client = _get_client()
    result = client.table(TABLE).select("*").execute()
    return result.data


def get_due_subscriptions(current_time: str) -> list[dict]:
    """Return active subscriptions matching the given HH:MM time.

    Args:
        current_time: Time string in "HH:MM" format.
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


def deactivate_subscription(subscription_id: str) -> dict:
    """Set is_active=false for the given subscription."""
    client = _get_client()
    result = (
        client.table(TABLE)
        .update({"is_active": False})
        .eq("id", subscription_id)
        .execute()
    )
    logger.info(f"Subscription deactivated: {subscription_id}")
    return result.data[0]


def activate_subscription(subscription_id: str) -> dict:
    """Set is_active=true for the given subscription."""
    client = _get_client()
    result = (
        client.table(TABLE)
        .update({"is_active": True})
        .eq("id", subscription_id)
        .execute()
    )
    logger.info(f"Subscription activated: {subscription_id}")
    return result.data[0]


def delete_subscription(subscription_id: str) -> None:
    """Permanently delete a subscription."""
    client = _get_client()
    client.table(TABLE).delete().eq("id", subscription_id).execute()
    logger.info(f"Subscription deleted: {subscription_id}")


def get_subscriptions_by_email(email: str) -> list[dict]:
    """Return all subscriptions for a specific email."""
    client = _get_client()
    result = client.table(TABLE).select("*").eq("email", email).execute()
    return result.data
