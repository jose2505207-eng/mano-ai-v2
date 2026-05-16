from .base import BrowserProvider

# Lazy imports — Playwright is only loaded when actually needed
# from .playwright_provider import PlaywrightProvider
# from .actionbook_provider import ActionbookProvider
# from .manager import BrowserManager


def __getattr__(name):
    """Lazy-load browser modules to avoid Playwright import at startup."""
    if name == "PlaywrightProvider":
        from .playwright_provider import PlaywrightProvider
        return PlaywrightProvider
    if name == "ActionbookProvider":
        from .actionbook_provider import ActionbookProvider
        return ActionbookProvider
    if name == "BrowserManager":
        from .manager import BrowserManager
        return BrowserManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BrowserProvider",
    "PlaywrightProvider",
    "ActionbookProvider",
    "BrowserManager",
]
