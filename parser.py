import regex as re
from typing import List, Dict, Optional

PRICE_RX = re.compile(
    r"""
    (?xi)
    (?:kr\s*)?                                   # ev. 'kr'
    (?:
        (?P<amount_dec>\d{1,3}(?:[ .]\d{3})*,\d{2})   # 29,90 / 1 299,00
        |
        (?P<amount_dash>\d{1,4})\s*[,.-]{1,2}         # 29,- / 29.-
        |
        (?P<only_int>\d{1,4})(?!\d)                   # 29 (naken)
    )
    |
    (?P<multi>(\d{1,2})\s*for\s*(\d{1,4}(?:[ .]\d{3})*(?:,\d{2})?))   # 3 for 100 / 2 for 79,90
    |
    (?P<percent>-\s*\d{1,2}\s*%|\d{1,2}\s*%)          # -40% / 40%
    """,
    flags=re.UNICODE
)

HINT_RX = re.compile(r"(?i)(kr|%|for|,\d{2}|\d+\s*for\s*\d+)")

def norm_amount(txt: str) -> Optional[float]:
    if not txt: return None
    t = txt.replace(" ", "").replace(".", "")
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None

def parse_prices_from_text(text: str, words: List[Dict] | None = None) -> List[Dict]:
    """
    Returnerer liste av funn:
      {
        product_text: str | None,
        price_raw: str,
        price_amount: float | None,
        currency: "NOK",
        offer_type: "unit" | "multi" | "percent" | "unknown",
        multi_qty: int | None,
        multi_price: float | None,
        unit: str | None,
      }
    Enkel heuristikk: del opp i linjer og behold linjer som matcher PRICE_RX.
    """
    out: List[Dict] = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # valgfritt 'hints' prefilter via env
    from os import getenv
    use_hints = getenv("PRICE_HINTS", "true").lower() == "true"
    if use_hints:
        lines = [l for l in lines if HINT_RX.search(l) or PRICE_RX.search(l)]

    for line in lines:
        m = PRICE_RX.search(line)
        if not m:
            continue

        item = {
            "product_text": None,
            "price_raw": line,
            "price_amount": None,
            "currency": "NOK",
            "offer_type": "unknown",
            "multi_qty": None,
            "multi_price": None,
            "unit": None,
        }

        if m.group("multi"):
            # f.eks "3 for 100", capture qty og pris
            qty = int(m.captures(2)[0]) if m.captures(2) else None
            ptxt = m.captures(3)[0] if m.captures(3) else None
            item["offer_type"] = "multi"
            item["multi_qty"] = qty
            item["multi_price"] = norm_amount(ptxt) if ptxt else None
        elif m.group("percent"):
            item["offer_type"] = "percent"
            # Ikke satt price_amount
        else:
            amt = None
            if m.group("amount_dec"):
                amt = norm_amount(m.group("amount_dec"))
            elif m.group("amount_dash"):
                amt = norm_amount(m.group("amount_dash"))
            elif m.group("only_int"):
                amt = norm_amount(m.group("only_int"))
            item["offer_type"] = "unit"
            item["price_amount"] = amt

        # Heuristikk: produktnavn = line uten selve pris-uttrykket, rydd whitespace
        if m:
            s, e = m.span()
            name = (line[:s] + " " + line[e:]).strip()
            name = re.sub(r"\s{2,}", " ", name).strip(" -.,;:")
            item["product_text"] = name if name else None

        out.append(item)

    return out
