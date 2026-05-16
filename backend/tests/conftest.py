import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_profile():
    return {
        "full_name": "Jose Ivan Zaragoza",
        "email": "jose@example.com",
        "phone": "408-555-0100",
        "date_of_birth": "2004-06-11",
        "address": "123 Main St, San Jose, CA",
        "preferred_language": "en",
        "preferred_airport": "SFO",
        "payment_allowed": False,
    }
