import os
import sys
import time
import re
import logging
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from db import DB
from ocr import ocr_image_bytes
from parser import parse_prices_from_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

BASE = "https://kundeavis.coop.no/aviser/"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; CoopScraper/1.0; +https://example.local)"
})

def get_page(url: str) -> str:
    r = SESSION.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def resolve_image_urls(avis_id: str) -> list[str]:
    """
    Prøv flere visninger og plukk ut .jpg/.jpeg-URL-er (absolutte).
    """
    candidates = [
        f"{BASE}app/?grid=1&id={avis_id}&p=1",
        f"{BASE}?id={avis_id}",
    ]
    imgs = []
    for u in candidates:
        try:
            html = get_page(u)
        except Exception as e:
            logging.warning("Feil ved henting %s: %s", u, e)
            continue
        soup = BeautifulSoup(html, "html.parser")
        # <a href="...jpg"> eller <img src="...jpg">
        for tag in soup.find_all(["a", "img"]):
            href = tag.get("href") or tag.get("src") or tag.get("data-src")
            if not href:
                continue
            if ".jpg" in href.lower() or ".jpeg" in href.lower():
                full = urljoin(u, href)
                imgs.append(full)
        if imgs:
            break  # fant noen – bra nok
    # Rydd duplikater, behold naturlig rekkefølge
    seen = set()
    ordered = []
    for x in imgs:
        if x not in seen:
            seen.add(x); ordered.append(x)
    logging.info("Fant %d sidebilder", len(ordered))
    return ordered

def extract_dates_and_title(html: str):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    # Finn periode "dd.mm.yyyy – dd.mm.yyyy"
    date_rx = re.compile(r"(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}).{0,5}(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})")
    m = date_rx.search(text)
    valid_from = valid_to = None
    if m:
        try:
            valid_from = dateparser.parse(m.group(1), dayfirst=True).date()
            valid_to   = dateparser.parse(m.group(2), dayfirst=True).date()
        except Exception:
            pass
    title = None
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    return title, valid_from, valid_to

def fetch_html_for_meta(avis_id: str) -> str | None:
    for u in (f"{BASE}app/?grid=1&id={avis_id}&p=1", f"{BASE}?id={avis_id}"):
        try:
            return get_page(u)
        except Exception:
            continue
    return None

def main():
    avis_id = os.getenv("AVIS_ID", "").strip()
    if not avis_id:
        logging.error("AVIS_ID må settes (env).")
        sys.exit(2)

    db = DB.from_env()
    db.migrate()

    meta_html = fetch_html_for_meta(avis_id) or ""
    title, vfrom, vto = extract_dates_and_title(meta_html)
    circular_id = db.ensure_circular(source_id=int(avis_id), title=title, valid_from=vfrom, valid_to=vto)
    logging.info("Circular id=%s title=%s period=%s–%s", circular_id, title, vfrom, vto)

    img_urls = resolve_image_urls(avis_id)
    if not img_urls:
        logging.error("Fant ingen .jpg-sider for avis %s", avis_id)
        sys.exit(1)

    for i, url in enumerate(img_urls, start=1):
        try:
            r = SESSION.get(url, timeout=60)
            r.raise_for_status()
        except Exception as e:
            logging.warning("Hopp over side %s: %s", url, e)
            continue

        page_id = db.ensure_page(circular_id, i, url)
        logging.info("OCR side %d (%s)", i, urlparse(url).path.rsplit('/', 1)[-1])

        text, words = ocr_image_bytes(r.content)
        items = parse_prices_from_text(text, words=words)
        logging.info("  fant %d prislinjer", len(items))

        for it in items:
            db.insert_item(
                circular_id=circular_id,
                page=i,
                page_id=page_id,
                product_text=it.get("product_text"),
                price_raw=it.get("price_raw"),
                price_amount=it.get("price_amount"),
                currency=it.get("currency", "NOK"),
                offer_type=it.get("offer_type"),
                multi_qty=it.get("multi_qty"),
                multi_price=it.get("multi_price"),
                unit=it.get("unit"),
            )

    logging.info("Ferdig.")

if __name__ == "__main__":
    main()
