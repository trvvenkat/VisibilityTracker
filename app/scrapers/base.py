from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SponsoredProduct:
    position: int
    name: str
    url: str | None = None


@dataclass
class SearchResult:
    keyword: str
    sponsored_products: list[SponsoredProduct] = field(default_factory=list)
    sponsored_display: SponsoredProduct | None = None
    success: bool = True
    error: str | None = None


class PlatformScraper(ABC):
    """
    Abstract base class for platform scrapers.
    Ensures platform-independent scraper architecture.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize browser, context, and persistent settings."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up and close browser resources."""
        pass

    @abstractmethod
    async def search(self, keyword: str, top_n: int = 3) -> SearchResult:
        """
        Execute visibility search for a single keyword.
        Must return structured SearchResult with up to top_n sponsored products
        and optional sponsored display placement.
        """
        pass
