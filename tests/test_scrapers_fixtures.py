import pytest
from app.scrapers.amazon import AmazonScraper
from app.scrapers.flipkart import FlipkartScraper

AMAZON_MOCK_HTML = """
<!DOCTYPE html>
<html>
<head><title>Amazon.in : test search</title></head>
<body>
  <!-- Sponsored Brand Banner -->
  <div data-component-type="sp-sponsored-brands" style="display: block;">
    <span class="puis-sponsored-label-text">Sponsored</span>
    <span class="sb-hero-banner-title">Acme Audio Official Store</span>
  </div>

  <!-- Organic item 1 -->
  <div data-component-type="s-search-result" data-asin="B001" style="display: block;">
    <h2><a class="a-link-normal" href="/dp/B001"><span>Organic Smartphone Pro 1</span></a></h2>
  </div>

  <!-- Sponsored item 1 (SP1) -->
  <div data-component-type="s-search-result" data-asin="B002" style="display: block;">
    <span class="puis-sponsored-label-text">Sponsored</span>
    <h2><a class="a-link-normal" href="/dp/B002"><span>Sponsored Ultra Sound Headphones</span></a></h2>
  </div>

  <!-- Organic item 2 -->
  <div data-component-type="s-search-result" data-asin="B003" style="display: block;">
    <h2><a class="a-link-normal" href="/dp/B003"><span>Organic Powerbank 10000mAh</span></a></h2>
  </div>

  <!-- Sponsored item 2 (SP2) -->
  <div data-component-type="s-search-result" data-asin="B004" style="display: block;">
    <span class="a-color-base">Sponsored</span>
    <h2><a class="a-link-normal" href="/dp/B004"><span>Sponsored Wireless Charging Pad</span></a></h2>
  </div>
</body>
</html>
"""

FLIPKART_MOCK_HTML = """
<!DOCTYPE html>
<html>
<head><title>Flipkart : test search</title></head>
<body>
  <!-- Sponsored Display Banner -->
  <div class="_1yR-bH" style="display: block;">
    <div>Ad</div>
    <div>Sony Bravia Master Series Store</div>
  </div>

  <!-- Organic product 1 -->
  <div class="cPHDOP" data-id="MOB001" style="display: block;">
    <div class="_4rR01T">Realme Smart Phone 5G</div>
    <a class="_1fQZEK" href="/realme/p/itm1">View</a>
  </div>

  <!-- Sponsored product 1 (SP1) -->
  <div class="cPHDOP" data-id="MOB002" style="display: block;">
    <div>Ad</div>
    <div class="_4rR01T">Samsung Galaxy Ultra 5G</div>
    <a class="_1fQZEK" href="/samsung/p/itm2">View</a>
  </div>

  <!-- Organic product 2 -->
  <div class="cPHDOP" data-id="MOB003" style="display: block;">
    <div class="_4rR01T">Motorola Edge 40 Neo</div>
    <a class="_1fQZEK" href="/moto/p/itm3">View</a>
  </div>

  <!-- Sponsored product 2 (SP2) -->
  <div class="cPHDOP" data-id="MOB004" style="display: block;">
    <span>Sponsored</span>
    <div class="_4rR01T">OnePlus 12R Armor Case</div>
    <a class="_1fQZEK" href="/oneplus/p/itm4">View</a>
  </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_amazon_scraper_html_fixtures():
    scraper = AmazonScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(AMAZON_MOCK_HTML)

    # Test sponsored display extraction
    sd = await scraper._extract_sponsored_display()
    assert sd is not None
    assert "Acme Audio" in sd.name

    # Test sponsored products extraction (should find only the 2 sponsored items in order)
    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert len(sp_items) == 2
    assert sp_items[0].position == 1
    assert "Sponsored Ultra Sound" in sp_items[0].name
    assert sp_items[1].position == 2
    assert "Sponsored Wireless Charging" in sp_items[1].name

    await scraper.close()


@pytest.mark.asyncio
async def test_flipkart_scraper_html_fixtures():
    scraper = FlipkartScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(FLIPKART_MOCK_HTML)

    # Test sponsored display extraction
    sd = await scraper._extract_sponsored_display()
    assert sd is not None
    assert "Sony Bravia" in sd.name

    # Test sponsored products extraction
    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert len(sp_items) == 2
    assert sp_items[0].position == 1
    assert "Samsung Galaxy Ultra 5G" in sp_items[0].name
    assert sp_items[1].position == 2
    assert "OnePlus 12R Armor Case" in sp_items[1].name

    await scraper.close()


AMAZON_MODERN_SEARCH_HTML = """
<!DOCTYPE html>
<html>
<head><title>Amazon.in : iphone 17</title></head>
<body>
  <div class="s-main-slot">
    <!-- Sponsored Item (SP1): Apple iPhone Air 256 GB -->
    <div data-component-type="s-search-result" data-asin="B0FQFTV1NP" data-uuid="uuid-sp-1" style="display: block;">
      <a class="puis-label-popover puis-sponsored-label-text" style="display: inline-block;">
        <span class="puis-label-popover-default"><span class="a-color-secondary">Sponsored</span></span>
      </a>
      <div data-cy="title-recipe">
        <div class="a-row a-color-secondary"><h2 class="a-size-mini"><span>Apple</span></h2></div>
        <a class="a-link-normal" href="/sspa/click?ie=UTF8&spc=TEST1234&url=%2FiPhone-Air-256-GB%2Fdp%2FB0FQFTV1NP">
          <h2 class="a-size-medium" aria-label="Sponsored Ad - iPhone Air 256 GB: Thinnest iPhone Ever">
            <span>iPhone Air 256 GB: Thinnest iPhone Ever</span>
          </h2>
        </a>
      </div>
    </div>

    <!-- Organic Item: Apple iPhone Air 256 GB -->
    <div data-component-type="s-search-result" data-asin="B0FQFTV1NP" data-uuid="uuid-org-1" style="display: block;">
      <div data-cy="title-recipe">
        <div class="a-row a-color-secondary"><h2 class="a-size-mini"><span>Apple</span></h2></div>
        <a class="a-link-normal" href="/iPhone-Air-256-GB/dp/B0FQFTV1NP">
          <h2 class="a-size-medium"><span>iPhone Air 256 GB: Thinnest iPhone Ever</span></h2>
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""

FLIPKART_MODERN_GRID_HTML = """
<!DOCTYPE html>
<html>
<head><title>smart watch - Buy Products Online at Best Price in India - Flipkart.com</title></head>
<body>
  <!-- Sponsored Grid Card 1: Vector SVG badge, ADVIEW tracking token, title in atJtCj -->
  <div class="cPHDOP" data-id="SMW1" data-tkid="ADVIEW_5883920_ad_test" style="display: block;">
    <div class="s4t9tK">
      <svg width="62" height="18"><path d="M..."></path></svg>
    </div>
    <a class="atJtCj" title="Fire-Boltt Hurricane 2026 1.3' Curved Glass Display with BT Calling" href="/fire-boltt-hurricane/p/itm1">
      Fire-Boltt Hurricane 2026 1.3' Curved Glass Display...
    </a>
  </div>

  <!-- Sponsored Grid Card 2: boAt Storm Call -->
  <div class="cPHDOP" data-id="SMW2" data-tkid="ADVIEW_5883921_ad_test" style="display: block;">
    <div class="s4t9tK">
      <svg width="62" height="18"></svg>
    </div>
    <a class="atJtCj Qum9aC" title="boAt Storm Call w/ 4.29 cm(1.69'), BT Calling Smartwatch" href="/boat-storm-call/p/itm2">
      boAt Storm Call...
    </a>
  </div>

  <!-- Organic Grid Card 3 -->
  <div class="cPHDOP" data-id="SMW3" data-tkid="search_organic_item" style="display: block;">
    <a class="atJtCj" title="Techy Alpha T500Ultra Max 1.92'HD Display" href="/techy-alpha/p/itm3">
      Techy Alpha T500Ultra...
    </a>
  </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_amazon_modern_title_and_sponsored_recipe():
    scraper = AmazonScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(AMAZON_MODERN_SEARCH_HTML)

    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert len(sp_items) == 1
    assert sp_items[0].position == 1
    assert sp_items[0].name == "Apple iPhone Air 256 GB: Thinnest iPhone Ever"
    assert "/sspa/click" in sp_items[0].url

    await scraper.close()


@pytest.mark.asyncio
async def test_flipkart_modern_grid_svg_and_adview():
    scraper = FlipkartScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(FLIPKART_MODERN_GRID_HTML)

    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert len(sp_items) == 2
    assert sp_items[0].position == 1
    assert sp_items[0].name == "Fire-Boltt Hurricane 2026 1.3' Curved Glass Display with BT Calling"
    assert "/fire-boltt-hurricane" in sp_items[0].url

    assert sp_items[1].position == 2
    assert sp_items[1].name == "boAt Storm Call w/ 4.29 cm(1.69'), BT Calling Smartwatch"
    assert "/boat-storm-call" in sp_items[1].url

    await scraper.close()

