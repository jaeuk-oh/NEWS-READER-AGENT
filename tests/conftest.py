"""pytest 공통 픽스처 모음.

실제 Supabase에 연결하지 않도록 db 모듈 전체를 모킹한다.
각 테스트는 독립적으로 mock_db 픽스처를 통해 db 함수를 제어한다.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from backend.api.main import app


@pytest.fixture
def mock_db(monkeypatch):
    """backend.db 의 모든 공개 함수를 MagicMock으로 교체한다.

    테스트에서 mock_db.add_subscription.return_value = {...} 식으로
    반환값을 자유롭게 지정할 수 있다.
    """
    import backend.db as db_module

    mock = MagicMock()
    monkeypatch.setattr(db_module, "add_subscription", mock.add_subscription)
    monkeypatch.setattr(db_module, "get_subscriptions", mock.get_subscriptions)
    monkeypatch.setattr(db_module, "get_subscriptions_by_email", mock.get_subscriptions_by_email)
    monkeypatch.setattr(db_module, "activate_subscription", mock.activate_subscription)
    monkeypatch.setattr(db_module, "deactivate_subscription", mock.deactivate_subscription)
    monkeypatch.setattr(db_module, "delete_subscription", mock.delete_subscription)
    return mock


@pytest.fixture
def client():
    """FastAPI TestClient 픽스처. 각 테스트마다 새로운 클라이언트를 제공한다."""
    return TestClient(app)
