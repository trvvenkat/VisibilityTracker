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


AMAZON_TITLE_LAYOUT_HTML = """
<!DOCTYPE html>
<html>
<head><title>Amazon.in : mixer grinder</title></head>
<body>
  <div class="s-main-slot">
    <!-- Feature line sits in the old brand slot; real title is in the product link -->
    <div data-component-type="s-search-result" data-asin="B0HL7707" data-uuid="uuid-feature" style="display: block;">
      <span class="puis-sponsored-label-text">Sponsored</span>
      <div data-cy="title-recipe">
        <div class="a-row a-color-secondary">
          <h2 class="a-size-mini s-line-clamp-1">
            <span>3-in-1, Mixer Grinder for home + Juicer + Food Processor, Black</span>
          </h2>
        </div>
        <a class="a-link-normal" href="/sspa/click?url=%2FPhilips-Mixer-Grinder%2Fdp%2FB0HL7707">
          <h2 class="a-size-base-plus">
            <span>Philips Stainless Steel Mixer Grinder HL7707/01, 750W, 4 Jars</span>
          </h2>
        </a>
      </div>
    </div>

    <!-- Organic card between sponsored results -->
    <div data-component-type="s-search-result" data-asin="B0ORGANIC" data-uuid="uuid-organic" style="display: block;">
      <div data-cy="title-recipe">
        <a class="a-link-normal" href="/Lifelong-Mixer/dp/B0ORGANIC">
          <h2 class="a-size-medium"><span>Lifelong Mixer Grinder 500W</span></h2>
        </a>
      </div>
    </div>

    <!-- Feature line and title are both a-size-mini; title is the heading inside the link -->
    <div data-component-type="s-search-result" data-asin="B0HL7756" data-uuid="uuid-both-mini" style="display: block;">
      <span class="puis-sponsored-label-text">Sponsored</span>
      <div data-cy="title-recipe">
        <h2 class="a-size-mini s-line-clamp-1">
          <span>25 mins Continuous Grinding, Mixer Grinder for Kitchen with 3 Speed Control, Pulse Function, Black</span>
        </h2>
        <a class="a-link-normal" href="/sspa/click?url=%2FPhilips-HL7756%2Fdp%2FB0HL7756">
          <h2 class="a-size-mini s-line-clamp-2">
            <span>Philips HL7756 Mixer Grinder 750W, with 3 Stainless Steel Jars</span>
          </h2>
        </a>
      </div>
    </div>

    <!-- One-line title, no subheading, name only inside the sponsored click link -->
    <div data-component-type="s-search-result" data-asin="B0ONELINE" data-uuid="uuid-one-line" style="display: block;">
      <span class="puis-sponsored-label-text">Sponsored</span>
      <div data-cy="title-recipe">
        <a class="a-link-normal s-line-clamp-1" href="/sspa/click?ie=UTF8&url=%2FPrestige-Iris%2Fdp%2FB0ONELINE">
          <span class="a-size-base-plus a-color-base a-text-normal">Prestige Iris 750 Watt Mixer Grinder with 4 Jars</span>
        </a>
      </div>
    </div>
  </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_amazon_title_ignores_feature_line_and_reads_one_line_cards():
    scraper = AmazonScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(AMAZON_TITLE_LAYOUT_HTML)

    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert len(sp_items) == 3

    assert sp_items[0].position == 1
    assert sp_items[0].name == "Philips Stainless Steel Mixer Grinder HL7707/01, 750W, 4 Jars"
    assert "/sspa/click" in sp_items[0].url

    assert sp_items[1].position == 2
    assert sp_items[1].name == "Philips HL7756 Mixer Grinder 750W, with 3 Stainless Steel Jars"

    assert sp_items[2].position == 3
    assert sp_items[2].name == "Prestige Iris 750 Watt Mixer Grinder with 4 Jars"
    assert "/sspa/click" in sp_items[2].url

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


FLIPKART_LIST_LAYOUT_HTML = """
<!DOCTYPE html>
<html>
<head><title>mixer grinder for kitchen - Buy Products Online at Best Price in India - Flipkart.com</title></head>
<body>
  <!-- Sponsored list card: SVG wordmark, title only in RG5Slk and img alt, wrapping link has no title -->
  <div data-id="MIXF5D4KPARAZNZA" style="display: block;">
    <a class="k7wcnx" href="/butterfly-rapid-750-w-juicer-mixer-grinder/p/itm9202a2047fd97?pid=MIXF5D4KPARAZNZA&amp;fm=organic">
      <label><span>Add to Compare</span></label>
      <img alt="Butterfly Rapid 750 W Juicer Mixer Grinder" src="https://rukminim2.flixcart.com/image/312/312/mixer.jpeg"/>
      <div class="t7gRps"><svg width="62" height="18" xmlns="http://www.w3.org/2000/svg"><rect width="62" height="18" fill="white"></rect></svg></div>
      <div class="RG5Slk">Butterfly Rapid 750 W Juicer Mixer Grinder</div>
    </a>
  </div>

  <!-- Second sponsored list card, same shape -->
  <div data-id="MIXH8YJA43VTGXQG" style="display: block;">
    <a class="k7wcnx" href="/grand-plus-sky-blue-550-w-mixer-grinder/p/itmd5ea4138f7fa5?pid=MIXH8YJA43VTGXQG&amp;fm=organic">
      <label><span>Add to Compare</span></label>
      <img alt="Grand plus Sky Blue 550 W Mixer Grinder" src="https://rukminim2.flixcart.com/image/312/312/grand.jpeg"/>
      <div class="t7gRps"><svg width="62" height="18" xmlns="http://www.w3.org/2000/svg"><rect width="62" height="18" fill="white"></rect></svg></div>
      <div class="RG5Slk">Grand plus Sky Blue 550 W Mixer Grinder</div>
    </a>
  </div>

  <!-- Organic bestseller: same title node, no sponsored SVG -->
  <div data-id="MIXGSF4YQSJYKR5J" style="display: block;">
    <a class="k7wcnx" href="/crompton-ds-500-w-mixer-grinder/p/itmbestseller?pid=MIXGSF4YQSJYKR5J&amp;fm=organic">
      <label><span>Add to Compare</span></label>
      <img alt="Crompton DS 500 W Mixer Grinder" src="https://rukminim2.flixcart.com/image/312/312/crompton.jpeg"/>
      <div class="RG5Slk">Crompton DS 500 W Mixer Grinder</div>
    </a>
  </div>
</body>
</html>
"""


FLIPKART_DISPLAY_HTML = """
<!DOCTYPE html>
<html>
<head><title>mixer grinder for kitchen</title></head>
<body>
  <div class="_1yR-bH" style="display: block;">Add to Compare</div>
  <div data-tracking-id="top-banner" style="display: block;">
    <div>Sponsored</div>
    <div>Butterfly Official Store</div>
  </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_flipkart_list_layout_reads_rg5slk_title():
    scraper = FlipkartScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(FLIPKART_LIST_LAYOUT_HTML)

    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert len(sp_items) == 2

    assert sp_items[0].position == 1
    assert sp_items[0].name == "Butterfly Rapid 750 W Juicer Mixer Grinder"
    assert "/butterfly-rapid-750-w-juicer-mixer-grinder" in sp_items[0].url

    assert sp_items[1].position == 2
    assert sp_items[1].name == "Grand plus Sky Blue 550 W Mixer Grinder"
    assert "/grand-plus-sky-blue-550-w-mixer-grinder" in sp_items[1].url

    await scraper.close()


@pytest.mark.asyncio
async def test_flipkart_sponsored_display_ignores_add_to_compare():
    scraper = FlipkartScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(FLIPKART_DISPLAY_HTML)

    display = await scraper._extract_sponsored_display()
    assert display is not None
    assert display.name == "Butterfly Official Store"

    await scraper.close()


FLIPKART_RESTACKED_HTML = """
<!DOCTYPE html>
<html>
<head><title>grinder mixer machine</title></head>
<body>
  <!-- Document order groups the two Cromptons. Flex order is the on-screen order:
       Ameo, Grand plus, BlendX. All three are sponsored, including two from one brand. -->
  <div style="display: flex; flex-direction: column;">
    <div data-id="AMEO" style="order: 1; display: block;">
      <a class="k7wcnx" href="/crompton-ameo-750-w-mixer-grinder/p/itm-ameo">
        <div class="t7gRps"><svg width="62" height="18"></svg></div>
        <div class="RG5Slk">Crompton Ameo 750 W Mixer Grinder</div>
      </a>
    </div>
    <div data-id="BLENDX" style="order: 3; display: block;">
      <a class="k7wcnx" href="/crompton-blendx-500-w-juicer-mixer-grinder/p/itm-blendx">
        <div class="t7gRps"><svg width="62" height="18"></svg></div>
        <div class="RG5Slk">Crompton BlendX 500 W Juicer Mixer Grinder</div>
      </a>
    </div>
    <div data-id="GRAND" style="order: 2; display: block;">
      <a class="k7wcnx" href="/grand-plus-sky-blue-550-w-mixer-grinder/p/itm-grand">
        <div class="t7gRps"><svg width="62" height="18"></svg></div>
        <div class="RG5Slk">Grand plus Sky Blue 550 W Mixer Grinder</div>
      </a>
    </div>
  </div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_flipkart_sponsored_follows_onscreen_order_for_repeated_brands():
    scraper = FlipkartScraper(headless=True)
    await scraper.initialize()
    assert scraper._page is not None

    await scraper._page.set_content(FLIPKART_RESTACKED_HTML)

    sp_items = await scraper._extract_sponsored_products(top_n=3)
    assert [item.name for item in sp_items] == [
        "Crompton Ameo 750 W Mixer Grinder",
        "Grand plus Sky Blue 550 W Mixer Grinder",
        "Crompton BlendX 500 W Juicer Mixer Grinder",
    ]
    assert [item.position for item in sp_items] == [1, 2, 3]

    await scraper.close()

