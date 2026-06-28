"""
Bygger kanonisk version av genoversikt-data.

Las data/genoversikt-raw.json (fran parse_full.py), berika varje mutation
med kanoniskt_organ + subkategori, och lagg till topp-niva-index
'kanoniska_organ' (kanonisk -> subkategori -> [originalnycklar]).

Output: data/genoversikt.json (overskrives).

Anvandning:
    python scripts/build_canonical.py
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "genoversikt-raw.json"
OUT = ROOT / "data" / "genoversikt.json"

# original-nyckel -> (kanoniskt_organ, subkategori | None)
MAPPING = {
    # Generiska samlingar
    "Andra maligna tumörer":                          ("Andra maligna tumörer", None),
    "Andra relevanta symptom":                        ("Andra relevanta symptom", None),
    "Benigna tumörer":                                ("Benigna tumörer", None),
    "Multipla tumörer":                               ("Multipla tumörer", None),
    "Saknar organ/symtom":                            ("Saknar organ/symtom", None),
    "Övriga cancer":                                  ("Övriga cancer", None),
    "Övrigt":                                         ("Övrigt", None),

    # Binjure
    "Binjure":                                        ("Binjure", None),
    "Binjurar (feokromocytom)":                       ("Binjure", "feokromocytom"),
    "Binjure (Feokromocytom)":                        ("Binjure", "feokromocytom"),
    "Binjure - feokromocytom":                        ("Binjure", "feokromocytom"),
    "Binjurebark":                                    ("Binjure", "bark"),

    "Bisköldkörtel":                                  ("Bisköldkörtel", None),

    # Lunga
    "Bronkialcarcinoid":                              ("Lunga", "bronkialcarcinoid"),
    "Lunga":                                          ("Lunga", None),
    "Lungblastom":                                    ("Lunga", "lungblastom"),
    "Lungcystor/pneumothorax":                        ("Lunga", "lungcystor/pneumothorax"),

    # Brost
    "Bröst":                                          ("Bröst", None),
    "Bröstcancer":                                    ("Bröst", "kvinnor"),
    "Bröst (kvinnor)":                                ("Bröst", "kvinnor"),
    "Bröst, kvinnor":                                 ("Bröst", "kvinnor"),
    "Bröst, kvinnor.":                                ("Bröst", "kvinnor"),
    "Kvinnor bröst":                                  ("Bröst", "kvinnor"),
    "Bröst (män)":                                    ("Bröst", "män"),
    "Bröst lobulär (kvinnor)":                        ("Bröst", "lobulär (kvinnor)"),

    # Bukspottkortel
    "Bukspottkörtel":                                 ("Bukspottkörtel", None),
    "Bukspottkörtel (PNET)":                          ("Bukspottkörtel", "PNET (neuroendokrin)"),
    "Endokrin bukspottkörtel":                        ("Bukspottkörtel", "endokrin"),

    # Magsack
    "Magsäck":                                        ("Magsäck", None),
    "Magsäck/tolvfingertarm":                         ("Magsäck/tolvfingertarm", None),
    "Carcinoider i magsäck/tolvfingertarm":           ("Magsäck/tolvfingertarm", "carcinoider"),
    "Magsäck, tunntarm och tjocktarm.":               ("Magsäck", "magsäck/tunntarm/tjocktarm"),
    "Tolvfingertarm":                                 ("Tolvfingertarm", None),

    # Tjocktarm
    "Tjock- och ändtarm":                             ("Tjock- och ändtarm", None),
    "Tjocktarm och ändtarm":                          ("Tjock- och ändtarm", None),

    # Endokrina ovrigt
    "Endolymfatiska säcken i innerörat (ELST)":       ("Endolymfatiska säcken i innerörat (ELST)", None),
    "GIST":                                           ("GIST", None),
    "Hypofys":                                        ("Hypofys", None),

    # Hematologi
    "Hematologiska maligniteter":                     ("Hematologiska maligniteter", None),
    "Lymfom":                                         ("Lymfom", None),

    # Hjarna
    "Hjärna":                                         ("Hjärna", None),
    "Hjärna, ryggmärg och dess hinnor":               ("Hjärna", "ryggmärg och dess hinnor"),
    "Hjärna, ryggmärg och dess hinnor (hemangioblastom)": ("Hjärna", "ryggmärg och dess hinnor (hemangioblastom)"),
    "Hjärna, ryggmärg och dess hinnor (Optikus gliom)":   ("Hjärna", "Optikus gliom"),
    "Hjärna-subependymalt jättecellsastrocytom (SEGA)":   ("Hjärna", "SEGA (subependymalt jättecellsastrocytom)"),

    "Medulloblastom":                                 ("Medulloblastom", None),
    "Meningiom":                                      ("Meningiom", None),
    "Schwannom":                                      ("Schwannom", None),
    "Malign perifer nervskidetumör (MPNST)":          ("Malign perifer nervskidetumör (MPNST)", None),

    "Hjärtfibrom":                                    ("Hjärtfibrom", None),

    # Hud
    "Hud":                                            ("Hud", None),
    "Hud - basalcellscancer (BCC).":                  ("Hud", "basalcellscancer (BCC)"),
    "Hud/fibrofolliculom":                            ("Hud", "fibrofolliculom"),

    # Konsorgan
    "Könsträngs tumör med annular tubules":           ("Könsträngs tumör med annular tubules", None),
    "Livmoderhals, germinala celler (SCTAT), äggstockar, livmoderkropp": ("Livmoderhals, germinala celler (SCTAT), äggstockar, livmoderkropp", None),
    "Livmoderkropp":                                  ("Livmoderkropp", None),

    "Lever":                                          ("Lever", None),
    "Mesoteliom (peritoneum och pleura)":             ("Mesoteliom (peritoneum och pleura)", None),

    # Njurar
    "Njurar":                                         ("Njurar", None),
    "Njurar (angiomyolipom)":                         ("Njurar", "angiomyolipom"),
    "Njurar (ffa papillär njurcancer )":              ("Njurar", "papillär"),
    "Njurar (klarcellig njurcancer)":                 ("Njurar", "klarcellig"),
    "Njurar (klarcellig)":                            ("Njurar", "klarcellig"),

    # Ogon
    "Ögon":                                           ("Ögon", None),
    "Ögon (näthinna)":                                ("Ögon", "näthinna"),
    "Näthinna (retinala hemangioblastom)":            ("Ögon", "näthinna (retinala hemangioblastom)"),

    "Osteoporos":                                     ("Osteoporos", None),

    # Paragangliom
    "Paragangliom":                                   ("Paragangliom/feokromocytom", "paragangliom"),
    "Paragangliom/feokromocytom":                     ("Paragangliom/feokromocytom", None),

    "Prostata":                                       ("Prostata", None),

    # Rhabdoida
    "Rhabdoida tumörer":                              ("Rhabdoida tumörer", None),
    "Rhaboida tumörer (olika lokalisationer)":        ("Rhabdoida tumörer", "olika lokalisationer"),

    # Sarkom
    "Sarkom":                                         ("Sarkom", None),
    "Sarkom i muskler, skelett och sköldkörtelcancer":("Sarkom", "muskler/skelett + sköldkörtelcancer"),

    # Skoldkortel
    "Sköldkörtel":                                    ("Sköldkörtel", None),
    "Sköldkörteln":                                   ("Sköldkörtel", None),
    "Sköldkörtel (medullär)":                         ("Sköldkörtel", "medullär"),

    "Tymuscarcinoid":                                 ("Tymuscarcinoid", None),
    "Tänder- odontogena keratocystor (OKC).":         ("Tänder", "odontogena keratocystor (OKC)"),
    "Urinvägar":                                      ("Urinvägar", None),

    # Aggstockar
    "Äggstockar":                                     ("Äggstockar", None),
    "Äggstockscancer":                                ("Äggstockar", None),
    "Äggstockar (könssträngstumörer).":               ("Äggstockar", "könssträngstumörer"),
    "Äggstockar (småcellig äggstockscancer, hyperkalcemisk typ, SCCOHT).": ("Äggstockar", "SCCOHT (småcellig, hyperkalcemisk typ)"),
    "Äggstocksfibrom":                                ("Äggstocksfibrom", None),
    "Äggstockar/äggledare":                           ("Äggstockar/äggledare", None),
    "Äggstockar/äggledare.":                          ("Äggstockar/äggledare", None),
}


def main():
    src = json.load(SRC.open(encoding="utf-8"))
    metadata = src["_metadata"]
    data = src["data"]

    missing = [k for k in data if k not in MAPPING]
    extra = [k for k in MAPPING if k not in data]
    if missing:
        print(f"WARNING: {len(missing)} keys saknas i MAPPING:")
        for k in missing:
            print(f"  - {k}")
    if extra:
        print(f"WARNING: {len(extra)} keys i MAPPING saknas i data:")
        for k in extra:
            print(f"  - {k}")
    if missing:
        raise SystemExit("MAPPING ar inte komplett. Lagg till de saknade nycklarna.")

    new_data = {}
    for orig, mutations in data.items():
        kanon, sub = MAPPING[orig]
        enriched = []
        for m in mutations:
            new_entry = {
                "gen": m["gen"],
                "syndrom": m["syndrom"],
                "kanoniskt_organ": kanon,
                "subkategori": sub,
                **{k: v for k, v in m.items() if k not in ("gen", "syndrom")},
            }
            enriched.append(new_entry)
        new_data[orig] = enriched

    canon_index = defaultdict(lambda: defaultdict(list))
    for orig in data.keys():
        kanon, sub = MAPPING[orig]
        sub_label = sub if sub else "_ospecificerat"
        canon_index[kanon][sub_label].append(orig)

    canon_index_clean = {}
    for kanon in sorted(canon_index.keys(), key=str.lower):
        subs = canon_index[kanon]
        sub_keys = sorted(subs.keys(), key=lambda s: (s != "_ospecificerat", s.lower()))
        total = sum(len(data[orig]) for sub in subs.values() for orig in sub)
        canon_index_clean[kanon] = {
            "antal_mutationer": total,
            "antal_originalnycklar": sum(len(v) for v in subs.values()),
            "subkategorier": {sk: sorted(subs[sk]) for sk in sub_keys},
        }

    metadata = dict(metadata)
    metadata["antal_kanoniska_organ"] = len(canon_index_clean)
    metadata["faltforklaringar"] = {
        "gen": "Genens namn (med ev. monoallelisk/biallelisk-suffix)",
        "syndrom": "Tumorrisksyndrom som genen ar associerad med",
        "kanoniskt_organ": "Overgripande organkategori (sammanslagning av nara-dubletter)",
        "subkategori": "Detalj inom kanoniskt organ (null = ospecificerat/generiskt)",
        "annat_relevant": "Annat relevant om genen/syndromet",
        "livstidsrisk": "Livstidsrisk for cancer/tumor i organet",
        "uppfoljning": "Rekommenderad uppfoljning/screening",
        "startalder": "Startalder for kontroller",
        "slut_av_kontroller": "Slutalder for kontroller",
        "nationellt_vardprogram": "Lank till nationellt vardprogram",
        "uppfoljning_annat": "Uppfoljning av annat skal an cancerrisk",
        "referens": "Referens for uppfoljningsrekommendationer",
    }
    metadata["struktur"] = (
        "tumorsjukdom (originalnyckel) -> lista av mutationer med kanoniskt_organ + subkategori. "
        "Toppnivans 'kanoniska_organ'-index mappar kanonisk -> subkategori -> [originalnycklar]."
    )

    payload = {
        "_metadata": metadata,
        "kanoniska_organ": canon_index_clean,
        "data": new_data,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {OUT}")
    print(f"  Originalnycklar: {len(new_data)}, kanoniska organ: {len(canon_index_clean)}")


if __name__ == "__main__":
    main()
