import logging
import urllib.parse
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from app.config import settings
from app.scrapers.base import PlatformScraper, SearchResult, SponsoredProduct

logger = logging.getLogger("visibility_tracker.scrapers.flipkart")


class FlipkartScraper(PlatformScraper):
    """
    Scraper implementation for Flipkart.
    Extracts ordered sponsored product listings and optional sponsored display placements.
    """

    # Primary navigation & search selectors
    SEARCH_INPUT_SELECTORS = [
        "input[name='q']",
        "input.Pke_EE",
        "input.header-form-search",
        "input[type='text']",
    ]

    # Potential login/dialog dismissal buttons
    CLOSE_LOGIN_DIALOG_SELECTORS = [
        "button._2KpZ6l._2doB4z",
        "span._30XB9F",
        "button:text-is('✕')",
        "span:text-is('✕')",
    ]

    # Search result item containers across Flipkart's list and grid layouts
    RESULT_CONTAINERS = [
        "div[data-id]",
        "div.cPHDOP[data-id]",
        "div._1AtVbE[data-id]",
        "div._75nlfW",
    ]

    # Sponsored / Ad indicators (supports SVG badges, tracking tokens, and text)
    SPONSORED_INDICATOR_SELECTORS = [
        "[data-tkid*='ADVIEW']",
        "[data-tkid*='adview']",
        "[data-tkid*='AD_']",
        "[data-tkid*='_ad_']",
        "a[href*='ADVIEW']",
        ".s4t9tK",
        "svg[width='62']",
        "div[class*='s4t9tK']",
        "div:text-is('Ad')",
        "span:text-is('Ad')",
        "div:text-is('Sponsored')",
        "span:text-is('Sponsored')",
        "._2WkVRV:text-is('Ad')",
        "div[class*='ad-label']",
        "span[class*='ad-label']",
    ]

    # Product title selectors (list layout, grid layout, new layouts)
    TITLE_SELECTORS = [
        "a.atJtCj",
        "a[title]",
        "div._4rR01T",
        "div.KzDlHZ",
        "a.s1Q9rs",
        "a.wByabb",
        "div.B_NuCI",
    ]

    # Product URL selector
    URL_SELECTORS = [
        "a._1fQZEK",
        "a.s1Q9rs",
        "a.wByabb",
        "a[href*='/p/']",
    ]

    # Sponsored Display / Top Brand placement
    SPONSORED_DISPLAY_CONTAINERS = [
        "div._1yR-bH",
        "div._2d0fq9",
        "div[data-tracking-id*='banner']",
        "div[data-tkid*='ad']",
    ]

    # Bot / block indicators
    BLOCK_INDICATORS = [
        "text='Please verify you are a human'",
        "text='Access Denied'",
        "#px-captcha",
    ]

    def __init__(
        self,
        base_url: str | None = None,
        headless: bool | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or settings.FLIPKART_BASE_URL).rstrip("/")
        self.headless = headless if headless is not None else settings.BROWSER_HEADLESS
        self.timeout = timeout or settings.NAVIGATION_TIMEOUT

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def initialize(self) -> None:
        logger.info(f"Initializing Flipkart scraper (headless={self.headless}, base_url={self.base_url})")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale="en-IN",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

    async def close(self) -> None:
        logger.info("Closing Flipkart scraper resources")
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception as e:
            logger.debug(f"Error closing Flipkart page: {e}")

        try:
            if self._context:
                await self._context.close()
        except Exception as e:
            logger.debug(f"Error closing context: {e}")

        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Error stopping playwright: {e}")

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    async def _dismiss_popups(self) -> None:
        """Dismiss initial login prompt modals if present."""
        if not self._page:
            return
        for btn_sel in self.CLOSE_LOGIN_DIALOG_SELECTORS:
            try:
                btn = await self._page.query_selector(btn_sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    break
            except Exception:
                continue

    async def _check_bot_detection(self) -> tuple[bool, str | None]:
        if not self._page:
            return False, None

        title = await self._page.title()
        if "Access Denied" in title:
            return True, "Flipkart Access Denied"

        for indicator in self.BLOCK_INDICATORS:
            try:
                el = await self._page.query_selector(indicator)
                if el and await el.is_visible():
                    return True, f"Bot protection verification detected: {indicator}"
            except Exception:
                continue

        return False, None

    async def search(self, keyword: str, top_n: int = 3) -> SearchResult:
        if not self._page:
            await self.initialize()

        assert self._page is not None

        clean_keyword = keyword.strip()
        encoded_kw = urllib.parse.quote_plus(clean_keyword)
        search_url = f"{self.base_url}/search?q={encoded_kw}"

        logger.info(f"Navigating to Flipkart search: {search_url} for '{clean_keyword}'")

        try:
            response = await self._page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)
            if response and response.status in (403, 503):
                return SearchResult(
                    keyword=clean_keyword,
                    sponsored_products=[],
                    sponsored_display=None,
                    success=False,
                    error=f"HTTP {response.status} returned by Flipkart (Throttled/Blocked)",
                )

            await self._dismiss_popups()

            # Check bot detection
            is_blocked, block_reason = await self._check_bot_detection()
            if is_blocked:
                logger.warning(f"Bot detection on Flipkart for '{clean_keyword}': {block_reason}")
                return SearchResult(
                    keyword=clean_keyword,
                    sponsored_products=[],
                    sponsored_display=None,
                    success=False,
                    error=block_reason or "Flipkart challenge encountered",
                )

            # Wait briefly for product results
            try:
                await self._page.wait_for_selector(
                    "div[data-id], div._1AtVbE, div.cPHDOP",
                    timeout=min(self.timeout, 10000),
                )
            except Exception:
                pass

            # 1. Check for Sponsored Display
            sponsored_display = await self._extract_sponsored_display()

            # 2. Extract Sponsored Products
            sponsored_products = await self._extract_sponsored_products(top_n=top_n)

            return SearchResult(
                keyword=clean_keyword,
                sponsored_products=sponsored_products,
                sponsored_display=sponsored_display,
                success=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Error searching Flipkart for '{clean_keyword}': {e}", exc_info=True)
            return SearchResult(
                keyword=clean_keyword,
                sponsored_products=[],
                sponsored_display=None,
                success=False,
                error=str(e),
            )

    async def _extract_sponsored_display(self) -> SponsoredProduct | None:
        """
        Extracts separate banner-like sponsored placements if present.
        """
        if not self._page:
            return None

        for container_sel in self.SPONSORED_DISPLAY_CONTAINERS:
            try:
                container = await self._page.query_selector(container_sel)
                if not container or not await container.is_visible():
                    continue

                text = await container.inner_text()
                if "Ad" in text or "Sponsored" in text:
                    lines = [l.strip() for l in text.splitlines() if l.strip() and l.strip() not in ("Ad", "Sponsored")]
                    if lines:
                        return SponsoredProduct(
                            position=0,
                            name=lines[0],
                            url=None,
                        )
            except Exception as e:
                logger.debug(f"Error checking Flipkart sponsored display: {e}")
                continue

        return None

    async def _extract_sponsored_products(self, top_n: int) -> list[SponsoredProduct]:
        """
        Iterates over product cards, identifies 'Ad' or 'Sponsored' tags,
        and collects up to top_n in order.
        """
        if not self._page:
            return []

        containers = []
        seen_ids = set()
        for container_sel in self.RESULT_CONTAINERS:
            found = await self._page.query_selector_all(container_sel)
            for el in found:
                data_id = await el.get_attribute("data-id")
                key = data_id or str(id(el))
                if key not in seen_ids:
                    seen_ids.add(key)
                    containers.append(el)

        sponsored_products: list[SponsoredProduct] = []
        current_position = 1

        for container in containers:
            try:
                # Check for Ad / Sponsored tag or ADVIEW tracking tokens
                is_sponsored = False

                # 1. Check data-tkid attribute directly on card
                card_tkid = await container.get_attribute("data-tkid") or ""
                if "adview" in card_tkid.lower() or "ad_" in card_tkid.lower():
                    is_sponsored = True

                # 2. Check indicator selectors (ADVIEW elements, s4t9tK SVG badge, text)
                if not is_sponsored:
                    for ind_sel in self.SPONSORED_INDICATOR_SELECTORS:
                        try:
                            ind_el = await container.query_selector(ind_sel)
                            if ind_el and await ind_el.is_visible():
                                is_sponsored = True
                                break
                        except Exception:
                            continue

                # 3. Check for text 'Sponsored' or 'Ad' in card text
                if not is_sponsored:
                    card_text = await container.inner_text()
                    lines = [l.strip().lower() for l in card_text.splitlines() if l.strip()]
                    if lines and (lines[0] in ("ad", "sponsored") or any("sponsored" in l for l in lines[:3])):
                        is_sponsored = True

                if not is_sponsored:
                    continue

                # Extract title (prefer title attribute on link if available)
                title: str | None = None
                for title_sel in self.TITLE_SELECTORS:
                    try:
                        title_el = await container.query_selector(title_sel)
                        if title_el:
                            candidate = (await title_el.get_attribute("title") or "").strip()
                            if not candidate:
                                candidate = (await title_el.inner_text()).strip()
                            if candidate and len(candidate) > 2:
                                title = candidate.replace("\n", " ").strip()
                                break
                    except Exception:
                        continue

                if not title:
                    continue

                # Extract URL
                url: str | None = None
                for url_sel in self.URL_SELECTORS:
                    try:
                        link_el = await container.query_selector(url_sel)
                        if link_el:
                            href = await link_el.get_attribute("href")
                            if href:
                                url = urllib.parse.urljoin(self.base_url, href)
                                break
                    except Exception:
                        continue

                sponsored_products.append(
                    SponsoredProduct(
                        position=current_position,
                        name=title,
                        url=url,
                    )
                )
                current_position += 1

                if len(sponsored_products) >= top_n:
                    break

            except Exception as e:
                logger.debug(f"Error inspecting Flipkart product container: {e}")
                continue

        return sponsored_products
