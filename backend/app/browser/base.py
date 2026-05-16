from abc import ABC, abstractmethod

from app.schemas.web_task import BrowserSnapshot, ActionDecision, ActionResult


class BrowserProvider(ABC):
    """Abstract browser provider that all implementations must follow."""

    @abstractmethod
    async def launch(self) -> None:
        """Launch the browser."""
        ...

    @abstractmethod
    async def navigate(self, url: str) -> ActionResult:
        """Navigate to a URL."""
        ...

    @abstractmethod
    async def click(self, ref: str) -> ActionResult:
        """Click an element identified by its ref."""
        ...

    @abstractmethod
    async def fill(self, ref: str, value: str) -> ActionResult:
        """Fill an input field with a value."""
        ...

    @abstractmethod
    async def select(self, ref: str, value: str) -> ActionResult:
        """Select an option in a dropdown."""
        ...

    @abstractmethod
    async def scroll(self, direction: str = "down") -> ActionResult:
        """Scroll the page in a direction."""
        ...

    @abstractmethod
    async def wait(self, seconds: float = 2.0) -> ActionResult:
        """Wait for a specified number of seconds."""
        ...

    @abstractmethod
    async def extract(self) -> ActionResult:
        """Extract text content from the page."""
        ...

    @abstractmethod
    async def screenshot(self) -> str | None:
        """Return base64 JPEG screenshot or None."""
        ...

    @abstractmethod
    async def observe(self) -> BrowserSnapshot:
        """Capture current page state as BrowserSnapshot."""
        ...

    @abstractmethod
    async def execute_action(self, decision: ActionDecision) -> ActionResult:
        """Execute an ActionDecision and return result."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the browser."""
        ...
