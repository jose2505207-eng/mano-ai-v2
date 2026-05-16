import asyncio
import base64
import logging
import time
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .base import BrowserProvider
from app.schemas.web_task import BrowserSnapshot, BrowserElement, ActionDecision, ActionResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule 8: Anti-bot stealth init script
# ---------------------------------------------------------------------------
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_ELEMENTS = 80        # Rule 2
MAX_TEXT_LENGTH = 5000    # Rule 3

# ---------------------------------------------------------------------------
# JavaScript: extract interactive elements from the current page
# Implements Rules 1, 2, 4
# ---------------------------------------------------------------------------
OBSERVE_JS = """
(() => {
    const elements = [];
    const selectors = 'a[href], button, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="option"], [role="gridcell"], [role="checkbox"], [role="radio"], [role="combobox"], [role="searchbox"], [role="textbox"], [role="menuitem"], [role="listbox"] > *, [data-iso], [contenteditable="true"], [tabindex="0"]:not(div:not([role])), [data-flt-ve], [jsname][role], [jsname][tabindex], [aria-haspopup], [jsaction], [data-placeholder], mdc-button, mdc-icon-button, mdc-text-field, mdc-menu, mdc-list-item, mdc-dialog';

    // Pierce shadow DOM to find elements inside custom components (Google Flights, etc.)
    function queryAllIncludingShadow(root, sel) {
        let results = Array.from(root.querySelectorAll(sel));
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) {
                results = results.concat(queryAllIncludingShadow(el.shadowRoot, sel));
            }
        });
        return results;
    }

    const allEls = queryAllIncludingShadow(document, selectors);
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    // Detect if page has main content (product/results area)
    const hasMainContent = !!document.querySelector('main, [role="main"], #main, .main-content, .search-results, .product-list, .results-list, [data-component-type="s-search-result"]');

    allEls.forEach((el, i) => {
        if (i >= 200) return;  // gather extra then trim after sort
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        const visible = rect.width > 0 && rect.height > 0
                        && style.visibility !== 'hidden'
                        && style.display !== 'none';

        if (!visible) return;  // Skip invisible elements entirely

        const role = el.getAttribute('role') || '';
        const tag = el.tagName.toLowerCase();

        // For anchor tags, skip those without meaningful text
        if (tag === 'a') {
            const text = (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim();
            if (!text || text.length < 2) return;  // Skip empty/icon-only links
        }

        // Skip header/footer nav links when main content is present
        if (hasMainContent && tag === 'a') {
            const inHeader = !!el.closest('header, [role="banner"], nav, [role="navigation"], .header, .navbar, .nav-bar, #navbar, #nav');
            const inFooter = !!el.closest('footer, [role="contentinfo"], .footer, #footer');
            if (inHeader || inFooter) return;  // Skip nav links when product content exists
        }

        // Rule 1: Calendar / gridcell — prefer aria-label over innerText
        let text = '';
        if (role === 'gridcell' || el.hasAttribute('data-iso')) {
            text = el.getAttribute('aria-label') || el.innerText || '';
        } else {
            text = el.getAttribute('aria-label') || el.innerText || el.textContent || '';
        }
        text = text.trim().substring(0, 200);

        // Determine semantic role for the agent
        let elRole = '';
        if (tag === 'input' || tag === 'textarea') elRole = 'INPUT';
        else if (tag === 'select') elRole = 'SELECT';
        else if (tag === 'button' || role === 'button') elRole = 'BUTTON';
        else if (tag === 'a' && text.match(/continue|next|submit|make appointment|book|confirm/i)) elRole = 'BUTTON-LINK';
        else if (tag === 'a') elRole = 'NAV-LINK';
        else if (role === 'tab') elRole = 'TAB';
        else if (role === 'option') elRole = 'OPTION';
        else if (role === 'gridcell') elRole = 'GRIDCELL';
        else if (role === 'checkbox') elRole = 'CHECKBOX';
        else if (role === 'radio') elRole = 'RADIO';
        else if (role === 'combobox') elRole = 'COMBOBOX';
        else if (role === 'searchbox') elRole = 'SEARCHBOX';
        else if (role === 'textbox') elRole = 'TEXTBOX';
        else if (role === 'menuitem') elRole = 'MENUITEM';
        else if (role === 'listbox') elRole = 'LISTBOX';
        else if (el.isContentEditable) elRole = 'INPUT';

        // Rule 4: Assign stable ref via data attribute
        const ref = `el-${elements.length}`;
        el.setAttribute('data-mano-ref', ref);

        // Calculate in-viewport bonus for sorting
        const inViewport = rect.top >= 0 && rect.top <= viewportHeight && rect.left >= 0 && rect.left <= viewportWidth;
        const sortPriority = inViewport ? 0 : 1;  // In-viewport elements sort first

        elements.push({
            ref: ref,
            role: elRole || null,
            tag: tag,
            text: text || null,
            name: el.getAttribute('name') || null,
            value: el.value || null,
            placeholder: el.getAttribute('placeholder') || null,
            input_type: el.getAttribute('type') || null,
            visible: visible,
            _sortPriority: sortPriority,
            _y: rect.top
        });
    });

    // Priority boost for search/submit/explore buttons
    elements.forEach(item => {
        const text = (item.text || '').toLowerCase();
        const inputType = item.input_type || '';
        if (text === 'search' || text === 'explore' || text === 'buscar' ||
            text.includes('search') || text.includes('explore') ||
            inputType === 'submit') {
            item._sortPriority = -1;  // Highest priority — sorts before everything
        }
    });

    // Rule 2: Sort by viewport priority first, then by vertical position
    elements.sort((a, b) => {
        if (a._sortPriority !== b._sortPriority) return a._sortPriority - b._sortPriority;
        return a._y - b._y;
    });

    // Strip internal helper fields
    elements.forEach(e => { delete e._sortPriority; delete e._y; });

    return elements.slice(0, 80);
})()
"""

# ---------------------------------------------------------------------------
# JavaScript: extract body text (Rule 3)
# ---------------------------------------------------------------------------
EXTRACT_TEXT_JS = "document.body.innerText.substring(0, 5000)"


class PlaywrightProvider(BrowserProvider):
    """Playwright-based browser provider implementing all 9 battle-tested rules."""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def launch(self) -> None:
        """Launch browser with configurable headless mode (Rule 9) and stealth (Rule 8)."""
        try:
            self._playwright = await async_playwright().start()
            # Rule 9: headless mode configurable via BROWSER_HEADLESS env var
            self._browser = await self._playwright.chromium.launch(headless=settings.browser_headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            # Rule 8: Anti-bot stealth
            await self._context.add_init_script(STEALTH_JS)
            self._page = await self._context.new_page()
            logger.info(f"Playwright browser launched (headless={settings.browser_headless})")
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            raise

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def navigate(self, url: str) -> ActionResult:
        try:
            if not self._page:
                return ActionResult(success=False, message="Browser not launched")
            logger.info(f"Navigating to: {url}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await self._page.wait_for_load_state("networkidle", timeout=15_000)
            title = await self._page.title()
            return ActionResult(
                success=True,
                message=f"Navigated to {url} — title: {title}",
            )
        except Exception as e:
            logger.error(f"Navigate error: {e}")
            return ActionResult(success=False, message=f"Navigation failed: {e}")

    # ------------------------------------------------------------------
    # Click
    # ------------------------------------------------------------------

    async def click(self, ref: str) -> ActionResult:
        if not self._page:
            return ActionResult(success=False, message="Browser not launched")

        locator = self._page.locator(f'[data-mano-ref="{ref}"]')
        if await locator.count() == 0:
            # Fallback: try JS-based click for shadow DOM elements
            return await self._click_via_js(ref)

        # Ensure element is visible
        if not await locator.is_visible():
            return ActionResult(success=False, message=f"Element {ref} is not visible")

        # Rule 6: Auto-submit guard — check if this is a submit button
        # inside a form. Only auto-submit if the button has visible text.
        try:
            is_submit = await locator.evaluate(
                """el => {
                    const isFormSubmit = el.closest('form') !== null
                        && (el.type === 'submit'
                            || el.getAttribute('role') === 'button'
                            || el.tagName === 'BUTTON');
                    const hasText = (el.innerText || '').trim().length > 0;
                    return { isFormSubmit, hasText };
                }"""
            )
            if is_submit.get("isFormSubmit") and not is_submit.get("hasText"):
                return ActionResult(
                    success=False,
                    message=f"Skipping auto-submit: button {ref} has no visible text (icon-only)",
                )
        except Exception:
            pass  # Non-fatal: proceed to click attempt

        # Retry logic: max 3 attempts, 1s wait between retries, 5s total cap
        start_time = time.monotonic()
        max_retries = 3
        last_error = ""

        for attempt in range(1, max_retries + 1):
            if time.monotonic() - start_time > 5.0:
                return ActionResult(
                    success=False,
                    message=f"Click failed on {ref}: exceeded 5s total timeout after {attempt-1} attempts",
                )
            try:
                await locator.click(timeout=1000)
                # Brief pause for page to react
                await asyncio.sleep(0.3)
                return ActionResult(success=True, message=f"Clicked element {ref}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Click attempt {attempt}/{max_retries} failed on {ref}: {e}")
                if attempt < max_retries:
                    wait_time = min(1.0, max(0.0, 5.0 - (time.monotonic() - start_time)))
                    await asyncio.sleep(wait_time)

        # If ref-based click failed, try by button text/selector
        try:
            for selector in [
                'button[aria-label*="Search" i]',
                'button[aria-label*="Explore" i]',
                'button:has-text("Search")',
                'button:has-text("Explore")',
                '[role="button"][aria-label*="Search" i]',
                '[role="button"][aria-label*="Explore" i]',
            ]:
                btn = self._page.locator(selector).first
                if await btn.count() > 0:
                    await btn.click(timeout=3000)
                    return ActionResult(success=True, message=f"Clicked search button via selector: {selector}")
        except Exception:
            pass

        return ActionResult(
            success=False,
            message=f"Click failed after {max_retries} attempts: {last_error}",
        )

    # ------------------------------------------------------------------
    # Fill (Rule 5: autocomplete behavior)
    # ------------------------------------------------------------------

    async def fill(self, ref: str, value: str) -> ActionResult:
        """Fill a field, handling both regular inputs and combobox widgets.

        Tries Playwright locator first. If that fails (e.g. shadow DOM element
        whose data-mano-ref was wiped by SPA re-render), falls back to using
        page.evaluate() to find and interact with the element directly.
        """
        if not self._page:
            return ActionResult(success=False, message="Browser not launched")

        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                el = self._page.locator(f'[data-mano-ref="{ref}"]')
                found = await el.count() > 0

                if not found:
                    # Fallback: use JS to find element (pierces shadow DOM)
                    # and re-apply data-mano-ref so Playwright can find it
                    reapply_result = await self._page.evaluate(f"""
                        (() => {{
                            function findByRef(root, ref) {{
                                let found = root.querySelector('[data-mano-ref="{ref}"]');
                                if (found) return found;
                                const allEls = root.querySelectorAll('*');
                                for (const el of allEls) {{
                                    if (el.shadowRoot) {{
                                        found = findByRef(el.shadowRoot, ref);
                                        if (found) return found;
                                    }}
                                }}
                                return null;
                            }}
                            const el = findByRef(document, '{ref}');
                            if (el) return true;
                            return false;
                        }})()
                    """)

                    if not reapply_result:
                        # Element truly gone — re-observe to get fresh refs
                        return ActionResult(
                            success=False,
                            message=f"Element {ref} no longer exists on page (SPA re-rendered)",
                        )

                    # Re-check Playwright locator after JS confirm
                    el = self._page.locator(f'[data-mano-ref="{ref}"]')
                    if await el.count() == 0:
                        # Playwright still can't find it — use JS-based fill
                        return await self._fill_via_js(ref, value)

                # Click to focus/activate the field
                try:
                    await el.click(timeout=3000)
                except Exception as click_err:
                    # Element found but not clickable — likely shadow DOM / SPA overlay
                    logger.info(f"Click timeout on {ref}, falling back to JS fill: {click_err}")
                    return await self._fill_via_js(ref, value)
                await asyncio.sleep(0.3)

                # Try to find the actual input inside (for composite widgets)
                inner_input = el.locator('input, [contenteditable="true"]')
                target = inner_input if await inner_input.count() > 0 else el

                # Clear existing content
                await target.press("Control+a", timeout=2000)
                await target.press("Backspace", timeout=2000)
                await asyncio.sleep(0.2)

                # Type value character by character
                await target.type(value, delay=50, timeout=5000)

                # Wait for autocomplete dropdown
                await asyncio.sleep(0.8)

                # Select first autocomplete option
                await target.press("ArrowDown", timeout=2000)
                await asyncio.sleep(0.2)
                await target.press("Enter", timeout=2000)
                await asyncio.sleep(0.5)

                return ActionResult(
                    success=True,
                    message=f"Filled '{ref}' with '{value}' and selected autocomplete option",
                )
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    continue
                # All retries failed — try JS fallback as last resort
                logger.info(f"All Playwright retries failed for {ref}, trying JS fill fallback")
                return await self._fill_via_js(ref, value)

    async def _click_via_js(self, ref: str) -> ActionResult:
        """Click a field using pure JavaScript (for shadow DOM / SPA elements)."""
        try:
            result = await self._page.evaluate(f"""
                (() => {{
                    function findByRef(root, ref) {{
                        let found = root.querySelector('[data-mano-ref="' + ref + '"]');
                        if (found) return found;
                        const allEls = root.querySelectorAll('*');
                        for (const el of allEls) {{
                            if (el.shadowRoot) {{
                                found = findByRef(el.shadowRoot, ref);
                                if (found) return found;
                            }}
                        }}
                        return null;
                    }}
                    const el = findByRef(document, '{ref}');
                    if (!el) return {{ success: false, message: 'Element {ref} not found via JS' }};
                    el.click();
                    return {{ success: true, message: 'Clicked via JS fallback' }};
                }})()
            """)
            if result.get('success'):
                await asyncio.sleep(0.3)
                return ActionResult(success=True, message=f"Clicked element {ref} via JS fallback")
            else:
                return ActionResult(success=False, message=result.get('message', f'JS click failed for {ref}'))
        except Exception as e:
            return ActionResult(success=False, message=f"JS click fallback error on {ref}: {str(e)[:100]}")

    async def _fill_via_js(self, ref: str, value: str) -> ActionResult:
        """Fill a field using pure JavaScript (for shadow DOM / SPA elements)."""
        try:
            result = await self._page.evaluate(f"""
                (() => {{
                    function findByRef(root, ref) {{
                        let found = root.querySelector('[data-mano-ref="' + ref + '"]');
                        if (found) return found;
                        const allEls = root.querySelectorAll('*');
                        for (const el of allEls) {{
                            if (el.shadowRoot) {{
                                found = findByRef(el.shadowRoot, ref);
                                if (found) return found;
                            }}
                        }}
                        return null;
                    }}
                    const el = findByRef(document, '{ref}');
                    if (!el) return {{ success: false, message: 'Element {ref} not found via JS' }};

                    // Find inner input if composite widget
                    const inner = el.querySelector('input, [contenteditable="true"]');
                    const target = inner || el;

                    // Focus and clear
                    target.focus();
                    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {{
                        target.value = '';
                        target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else if (target.isContentEditable) {{
                        target.textContent = '';
                    }}

                    // Set value
                    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {{
                        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        )?.set || Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype, 'value'
                        )?.set;
                        if (nativeInputValueSetter) {{
                            nativeInputValueSetter.call(target, '{value}');
                        }} else {{
                            target.value = '{value}';
                        }}
                        target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }} else if (target.isContentEditable) {{
                        target.textContent = '{value}';
                        target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }} else {{
                        // For combobox divs, simulate keyboard events
                        target.focus();
                        target.click();
                    }}

                    return {{ success: true, message: 'Filled via JS fallback' }};
                }})()
            """)

            if result.get('success'):
                # After JS fill, use Playwright keyboard to select autocomplete
                await asyncio.sleep(0.8)
                await self._page.keyboard.press('ArrowDown')
                await asyncio.sleep(0.2)
                await self._page.keyboard.press('Enter')
                await asyncio.sleep(0.5)
                return ActionResult(
                    success=True,
                    message=f"Filled '{ref}' with '{value}' via JS fallback + autocomplete",
                )
            else:
                return ActionResult(
                    success=False,
                    message=result.get('message', f'JS fill failed for {ref}'),
                )
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"JS fill fallback error on {ref}: {str(e)[:100]}",
            )

    # ------------------------------------------------------------------
    # Select Date (calendar widget)
    # ------------------------------------------------------------------

    async def select_date(self, ref: str, date_str: str) -> ActionResult:
        """Select a date from a calendar widget. date_str format: YYYY-MM-DD or natural language."""
        from datetime import datetime

        if not self._page:
            return ActionResult(success=False, message="Browser not launched")

        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                # First click the date field to open the calendar
                el = self._page.locator(f'[data-mano-ref="{ref}"]')
                if await el.count() > 0:
                    await el.click(timeout=3000)
                    await asyncio.sleep(1.0)

                # Parse the date
                target_date = None
                try:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    # Try other formats
                    for fmt in ["%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y"]:
                        try:
                            target_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue

                if not target_date:
                    # If can't parse, just try to type it and press Enter
                    if await el.count() > 0:
                        await el.type(date_str, delay=50, timeout=3000)
                    else:
                        await self._page.keyboard.type(date_str, delay=50)
                    await asyncio.sleep(0.5)
                    await self._page.keyboard.press("Enter")
                    return ActionResult(success=True, message=f"Typed date '{date_str}' and pressed Enter")

                # Try to find and click the date cell by aria-label or data-iso
                iso_str = target_date.strftime("%Y-%m-%d")

                # Strategy 1: data-iso attribute
                date_cell = self._page.locator(f'[data-iso="{iso_str}"]')
                if await date_cell.count() > 0:
                    await date_cell.first.click(timeout=3000)
                    await asyncio.sleep(0.5)
                    return ActionResult(success=True, message=f"Selected date {iso_str} via data-iso")

                # Strategy 2: aria-label containing the date
                # Google Flights uses format: "Friday, June 20, 2026"
                month_names = ["January", "February", "March", "April", "May", "June",
                              "July", "August", "September", "October", "November", "December"]
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

                day_name = day_names[target_date.weekday()]
                month_name = month_names[target_date.month - 1]
                day_num = target_date.day
                year = target_date.year

                # Try multiple aria-label formats
                aria_patterns = [
                    f"{day_name}, {month_name} {day_num}, {year}",
                    f"{month_name} {day_num}, {year}",
                    f"{month_name} {day_num}",
                    f"{day_num} {month_name} {year}",
                ]

                for pattern in aria_patterns:
                    cell = self._page.locator(f'[aria-label*="{pattern}"]')
                    if await cell.count() > 0:
                        await cell.first.click(timeout=3000)
                        await asyncio.sleep(0.5)
                        return ActionResult(success=True, message=f"Selected date via aria-label: {pattern}")

                # Strategy 3: Navigate months if needed, then try again
                # Check if we need to go forward in the calendar
                for _ in range(6):  # Try up to 6 months forward
                    next_btn = self._page.locator('[aria-label*="Next" i], [aria-label*="next month" i], button:has-text("\u203a"), button:has-text(">")')
                    if await next_btn.count() > 0:
                        await next_btn.first.click(timeout=2000)
                        await asyncio.sleep(0.5)

                        # Check again for the date
                        for pattern in aria_patterns:
                            cell = self._page.locator(f'[aria-label*="{pattern}"]')
                            if await cell.count() > 0:
                                await cell.first.click(timeout=3000)
                                await asyncio.sleep(0.5)
                                return ActionResult(success=True, message=f"Selected date after navigating: {pattern}")
                    else:
                        break

                # Strategy 4: Try keyboard input — clear and type the date
                await self._page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
                if await el.count() > 0:
                    await el.click(timeout=2000)
                    await asyncio.sleep(0.3)
                await self._page.keyboard.press("Control+a")
                await self._page.keyboard.type(target_date.strftime("%b %d"), delay=50)
                await asyncio.sleep(0.5)
                await self._page.keyboard.press("Enter")
                await asyncio.sleep(0.5)
                return ActionResult(success=True, message=f"Typed date {date_str} via keyboard")

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    continue
                return ActionResult(success=False, message=f"select_date failed: {str(e)[:100]}")

    # ------------------------------------------------------------------
    # Select
    # ------------------------------------------------------------------

    async def select(self, ref: str, value: str) -> ActionResult:
        try:
            if not self._page:
                return ActionResult(success=False, message="Browser not launched")
            locator = self._page.locator(f'[data-mano-ref="{ref}"]')
            if await locator.count() == 0:
                return ActionResult(success=False, message=f"Element {ref} not found")

            await locator.select_option(label=value, timeout=10_000)
            return ActionResult(
                success=True,
                message=f"Selected '{value}' in element {ref}",
            )
        except Exception as e:
            logger.error(f"Select error on {ref}: {e}")
            return ActionResult(success=False, message=f"Select failed on {ref}: {e}")

    # ------------------------------------------------------------------
    # Scroll
    # ------------------------------------------------------------------

    async def scroll(self, direction: str = "down") -> ActionResult:
        try:
            if not self._page:
                return ActionResult(success=False, message="Browser not launched")
            delta = 400 if direction == "down" else -400
            await self._page.mouse.wheel(0, delta)
            await asyncio.sleep(0.3)
            return ActionResult(
                success=True,
                message=f"Scrolled {direction} by 400px",
            )
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return ActionResult(success=False, message=f"Scroll failed: {e}")

    # ------------------------------------------------------------------
    # Wait
    # ------------------------------------------------------------------

    async def wait(self, seconds: float = 2.0) -> ActionResult:
        try:
            await asyncio.sleep(seconds)
            return ActionResult(
                success=True,
                message=f"Waited {seconds}s",
            )
        except Exception as e:
            logger.error(f"Wait error: {e}")
            return ActionResult(success=False, message=f"Wait failed: {e}")

    # ------------------------------------------------------------------
    # Press Key
    # ------------------------------------------------------------------

    async def press_key(self, key: str = "Enter") -> ActionResult:
        """Press a keyboard key (e.g. Enter, Tab, Escape, ArrowDown)."""
        try:
            if not self._page:
                return ActionResult(success=False, message="Browser not launched")
            await self._page.keyboard.press(key)
            await asyncio.sleep(0.3)
            return ActionResult(
                success=True,
                message=f"Pressed key: {key}",
            )
        except Exception as e:
            logger.error(f"Press key error: {e}")
            return ActionResult(success=False, message=f"Press key failed: {e}")

    # ------------------------------------------------------------------
    # Extract (Rule 3)
    # ------------------------------------------------------------------

    async def extract(self) -> ActionResult:
        try:
            if not self._page:
                return ActionResult(success=False, message="Browser not launched")
            text: str = await self._page.evaluate(EXTRACT_TEXT_JS)
            # Rule 3: Never truncate below 5000
            return ActionResult(
                success=True,
                message=f"Extracted {len(text)} characters",
                snapshot_summary=text,
            )
        except Exception as e:
            logger.error(f"Extract error: {e}")
            return ActionResult(success=False, message=f"Extract failed: {e}")

    # ------------------------------------------------------------------
    # Screenshot (Rule 7)
    # ------------------------------------------------------------------

    async def screenshot(self) -> str | None:
        """JPEG quality 50, base64, never crash (Rule 7)."""
        try:
            if not self._page:
                return None
            raw = await self._page.screenshot(type="jpeg", quality=50)
            return base64.b64encode(raw).decode()
        except Exception as e:
            logger.warning(f"Screenshot failed (non-fatal): {e}")
            return None

    # ------------------------------------------------------------------
    # Observe — the most critical method
    # Implements Rules 1, 2, 3, 4, 7
    # ------------------------------------------------------------------

    async def observe(self) -> BrowserSnapshot:
        try:
            if not self._page:
                return BrowserSnapshot(
                    url="about:blank",
                    title=None,
                    text_summary="Browser not launched",
                    elements=[],
                    screenshot=None,
                )

            # Wait for page to stabilize (network idle)
            try:
                await self._page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass  # Don't fail if timeout — page might be streaming

            # Small additional wait for dynamic rendering
            await asyncio.sleep(0.8)

            # 1. URL and title
            url = self._page.url
            title = await self._page.title()

            # 2. Rule 3: Extract text (5000 chars max)
            try:
                text: str = await self._page.evaluate(EXTRACT_TEXT_JS)
            except Exception as e:
                logger.warning(f"Text extraction failed: {e}")
                text = ""

            # 3. Rule 1, 2, 4: Extract interactive elements via JS
            try:
                raw_elements: list[dict] = await self._page.evaluate(OBSERVE_JS)
            except Exception as e:
                logger.warning(f"Element extraction failed: {e}")
                raw_elements = []

            # 4. Convert raw dicts to BrowserElement models
            elements: list[BrowserElement] = []
            for item in raw_elements[:MAX_ELEMENTS]:
                try:
                    elements.append(BrowserElement(**item))
                except Exception as e:
                    logger.debug(f"Skipping malformed element: {e}")
                    continue

            # 5. Rule 7: Screenshot (non-fatal)
            screenshot_b64 = await self.screenshot()

            return BrowserSnapshot(
                url=url,
                title=title,
                text_summary=text[:MAX_TEXT_LENGTH],
                elements=elements,
                screenshot=screenshot_b64,
            )
        except Exception as e:
            logger.error(f"Observe error: {e}")
            return BrowserSnapshot(
                url="about:blank",
                title=None,
                text_summary=f"Observe failed: {e}",
                elements=[],
                screenshot=None,
            )

    # ------------------------------------------------------------------
    # Execute action — dispatch based on decision.kind
    # ------------------------------------------------------------------

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
                case "select_date":
                    return await self.select_date(decision.ref or "", decision.value or "")
                case "scroll":
                    return await self.scroll(decision.value or "down")
                case "wait":
                    return await self.wait(float(decision.value or "2"))
                case "extract":
                    return await self.extract()
                case "search_web":
                    import urllib.parse
                    query = urllib.parse.quote_plus(decision.value or "")
                    url = f"https://www.google.com/search?q={query}"
                    return await self.navigate(url)
                case "press_key":
                    return await self.press_key(decision.value or "Enter")
                case _:
                    return ActionResult(
                        success=False,
                        message=f"Unknown action kind: {decision.kind}",
                    )
        except Exception as e:
            logger.error(f"Execute action error: {e}")
            return ActionResult(
                success=False,
                message=f"Action execution failed: {e}",
            )

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    async def close(self) -> None:
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Close error: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
