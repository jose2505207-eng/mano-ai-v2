import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BUTTERBASE_URL = "https://api.butterbase.ai"


class ButterbaseTool:
    """Client for Butterbase backend-as-a-service API."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                headers={
                    "Authorization": f"Bearer {settings.butterbase_api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    @property
    def configured(self) -> bool:
        return bool(settings.butterbase_api_key)

    async def store_task(self, task_data: dict) -> dict | None:
        """Store a task record in Butterbase."""
        if not self.configured:
            return None
        try:
            client = self._get_client()
            response = await client.post(
                f"{BUTTERBASE_URL}/v1/records/tasks",
                json=task_data,
            )
            if response.status_code in (200, 201):
                return response.json()
            logger.warning(f"Butterbase store_task failed: {response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Butterbase store_task error: {e}")
            return None

    async def get_task(self, task_id: str) -> dict | None:
        """Retrieve a task record from Butterbase."""
        if not self.configured:
            return None
        try:
            client = self._get_client()
            response = await client.get(f"{BUTTERBASE_URL}/v1/records/tasks/{task_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.warning(f"Butterbase get_task error: {e}")
            return None

    async def list_tasks(self, limit: int = 50) -> list[dict]:
        """List recent task records."""
        if not self.configured:
            return []
        try:
            client = self._get_client()
            response = await client.get(
                f"{BUTTERBASE_URL}/v1/records/tasks",
                params={"limit": limit, "sort": "-created_at"},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("records", data.get("data", []))
            return []
        except Exception as e:
            logger.warning(f"Butterbase list_tasks error: {e}")
            return []

    async def store_profile(self, profile_data: dict) -> dict | None:
        """Store user profile in Butterbase."""
        if not self.configured:
            return None
        try:
            client = self._get_client()
            response = await client.post(
                f"{BUTTERBASE_URL}/v1/records/profiles",
                json=profile_data,
            )
            if response.status_code in (200, 201):
                return response.json()
            return None
        except Exception as e:
            logger.warning(f"Butterbase store_profile error: {e}")
            return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton
butterbase = ButterbaseTool()
