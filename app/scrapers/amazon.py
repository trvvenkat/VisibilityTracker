import logging
import re
import urllib.parse
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from app.config import settings
from app.scrapers.base import PlatformScraper, SearchResult, SponsoredProduct

logger = logging.getLogger("visibility_tracker.scrapers.amazon")

_SPONSORED_LABEL_RE = re.compile(
    r"^(?:sponsored\s*(?:ad)?\s*[-–—:]\s*|\(sponsored\)\s*)",
    re.IGNORECASE,
)
_NOT_A_BRAND = frozenset({"sponsored", "sponsored ad", "featured", "featured from our brands"})


def _normalize_listing_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()
    return _SPONSORED_LABEL_RE.sub("", cleaned).strip()


def _is_short_brand(brand: str, title: str) -> bool:
    """A brand is a short maker name. Feature subheadings are full sentences."""
    if not brand or not title:
        return False
    if brand.casefold() in _NOT_A_BRAND or brand.casefold() == title.casefold():
        return False
    if "," in brand or "|" in brand:
        return False
    words = brand.split()
    if not words or len(words) > 3:
        return False
    if len(brand) > 40 or len(brand) >= len(title):
        return False
    return True


class AmazonScraper(PlatformScraper):
    """
    Scraper implementation for Amazon (default Amazon.in / configurable via AMAZON_BASE_URL).
    Extracts ordered sponsored product listings and optional sponsored display placements.
    """

    # Primary navigation & search selectors
    SEARCH_INPUT = "#twotabsearchtextbox"
    SEARCH_SUBMIT_BUTTON = "#nav-search-submit-button"

    # Search result item containers
    RESULT_CONTAINERS = [
        "div.s-main-slot > div[data-asin]:not([data-asin=''])",
        "div[data-component-type='s-search-result']",
        "div.s-result-item[data-asin]:not([data-asin=''])",
    ]

    # Sponsored indicator selectors within a result container
    SPONSORED_INDICATOR_SELECTORS = [
        ".puis-sponsored-label-text",
        "[aria-label*='Sponsored']",
        "[aria-label*='View Sponsored information']",
        "span:text-is('Sponsored')",
        "span:has-text('Sponsored')",
        "span:text-is('Featured from our brands')",
        ".s-featured-result-item",
        "div[data-component-props*='sp_delivered']",
        "div[data-component-props*='SponsoredProducts']",
        "span.a-badge-text:has-text('Sponsored')",
        "span.a-color-base:has-text('Sponsored')",
        "span.a-color-secondary:has-text('Sponsored')",
    ]

    # Product title selectors within result container
    TITLE_SELECTORS = [
        "h2[class*='a-size-medium'] span",
        "h2:not(.a-size-mini) span",
        "h2[class*='a-size-medium']",
        "h2:not(.a-size-mini)",
        "[data-cy='title-recipe'] h2 span",
        "[data-cy='title-recipe'] a:has(h2) span",
        "[data-cy='title-recipe'] a:has(h2)",
        "div.s-title-instructions-style h2 span",
        "div.s-title-instructions-style a:has(h2)",
        "a.a-link-normal[href*='/dp/']:not([class*='s-no-hover'])",
        "h2 a.a-link-normal span",
        "h2 a span",
        "a.a-text-normal",
        "h2 span",
        "h2",
    ]

    # Brand selectors above product title
    BRAND_SELECTORS = [
        "h2.a-size-mini span",
        "[data-cy='title-recipe'] .a-color-secondary span",
        "div.s-title-instructions-style .a-color-secondary span",
        "div.s-line-clamp-1 span",
    ]

    # Product link. The title is read from this anchor, not from the first heading on the card.
    PRODUCT_LINK_SELECTORS = [
        "a[href*='/sspa/click']",
        "a[href*='%2Fdp%2F']",
        "a[href*='/dp/']",
    ]

    # Product URL selector
    URL_SELECTORS = [
        "a:has(h2:not(.a-size-mini))[href*='/sspa/click']",
        "a:has(h2:not(.a-size-mini))[href*='/dp/']",
        "a:has(h2:not(.a-size-mini))[href*='%2Fdp%2F']",
        "a:has(h2:not(.a-size-mini))",
        "a.a-link-normal[href*='/sspa/click']",
        "a.a-link-normal[href*='/dp/']",
        "a.a-link-normal[href*='%2Fdp%2F']",
        "[data-cy='title-recipe'] a[href]",
        "h2 a.a-link-normal",
        "a.a-link-normal",
    ]

    # Sponsored Display / Brand Placement (separate from organic/SP product grid)
    SPONSORED_DISPLAY_CONTAINERS = [
        "div[data-component-type='sp-sponsored-brands']",
        "div[data-component-type='s-head-to-foot-slot']",
        "div.sbv-video-single-product",
        "div.s-shopping-ad-widget",
        "div[data-cel-widget*='MAIN-TOP_BANNER']",
    ]
    SPONSORED_DISPLAY_TITLE_SELECTORS = [
        "span.sb-hero-banner-title",
        "span[data-action='sponsored-brand-headline']",
        ".sbv-product-title",
        "h2",
        "span.a-size-medium",
    ]

    # Bot / CAPTCHA challenge detection
    CAPTCHA_SELECTORS = [
        "form[action*='validateCaptcha']",
        "#captchacharacters",
        "input#captchacharacters",
        "text='Enter the characters you see below'",
        "text='Type the characters you see in this image'",
    ]

    def __init__(
        self,
        base_url: str | None = None,
        headless: bool | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or settings.AMAZON_BASE_URL).rstrip("/")
        self.headless = headless if headless is not None else settings.BROWSER_HEADLESS
        self.timeout = timeout or settings.NAVIGATION_TIMEOUT

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def initialize(self) -> None:
        logger.info(f"Initializing Amazon scraper (headless={self.headless}, base_url={self.base_url})")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            locale="en-IN",
            extra_http_headers={
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

    async def close(self) -> None:
        logger.info("Closing Amazon scraper resources")
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception as e:
            logger.debug(f"Error closing page: {e}")

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

    async def _check_bot_detection(self) -> tuple[bool, str | None]:
        """Detect CAPTCHA or blocking responses."""
        if not self._page:
            return False, None

        title = await self._page.title()
        if "Robot Check" in title or "CAPTCHA" in title:
            return True, "Amazon Robot Check (CAPTCHA) page detected"

        for selector in self.CAPTCHA_SELECTORS:
            try:
                el = await self._page.query_selector(selector)
                if el and await el.is_visible():
                    return True, f"CAPTCHA detected via selector: {selector}"
            except Exception:
                continue

        content = await self._page.content()
        if "Sorry, we just need to make sure you're not a robot" in content:
            return True, "Amazon automated traffic verification challenge detected"

        return False, None

    async def search(self, keyword: str, top_n: int = 3) -> SearchResult:
        if not self._page:
            await self.initialize()

        assert self._page is not None

        clean_keyword = keyword.strip()
        encoded_kw = urllib.parse.quote_plus(clean_keyword)
        search_url = f"{self.base_url}/s?k={encoded_kw}"

        logger.info(f"Navigating to Amazon search: {search_url} for '{clean_keyword}'")

        try:
            response = await self._page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)
            if response and response.status in (403, 503):
                return SearchResult(
                    keyword=clean_keyword,
                    sponsored_products=[],
                    sponsored_display=None,
                    success=False,
                    error=f"HTTP {response.status} returned by Amazon (Request throttled or blocked)",
                )

            # Check for CAPTCHA
            is_captcha, captcha_reason = await self._check_bot_detection()
            if is_captcha:
                logger.warning(f"Bot detection triggered for '{clean_keyword}': {captcha_reason}")
                return SearchResult(
                    keyword=clean_keyword,
                    sponsored_products=[],
                    sponsored_display=None,
                    success=False,
                    error=captcha_reason or "Amazon CAPTCHA challenge encountered",
                )

            # Wait briefly for main search container to populate and ads to settle
            try:
                await self._page.wait_for_selector(
                    "div.s-main-slot, div[data-component-type='s-search-result'], div.s-result-item",
                    timeout=min(self.timeout, 10000),
                )
                await self._page.wait_for_timeout(2000)
            except Exception:
                pass

            # 1. Identify Sponsored Display / Headline brand placement
            sponsored_display = await self._extract_sponsored_display()

            # 2. Extract Sponsored Product Listings in displayed order
            sponsored_products = await self._extract_sponsored_products(top_n=top_n)

            return SearchResult(
                keyword=clean_keyword,
                sponsored_products=sponsored_products,
                sponsored_display=sponsored_display,
                success=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Error searching Amazon for '{clean_keyword}': {e}", exc_info=True)
            return SearchResult(
                keyword=clean_keyword,
                sponsored_products=[],
                sponsored_display=None,
                success=False,
                error=str(e),
            )

    async def _extract_sponsored_display(self) -> SponsoredProduct | None:
        """
        Attempts to find a dedicated Sponsored Display or Sponsored Brand banner
        placement distinct from regular product cards.
        """
        if not self._page:
            return None

        for container_sel in self.SPONSORED_DISPLAY_CONTAINERS:
            try:
                container = await self._page.query_selector(container_sel)
                if not container or not await container.is_visible():
                    continue

                # Verify sponsored indicator inside or near container
                inner_text = await container.inner_text()
                if "Sponsored" not in inner_text:
                    continue

                # Extract title/brand name
                for title_sel in self.SPONSORED_DISPLAY_TITLE_SELECTORS:
                    title_el = await container.query_selector(title_sel)
                    if title_el:
                        title_text = (await title_el.inner_text()).strip()
                        if title_text and len(title_text) > 2:
                            return SponsoredProduct(
                                position=0,
                                name=title_text.replace("\n", " ").strip(),
                                url=None,
                            )

                # Fallback to trimmed text if specific title element not matched
                lines = [line.strip() for line in inner_text.splitlines() if line.strip() and line.strip() != "Sponsored"]
                if lines:
                    return SponsoredProduct(
                        position=0,
                        name=lines[0],
                        url=None,
                    )
            except Exception as e:
                logger.debug(f"Error checking sponsored display container {container_sel}: {e}")
                continue

        return None

    async def _title_from_heading(self, heading) -> str:
        text = _normalize_listing_text(await heading.inner_text())
        if len(text) > 2 and text.casefold() not in _NOT_A_BRAND:
            return text
        aria = _normalize_listing_text(await heading.get_attribute("aria-label") or "")
        if len(aria) > 2 and aria.casefold() not in _NOT_A_BRAND:
            return aria
        return ""

    async def _title_from_product_link(self, link) -> str:
        """
        Read the product name from the listing link.
        A feature line above the link is a sibling heading, so it is ignored.
        When every heading inside the link is the compact mini style, the last
        one is the title (the feature line, when present, comes first).
        """
        headings = await link.query_selector_all("h2")
        chosen = None
        for heading in headings:
            class_name = await heading.get_attribute("class") or ""
            if "a-size-mini" not in class_name.split():
                chosen = heading
                break
        if chosen is None and headings:
            chosen = headings[-1]
        if chosen is not None:
            text = await self._title_from_heading(chosen)
            if text:
                return text

        link_text = _normalize_listing_text(await link.inner_text())
        if len(link_text) > 2 and link_text.casefold() not in _NOT_A_BRAND:
            return link_text
        return ""

    async def _title_from_legacy_selectors(self, container) -> str:
        for title_sel in self.TITLE_SELECTORS:
            try:
                title_el = await container.query_selector(title_sel)
                if not title_el:
                    continue
                tag_name = await title_el.evaluate("el => el.tagName")
                if tag_name == "A":
                    heading = await title_el.query_selector("h2")
                    candidate = await self._title_from_heading(heading) if heading else ""
                    if not candidate:
                        candidate = _normalize_listing_text(await title_el.inner_text())
                elif tag_name == "H2":
                    candidate = await self._title_from_heading(title_el)
                else:
                    candidate = _normalize_listing_text(await title_el.inner_text())
                if len(candidate) > 2 and candidate.casefold() not in _NOT_A_BRAND:
                    return candidate
            except Exception:
                continue
        return ""

    async def _with_short_brand(self, container, title: str) -> str:
        for selector in self.BRAND_SELECTORS:
            try:
                elements = await container.query_selector_all(selector)
            except Exception:
                continue
            for element in elements:
                try:
                    brand = _normalize_listing_text(await element.inner_text())
                except Exception:
                    continue
                if _is_short_brand(brand, title) and not title.casefold().startswith(brand.casefold()):
                    return f"{brand} {title}".strip()
        return title

    async def _extract_product_title(self, container) -> str | None:
        for selector in self.PRODUCT_LINK_SELECTORS:
            try:
                links = await container.query_selector_all(selector)
            except Exception:
                continue
            for link in links:
                try:
                    title = await self._title_from_product_link(link)
                except Exception:
                    continue
                if title:
                    return await self._with_short_brand(container, title)

        title = await self._title_from_legacy_selectors(container)
        if not title:
            return None
        return await self._with_short_brand(container, title)

    async def _extract_sponsored_products(self, top_n: int) -> list[SponsoredProduct]:
        """
        Iterates through search results in DOM order, identifies sponsored products,
        and collects up to top_n sponsored items.
        """
        if not self._page:
            return []

        # Find all candidate product containers
        containers = []
        seen_elements = set()
        for container_sel in self.RESULT_CONTAINERS:
            found = await self._page.query_selector_all(container_sel)
            for el in found:
                asin = await el.get_attribute("data-asin")
                uuid = await el.get_attribute("data-uuid") or asin
                key = uuid or str(id(el))
                if key not in seen_elements:
                    seen_elements.add(key)
                    containers.append(el)

        sponsored_products: list[SponsoredProduct] = []
        current_position = 1

        for container in containers:
            try:
                # Check if this container is visibly sponsored
                is_sponsored = False
                for ind_sel in self.SPONSORED_INDICATOR_SELECTORS:
                    try:
                        ind_el = await container.query_selector(ind_sel)
                        if ind_el and await ind_el.is_visible():
                            is_sponsored = True
                            break
                    except Exception:
                        continue

                if not is_sponsored:
                    # Check text content: check first 3 lines for Sponsored indicator
                    container_text = await container.inner_text()
                    lines = [line.strip() for line in container_text.splitlines() if line.strip()]
                    if lines and any("sponsored" in line.lower() for line in lines[:3]):
                        is_sponsored = True

                if not is_sponsored:
                    continue

                title = await self._extract_product_title(container)
                if not title:
                    continue

                # Extract product link
                url: str | None = None
                for url_sel in self.URL_SELECTORS:
                    try:
                        link_el = await container.query_selector(url_sel)
                        if link_el:
                            href = await link_el.get_attribute("href")
                            if href and not href.startswith("#") and not href.startswith("javascript:"):
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
                logger.debug(f"Error inspecting container for sponsored product: {e}")
                continue

        return sponsored_products
