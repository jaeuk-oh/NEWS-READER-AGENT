"""구독 API 엔드포인트 단위 테스트.

각 테스트는 실제 DB에 접근하지 않으며, mock_db 픽스처로 db 함수를 모킹한다.
"""
import pytest
from backend.db import SubscriptionNotFoundError

# ── 공통 테스트 데이터 ──────────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "email": "test@example.com",
    "topic": "AI",
    "schedule_time": "09:00",
    "target_lang": "ko",
}

SAMPLE_ROW = {
    "id": "uuid-1234",
    "email": "test@example.com",
    "topic": "AI",
    "schedule_time": "09:00",
    "target_lang": "ko",
    "is_active": True,
}


# ── POST /subscriptions ────────────────────────────────────────────────────────

class TestCreateSubscription:
    def test_성공_201_반환(self, client, mock_db):
        """유효한 요청 시 201과 생성된 구독 데이터를 반환해야 한다."""
        mock_db.add_subscription.return_value = SAMPLE_ROW

        res = client.post("/subscriptions", json=VALID_PAYLOAD)

        assert res.status_code == 201
        assert res.json()["email"] == "test@example.com"
        mock_db.add_subscription.assert_called_once_with(
            "test@example.com", "AI", "09:00", "ko"
        )

    def test_중복_구독_409_반환(self, client, mock_db):
        """동일 email+topic 조합이 이미 존재하면 409를 반환해야 한다."""
        mock_db.add_subscription.side_effect = ValueError("already exists")

        res = client.post("/subscriptions", json=VALID_PAYLOAD)

        assert res.status_code == 409

    def test_잘못된_이메일_422_반환(self, client, mock_db):
        """이메일 형식이 잘못되면 422를 반환해야 한다."""
        payload = {**VALID_PAYLOAD, "email": "not-an-email"}
        res = client.post("/subscriptions", json=payload)
        assert res.status_code == 422

    def test_잘못된_schedule_time_형식_422(self, client, mock_db):
        """HH:MM 형식이 아닌 schedule_time은 422를 반환해야 한다."""
        payload = {**VALID_PAYLOAD, "schedule_time": "9:0"}
        res = client.post("/subscriptions", json=payload)
        assert res.status_code == 422

    def test_범위_벗어난_schedule_time_422(self, client, mock_db):
        """25:00 같이 범위를 벗어난 시각은 422를 반환해야 한다."""
        payload = {**VALID_PAYLOAD, "schedule_time": "25:00"}
        res = client.post("/subscriptions", json=payload)
        assert res.status_code == 422

    def test_지원하지_않는_언어_422(self, client, mock_db):
        """지원 목록에 없는 target_lang은 422를 반환해야 한다."""
        payload = {**VALID_PAYLOAD, "target_lang": "xx"}
        res = client.post("/subscriptions", json=payload)
        assert res.status_code == 422

    def test_빈_topic_422(self, client, mock_db):
        """topic이 빈 문자열이면 422를 반환해야 한다."""
        payload = {**VALID_PAYLOAD, "topic": ""}
        res = client.post("/subscriptions", json=payload)
        assert res.status_code == 422


# ── GET /subscriptions ─────────────────────────────────────────────────────────

class TestListSubscriptions:
    def test_전체_목록_반환(self, client, mock_db):
        """email 파라미터 없이 호출하면 전체 구독 목록을 반환해야 한다."""
        mock_db.get_subscriptions.return_value = [SAMPLE_ROW]

        res = client.get("/subscriptions")

        assert res.status_code == 200
        assert len(res.json()) == 1
        mock_db.get_subscriptions.assert_called_once()

    def test_이메일_필터링(self, client, mock_db):
        """email 쿼리 파라미터가 있으면 해당 이메일 구독만 반환해야 한다."""
        mock_db.get_subscriptions_by_email.return_value = [SAMPLE_ROW]

        res = client.get("/subscriptions?email=test@example.com")

        assert res.status_code == 200
        mock_db.get_subscriptions_by_email.assert_called_once_with("test@example.com")

    def test_빈_목록_반환(self, client, mock_db):
        """구독이 없으면 빈 배열을 반환해야 한다."""
        mock_db.get_subscriptions.return_value = []

        res = client.get("/subscriptions")

        assert res.status_code == 200
        assert res.json() == []


# ── PATCH /subscriptions/{id} ─────────────────────────────────────────────────

class TestUpdateSubscription:
    def test_활성화_성공(self, client, mock_db):
        """is_active=true 요청 시 activate_subscription을 호출하고 200을 반환해야 한다."""
        mock_db.activate_subscription.return_value = {**SAMPLE_ROW, "is_active": True}

        res = client.patch("/subscriptions/uuid-1234", json={"is_active": True})

        assert res.status_code == 200
        mock_db.activate_subscription.assert_called_once_with("uuid-1234")

    def test_비활성화_성공(self, client, mock_db):
        """is_active=false 요청 시 deactivate_subscription을 호출하고 200을 반환해야 한다."""
        mock_db.deactivate_subscription.return_value = {**SAMPLE_ROW, "is_active": False}

        res = client.patch("/subscriptions/uuid-1234", json={"is_active": False})

        assert res.status_code == 200
        mock_db.deactivate_subscription.assert_called_once_with("uuid-1234")

    def test_존재하지_않는_ID_404(self, client, mock_db):
        """존재하지 않는 ID로 PATCH하면 404를 반환해야 한다."""
        mock_db.activate_subscription.side_effect = SubscriptionNotFoundError("no-such-id")

        res = client.patch("/subscriptions/no-such-id", json={"is_active": True})

        assert res.status_code == 404

    def test_DB_오류_500(self, client, mock_db):
        """DB 연결 오류 등 예기치 않은 예외 발생 시 500을 반환해야 한다."""
        mock_db.activate_subscription.side_effect = RuntimeError("db connection failed")

        res = client.patch("/subscriptions/uuid-1234", json={"is_active": True})

        assert res.status_code == 500


# ── DELETE /subscriptions/{id} ────────────────────────────────────────────────

class TestDeleteSubscription:
    def test_삭제_성공_204(self, client, mock_db):
        """존재하는 ID 삭제 시 204를 반환하고 delete_subscription을 호출해야 한다."""
        mock_db.delete_subscription.return_value = None

        res = client.delete("/subscriptions/uuid-1234")

        assert res.status_code == 204
        mock_db.delete_subscription.assert_called_once_with("uuid-1234")

    def test_존재하지_않는_ID_404(self, client, mock_db):
        """존재하지 않는 ID 삭제 시 404를 반환해야 한다."""
        mock_db.delete_subscription.side_effect = SubscriptionNotFoundError("no-such-id")

        res = client.delete("/subscriptions/no-such-id")

        assert res.status_code == 404
