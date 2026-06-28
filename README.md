# Genoversikt – Organ ↔ Gen graf

Interaktiv visualisering av sambanden mellan ärftliga genmutationer och tumörsjukdomar/organ, baserad på RCC:s nationella vårdprogram.

**Källa:** [kunskapsbanken.cancercentrum.se/.../genoversikt](https://kunskapsbanken.cancercentrum.se/diagnoser/arftliga-tumorrisksyndrom-hos-barn-och-vuxna/vardprogram/genoversikt/)

## Innehåll

```
genoversikt-graf/
├── README.md                       ← denna fil
├── data/
│   ├── genoversikt-source.html     ← HTML-snapshot av RCC-sidan (källa)
│   ├── genoversikt-raw.json        ← (genereras av parse_full.py) rå struktur utan kanonisk mapping
│   ├── genoversikt.json            ← kanonisk struktur (87 originalnycklar + 47 kanoniska organ)
│   └── graph_edges.json            ← (genereras) härledda edges (organ ↔ gen) för grafen
├── scripts/
│   ├── parse_full.py               ← HTML → data/genoversikt-raw.json
│   ├── build_canonical.py          ← raw → data/genoversikt.json (innehåller MAPPING-tabellen)
│   └── build_graph_html.py         ← genoversikt.json → public/index.html + data/graph_edges.json
└── public/
    ├── index.html                  ← grafen (deploybar)
    └── genoversikt.json            ← kopia av datat (för "Ladda ned data"-knappen i grafen)
```

## Dataflöde

```
RCC HTML (data/genoversikt-source.html)
         │  parse_full.py
         ▼
data/genoversikt-raw.json   ← organrubrik → mutationer (osanerade nycklar)
         │  build_canonical.py  (innehåller MAPPING)
         ▼
data/genoversikt.json       ← + kanoniskt_organ, subkategori, kanoniska_organ-index
         │  build_graph_html.py
         ▼
data/graph_edges.json       ← (organ, gen) → metadata
public/index.html           ← graf med embedded edge-data
public/genoversikt.json     ← kopia (för download-knappen)
```

## Vanliga uppgifter

### Iterera på grafens utseende eller interaktion

Redigera `HTML_TEMPLATE` i `scripts/build_graph_html.py`. Kör sedan:

```bash
python scripts/build_graph_html.py
```

Öppna `public/index.html` i webbläsare för att se resultatet.

### Justera den kanoniska mappningen

Redigera `MAPPING`-dict:en i `scripts/build_canonical.py`. Kör sedan:

```bash
python scripts/build_canonical.py
python scripts/build_graph_html.py   # regenerera grafen
```

### Hämta nyare version av RCC-sidan

Spara den nya HTML-källan som `data/genoversikt-source.html` (t.ex. via WebFetch eller `curl`), och kör hela kedjan:

```bash
python scripts/parse_full.py
python scripts/build_canonical.py
python scripts/build_graph_html.py
```

`build_canonical.py` varnar om nya organrubriker dyker upp som inte finns i MAPPING — då behöver du lägga till dem innan kedjan slutförs.

### Deploya grafen

Dra `public/`-mappen till [app.netlify.com/drop](https://app.netlify.com/drop). Filen `index.html` är fristående (inga externa beroenden) och `genoversikt.json` finns i samma mapp så download-länken funkar.

## Beroenden

- **Python 3** med `beautifulsoup4`:
  ```bash
  pip install beautifulsoup4
  ```
- Inga JS- eller bibliotek-beroenden för grafen (vanilla JS+SVG).

## Datadetaljer

- **74 gener** (varianter inkluderar monoallelisk/biallelisk-suffix där det skiljer)
- **171 organ-kort** totalt
- **87 originalnycklar** (organrubriker som de står på RCC-sidan)
- **47 kanoniska organkategorier** efter normalisering
- **170 kanter** (organ ↔ gen) i grafen

Varje kant har: syndrom, ev. subkategori, livstidsrisk, och pekare till alla originalnycklar som matchar (för "Bröst" t.ex. samlas Bröst, Bröst (kvinnor), Bröstcancer m.fl.).

## Uppdateringshistorik

- *2026-04-26*: Initial extraktion + kanonisk mapping + force-directed graf.

## Licens

- **Kod** (`scripts/` + grafens HTML/JS): [MIT](LICENSE)
- **Data** (`data/` samt `public/genoversikt.json`): [CC BY 4.0](data/LICENSE)

Datat är en sammanställd och normaliserad mappning härledd ur publika kliniska
vårdprogram (RCC, EAU m.fl.). CC BY 4.0 gäller denna sammanställning och dess
grafrepresentation, inte de underliggande källdokumenten, vars upphovsrätt
ligger kvar hos respektive utgivare. Materialet är ett referens-/beslutsstöd,
inte en klinisk rekommendation.
