import pytest
from app.scrapers.mock import MockScraper


@pytest.mark.asyncio
async def test_mock_scraper_search():
    scraper = MockScraper(simulate_latency=0.0)
    await scraper.initialize()

    res = await scraper.search("mechanical keyboard", top_n=3)
    assert res.success is True
    assert res.keyword == "mechanical keyboard"
    assert len(res.sponsored_products) == 3
    assert res.sponsored_products[0].position == 1
    assert "Mechanical Keyboard" in res.sponsored_products[0].name

    await scraper.close()


@pytest.mark.asyncio
async def test_mock_scraper_custom_n():
    scraper = MockScraper(simulate_latency=0.0)
    await scraper.initialize()

    res = await scraper.search("headphones", top_n=5)
    assert len(res.sponsored_products) == 5

    res1 = await scraper.search("headphones", top_n=1)
    assert len(res1.sponsored_products) == 1

    await scraper.close()


@pytest.mark.asyncio
async def test_mock_scraper_simulated_failure():
    scraper = MockScraper(simulate_latency=0.0, failure_rate=1.0)
    await scraper.initialize()

    res = await scraper.search("error query", top_n=3)
    assert res.success is False
    assert res.error is not None
    assert len(res.sponsored_products) == 0

    await scraper.close()
