import asyncio
import random
from app.scrapers.base import PlatformScraper, SearchResult, SponsoredProduct


class MockScraper(PlatformScraper):
    """
    Mock scraper simulating e-commerce visibility checks.
    Used for unit testing and offline development.
    """

    def __init__(self, simulate_latency: float = 0.1, failure_rate: float = 0.0):
        self.simulate_latency = simulate_latency
        self.failure_rate = failure_rate
        self.initialized = False

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.initialized = False

    async def search(self, keyword: str, top_n: int = 3) -> SearchResult:
        if self.simulate_latency > 0:
            await asyncio.sleep(self.simulate_latency)

        # Simulate intermittent keyword error if failure rate set
        if self.failure_rate > 0 and random.random() < self.failure_rate:
            return SearchResult(
                keyword=keyword,
                sponsored_products=[],
                sponsored_display=None,
                success=False,
                error="Simulated network or page load failure",
            )

        # Generate realistic sponsored products
        clean_kw = keyword.strip()
        sponsored_products = [
            SponsoredProduct(
                position=i + 1,
                name=f"{clean_kw.title()} Brand Pro Edition {i + 1}",
                url=f"https://example.com/products/{clean_kw.replace(' ', '-')}-{i + 1}",
            )
            for i in range(top_n)
        ]

        # Simulate sponsored display on 50% of searches
        sponsored_display = None
        if len(clean_kw) % 2 == 0:
            sponsored_display = SponsoredProduct(
                position=0,
                name=f"Sponsored Brand Banner: {clean_kw.title()} Official Store",
                url=f"https://example.com/stores/{clean_kw.replace(' ', '-')}",
            )

        return SearchResult(
            keyword=keyword,
            sponsored_products=sponsored_products,
            sponsored_display=sponsored_display,
            success=True,
            error=None,
        )
