# Coop Kundeavis Scraper (OCR → Postgres)

Dette prosjektet laster ned sidebilder fra en Coop-kundeavis, kjører OCR (Tesseract med norsk), parser ut prislinjer og lagrer funnene i Postgres.

## Rask start

1) **Krav**: Docker og Docker Compose.
2) **Sett miljøvariabler** (eksempel i `.env.example`).
3) **Start Postgres** og kjør én scraping:
```bash
docker compose --env-file .env.example up -d db
docker compose --env-file .env.example run --rm scraper
```
4) Se data:
```bash
docker exec -it coopdb psql -U ${DB_USER:-postgres} -d ${DB_NAME:-kundeaviser} -c "SELECT id, circular_id, page, price_raw, price_amount, multi_qty, multi_price FROM items ORDER BY id DESC LIMIT 20;"
```

> **Tips**: For daglig kjøring, bruk host-`cron` (se lenger ned).

## Miljøvariabler
Se `.env.example` for alle. Viktige:
- `AVIS_ID`: ID for kundeavisen (f.eks. 2534)
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_PORT` (Postgres)
- `TESS_LANG="nor+eng"` for norsk+engelsk OCR.
- `MIN_CONFIDENCE` (0–100) for enkel filtrering av OCR-ord (default 60)
- `PRICE_HINTS` (true/false): prefilter linjer som inneholder ord som "kr", "%", "for", "," etc.

## Planlagt kjøring (cron)
Eksempel: kjør daglig kl 07:05:
```bash
crontab -e
# Legg til (tilpass sti):
5 7 * * * cd /path/til/coop_kundeavis_scraper && docker compose --env-file .env.example run --rm scraper >> scrape.log 2>&1
```

## Hva lagres?
Tre tabeller: `circulars`, `pages`, `items`. `items.price_raw` er den rå tekstlinjen; `price_amount`, `multi_qty`, `multi_price` normaliseres når mulig.

## Viktig
- Struktur på nettsider kan endre seg – parseren prøver flere strategier (lenker til `.jpg` i <a> eller <img>).
- OCR er "best effort". Resultatene bør kvalitetssjekkes før bruk.
- Respekter nettstedets vilkår og robots.txt før scraping.
- Dette er kun for læring/testing. Bruk ansvarlig.
