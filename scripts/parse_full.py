"""
Parser: RCC Genoversikt HTML -> genoversikt.json (raw, utan kanonisk mapping).

Las nedladdad HTML-cache fran data/genoversikt-source.html och producera
en strukturerad JSON med:
- Originalnyckel (organrubrik) -> lista av mutationer (gener) med strukturerad text per kort.

Anvandning:
    python scripts/parse_full.py

Output skrivs till: data/genoversikt-raw.json (innan kanonisk mapping pabarjas).
"""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "genoversikt-source.html"
OUT = ROOT / "data" / "genoversikt-raw.json"
SOURCE_URL = "https://kunskapsbanken.cancercentrum.se/diagnoser/arftliga-tumorrisksyndrom-hos-barn-och-vuxna/vardprogram/genoversikt/"


def clean(text):
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_card(card, gene_name, syndrome_name):
    btn = card.select_one(".card-header button")
    organ = clean(btn.get_text()) if btn else ""

    body = card.select_one(".card-body")
    if body is None:
        return organ, None

    def first_text(selector):
        el = body.select_one(selector)
        return clean(el.get_text(" ", strip=True)) if el else ""

    items = body.select(".livstidsrisk-item")
    annat_relevant = clean(items[0].get_text(" ", strip=True)) if len(items) >= 1 else ""
    livstidsrisk = clean(items[1].get_text(" ", strip=True)) if len(items) >= 2 else ""

    vp_title = body.select_one(".vp-title")
    vp_parts = []
    if vp_title:
        sib = vp_title.next_sibling
        while sib is not None:
            if hasattr(sib, "get") and sib.name == "div" and sib.get("class") and any(
                c.endswith("-title") for c in sib.get("class")
            ):
                break
            if hasattr(sib, "get_text"):
                txt = clean(sib.get_text(" ", strip=True))
                if txt:
                    href = sib.get("href") if sib.name == "a" else None
                    vp_parts.append(f"{txt} ({href})" if href else txt)
            sib = sib.next_sibling
    vp_text = " | ".join(p for p in vp_parts if p)

    ref_div = body.select_one(".reference-item")
    ref_parts = []
    if ref_div:
        for a in ref_div.find_all("a"):
            href = a.get("href", "")
            txt = clean(a.get_text())
            if href and href != txt:
                ref_parts.append(f"{txt} ({href})")
            elif txt:
                ref_parts.append(txt)
        if not ref_parts:
            ref_parts.append(clean(ref_div.get_text(" ", strip=True)))
    ref_text = " | ".join(p for p in ref_parts if p)

    return organ, {
        "gen": gene_name,
        "syndrom": syndrome_name,
        "annat_relevant": annat_relevant,
        "livstidsrisk": livstidsrisk,
        "uppfoljning": first_text(".followup-item"),
        "startalder": first_text(".start-age-item"),
        "slut_av_kontroller": first_text(".end-followup-age-item"),
        "nationellt_vardprogram": vp_text,
        "uppfoljning_annat": first_text(".other-followup-item"),
        "referens": ref_text,
    }


def main():
    if not SRC.exists():
        print(f"ERROR: {SRC} saknas. Ladda om RCC-sidan med WebFetch och spara HTML.", file=sys.stderr)
        sys.exit(1)

    html = SRC.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    groups = soup.select("div.syndrom-group")
    by_organ = {}
    gene_count = 0
    card_count = 0

    for g in groups:
        gene = g.get("data-gen", "").strip()
        if not gene:
            continue
        gene_count += 1
        syndrome_div = g.select_one(".syndrom")
        syndrome = clean(syndrome_div.get_text()) if syndrome_div else ""
        cards = g.select(".card.card-collapse")
        for card in cards:
            organ, data = parse_card(card, gene, syndrome)
            if data is None or not organ:
                continue
            card_count += 1
            by_organ.setdefault(organ, []).append(data)

    sorted_by_organ = dict(sorted(by_organ.items(), key=lambda x: x[0].lower()))
    for organ, lst in sorted_by_organ.items():
        lst.sort(key=lambda d: d["gen"].lower())

    payload = {
        "_metadata": {
            "kalla": SOURCE_URL,
            "antal_gener": gene_count,
            "antal_organ_kort": card_count,
            "antal_unika_organ": len(sorted_by_organ),
            "struktur": "originalnyckel (organ) -> lista av mutationer (gener) med strukturerad text per kort",
        },
        "data": sorted_by_organ,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT}")
    print(f"  Gener: {gene_count}, kort: {card_count}, unika organ: {len(sorted_by_organ)}")


if __name__ == "__main__":
    main()
