import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class BrightDataTool:
    """Client for Bright Data SERP and web scraping API."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def search(self, query: str, country: str = "us", language: str = "en") -> list[dict]:
        """
        Perform a SERP search via Bright Data.
        Returns list of search results or empty list if not configured.
        """
        if not settings.brightdata_api_token:
            logger.debug("Bright Data not configured — skipping SERP search")
            return []

        try:
            client = self._get_client()
            response = await client.post(
                "https://api.brightdata.com/serp/req",
                headers={
                    "Authorization": f"Bearer {settings.brightdata_api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "country": country,
                    "language": language,
                    "zone": settings.brightdata_zone or "serp",
                },
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Bright Data SERP: {len(data.get('results', []))} results for '{query}'")
                return data.get("results", [])
            else:
                logger.warning(f"Bright Data SERP failed: {response.status_code}")
                return []

        except Exception as e:
            logger.warning(f"Bright Data search failed: {e}")
            return []

    async def scrape_url(self, url: str) -> str | None:
        """
        Scrape a URL via Bright Data proxy.
        Returns page HTML or None.
        """
        if not settings.brightdata_api_token:
            return None

        try:
            client = self._get_client()
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {settings.brightdata_api_token}",
                },
            )
            if response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            logger.warning(f"Bright Data scrape failed: {e}")
            return None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
brightdata = BrightDataTool()
