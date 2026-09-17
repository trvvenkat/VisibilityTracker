from app.scrapers.base import PlatformScraper, SearchResult, SponsoredProduct
from app.scrapers.amazon import AmazonScraper
from app.scrapers.flipkart import FlipkartScraper
from app.scrapers.mock import MockScraper

__all__ = [
    "PlatformScraper",
    "SearchResult",
    "SponsoredProduct",
    "AmazonScraper",
    "FlipkartScraper",
    "MockScraper",
]
