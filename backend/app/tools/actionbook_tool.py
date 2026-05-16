import asyncio
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class ActionbookTool:
    """Client for Actionbook action manual search via MCP subprocess."""

    def __init__(self):
        self._process = None
        self._request_id = 0

    async def search_manual(self, query: str, domain: str | None = None) -> dict | None:
        """
        Search Actionbook for an action manual matching the query.
        Returns manual dict or None if not found/not configured.
        """
        if not settings.actionbook_api_key:
            logger.debug("Actionbook not configured — skipping manual search")
            return None

        try:
            cmd = [settings.actionbook_cli_path, "search", query]
            if domain:
                cmd.extend(["--domain", domain])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"ACTIONBOOK_API_KEY": settings.actionbook_api_key},
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=15.0
            )

            if process.returncode == 0 and stdout:
                result = json.loads(stdout.decode())
                logger.info(f"Actionbook manual found for: {query}")
                return result
            else:
                logger.debug(f"Actionbook search returned no results for: {query}")
                return None

        except asyncio.TimeoutError:
            logger.warning("Actionbook search timed out")
            return None
        except FileNotFoundError:
            logger.warning(f"Actionbook CLI not found at: {settings.actionbook_cli_path}")
            return None
        except Exception as e:
            logger.warning(f"Actionbook search failed: {e}")
            return None

    async def get_manual(self, manual_id: str) -> dict | None:
        """Get a specific action manual by ID."""
        if not settings.actionbook_api_key:
            return None

        try:
            process = await asyncio.create_subprocess_exec(
                settings.actionbook_cli_path, "get", manual_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"ACTIONBOOK_API_KEY": settings.actionbook_api_key},
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=10.0
            )

            if process.returncode == 0 and stdout:
                return json.loads(stdout.decode())
            return None

        except Exception as e:
            logger.warning(f"Actionbook get failed: {e}")
            return None


# Singleton instance
actionbook = ActionbookTool()
