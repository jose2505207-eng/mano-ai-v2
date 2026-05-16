import asyncio
import json
import logging
from typing import Any

from .base import BrowserProvider
from app.schemas.web_task import BrowserSnapshot, BrowserElement, ActionDecision, ActionResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# JSON-RPC request ID counter
_rpc_id = 0


def _next_id() -> int:
    global _rpc_id
    _rpc_id += 1
    return _rpc_id


class ActionbookProvider(BrowserProvider):
    """Browser provider using Actionbook MCP subprocess.

    Communicates with the Actionbook MCP server via JSON-RPC over stdio.
    Methods that cannot be meaningfully implemented via Actionbook
    (observe, screenshot) provide reasonable fallbacks.
    """

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Start the Actionbook MCP server as a subprocess."""
        try:
            self._process = await asyncio.create_subprocess_exec(
                settings.actionbook_cli_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info("Actionbook MCP process started (pid=%s)", self._process.pid)
        except Exception as e:
            logger.error(f"Failed to start Actionbook: {e}")
            raise

    # ------------------------------------------------------------------
    # JSON-RPC transport
    # ------------------------------------------------------------------

    async def _send_command(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC command and read the response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("Actionbook process not running")

        msg_id = _next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params or {},
        }
        data = json.dumps(payload) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

        # Read a single line response
        response_line = await self._process.stdout.readline()
        if not response_line:
            raise RuntimeError("Actionbook returned empty response")

        response = json.loads(response_line.decode())
        if "error" in response:
            raise RuntimeError(f"Actionbook error: {response['error']}")
        return response.get("result", {})

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    async def navigate(self, url: str) -> ActionResult:
        try:
            result = await self._send_command("browser/navigate", {"url": url})
            return ActionResult(
                success=True,
                message=f"Navigated to {url}",
                snapshot_summary=result.get("title"),
            )
        except Exception as e:
            logger.error(f"Actionbook navigate error: {e}")
            return ActionResult(success=False, message=f"Navigate failed: {e}")

    async def click(self, ref: str) -> ActionResult:
        try:
            await self._send_command("browser/click", {"ref": ref})
            return ActionResult(success=True, message=f"Clicked element {ref}")
        except Exception as e:
            logger.error(f"Actionbook click error: {e}")
            return ActionResult(success=False, message=f"Click failed: {e}")

    async def fill(self, ref: str, value: str) -> ActionResult:
        try:
            await self._send_command("browser/fill", {"ref": ref, "value": value})
            return ActionResult(
                success=True,
                message=f"Filled {ref} with '{value}'",
            )
        except Exception as e:
            logger.error(f"Actionbook fill error: {e}")
            return ActionResult(success=False, message=f"Fill failed: {e}")

    async def select(self, ref: str, value: str) -> ActionResult:
        try:
            await self._send_command("browser/select", {"ref": ref, "value": value})
            return ActionResult(
                success=True,
                message=f"Selected '{value}' in element {ref}",
            )
        except Exception as e:
            logger.error(f"Actionbook select error: {e}")
            return ActionResult(success=False, message=f"Select failed: {e}")

    async def scroll(self, direction: str = "down") -> ActionResult:
        try:
            await self._send_command("browser/scroll", {"direction": direction})
            return ActionResult(
                success=True,
                message=f"Scrolled {direction}",
            )
        except Exception as e:
            logger.error(f"Actionbook scroll error: {e}")
            return ActionResult(success=False, message=f"Scroll failed: {e}")

    async def wait(self, seconds: float = 2.0) -> ActionResult:
        try:
            await asyncio.sleep(seconds)
            return ActionResult(success=True, message=f"Waited {seconds}s")
        except Exception as e:
            logger.error(f"Actionbook wait error: {e}")
            return ActionResult(success=False, message=f"Wait failed: {e}")

    async def extract(self) -> ActionResult:
        try:
            result = await self._send_command("browser/extract")
            return ActionResult(
                success=True,
                message=f"Extracted {len(result.get('text', ''))} characters",
                snapshot_summary=result.get("text", ""),
            )
        except Exception as e:
            logger.error(f"Actionbook extract error: {e}")
            return ActionResult(success=False, message=f"Extract failed: {e}")

    async def screenshot(self) -> str | None:
        """Actionbook does not expose a reliable screenshot API."""
        try:
            result = await self._send_command("browser/screenshot")
            return result.get("data")
        except Exception as e:
            logger.warning(f"Actionbook screenshot failed (non-fatal): {e}")
            return None

    async def observe(self) -> BrowserSnapshot:
        """Actionbook does not provide structured snapshots natively.

        Attempt to extract what we can via JSON-RPC, otherwise
        return a minimal snapshot.
        """
        try:
            result = await self._send_command("browser/observe")
            elements = [
                BrowserElement(**el) for el in result.get("elements", [])
            ]
            return BrowserSnapshot(
                url=result.get("url", "about:blank"),
                title=result.get("title"),
                text_summary=result.get("text", "")[:5000],
                elements=elements,
                screenshot=result.get("screenshot"),
            )
        except Exception as e:
            logger.error(f"Actionbook observe error: {e}")
            return BrowserSnapshot(
                url="about:blank",
                title=None,
                text_summary=f"Observe failed: {e}",
                elements=[],
                screenshot=None,
            )

    async def execute_action(self, decision: ActionDecision) -> ActionResult:
        try:
            match decision.kind:
                case "navigate":
                    return await self.navigate(decision.url or decision.value or "")
                case "click":
                    return await self.click(decision.ref or "")
                case "fill":
                    return await self.fill(decision.ref or "", decision.value or "")
                case "select":
                    return await self.select(decision.ref or "", decision.value or "")
                case "scroll":
                    return await self.scroll(decision.value or "down")
                case "wait":
                    return await self.wait(float(decision.value or "2"))
                case "extract":
                    return await self.extract()
                case "search_web":
                    import urllib.parse
                    query = urllib.parse.quote_plus(decision.value or "")
                    return await self.navigate(f"https://www.google.com/search?q={query}")
                case _:
                    return ActionResult(
                        success=False,
                        message=f"Unknown action kind: {decision.kind}",
                    )
        except Exception as e:
            logger.error(f"Actionbook execute_action error: {e}")
            return ActionResult(
                success=False,
                message=f"Action execution failed: {e}",
            )

    async def close(self) -> None:
        try:
            if self._process:
                self._process.terminate()
                await self._process.wait()
        except Exception as e:
            logger.error(f"Actionbook close error: {e}")
        finally:
            self._process = None
