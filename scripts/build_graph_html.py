"""
Bygger graf-HTML (force-directed, vanilla JS+SVG) med embedded edge-data och
översättningstabell för SV/EN.

Las data/genoversikt.json + data/translations.json, harled (kanoniskt_organ, gen) -> info,
spara som data/graph_edges.json, och bygg public/index.html med datat och översättningarna
inbäddade i JS-konstanter.

Anvandning:
    python scripts/build_graph_html.py
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "genoversikt.json"
TRANSLATIONS = ROOT / "data" / "translations.json"
EDGES_OUT = ROOT / "data" / "graph_edges.json"
HTML_OUT = ROOT / "public" / "index.html"
JSON_PUBLIC = ROOT / "public" / "genoversikt.json"
EAU_SRC = ROOT / "data" / "eau-prostate.json"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="utf-8">
<title>Genoversikt - Organ vs Gen</title>
<meta name="description" content="Interactive map of the Swedish national care programme for hereditary cancer syndromes. 170 documented gene-organ links across 72 high-penetrance predisposition genes and 47 organ categories.">

<!-- Open Graph (for LinkedIn, Facebook, Slack, etc.) -->
<meta property="og:type" content="website">
<meta property="og:title" content="Gene overview - Organ vs Gene">
<meta property="og:description" content="Interactive map of the Swedish national care programme for hereditary cancer syndromes. 170 documented gene-organ links across 72 high-penetrance predisposition genes and 47 organ categories.">
<meta property="og:image" content="og-preview.png">
<meta property="og:image:alt" content="Force-directed graph showing connections between cancer predisposition genes and affected organs">
<meta property="og:locale" content="en_GB">
<meta property="og:locale:alternate" content="sv_SE">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Gene overview - Organ vs Gene">
<meta name="twitter:description" content="Interactive map of the Swedish national care programme for hereditary cancer syndromes.">
<meta name="twitter:image" content="og-preview.png">

<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #111; background: #fafaf7; }
  #root { display: flex; flex-direction: column; height: 100vh; }
  header { padding: 8px 12px; background: #fff; border-bottom: 1px solid #ddd; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 13px; }
  header h1 { font-size: 14px; font-weight: 600; margin: 0 8px 0 0; }
  header input[type=text] { font-size: 13px; padding: 4px 8px; border: 1px solid #bbb; border-radius: 4px; width: 220px; }
  header label { display: flex; align-items: center; gap: 4px; cursor: pointer; }
  header button, header a.btn { font-size: 12px; padding: 4px 10px; border: 1px solid #999; background: #fff; border-radius: 4px; cursor: pointer; text-decoration: none; color: #111; }
  header button:hover, header a.btn:hover { background: #eee; }
  #lang-toggle { display: inline-flex; border: 1px solid #999; border-radius: 4px; overflow: hidden; }
  #lang-toggle button { border: none; border-radius: 0; padding: 4px 10px; background: #fff; font-size: 12px; cursor: pointer; }
  #lang-toggle button + button { border-left: 1px solid #999; }
  #lang-toggle button.active { background: #3a7bd5; color: #fff; font-weight: 600; }
  #lang-toggle button:not(.active):hover { background: #eee; }
  #legend { display: flex; gap: 12px; align-items: center; font-size: 12px; color: #555; }
  #legend .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 4px; vertical-align: middle; }
  #info { font-size: 12px; color: #777; margin-left: auto; }
  #stage { flex: 1; position: relative; overflow: hidden; background: #fafaf7; }
  svg { width: 100%; height: 100%; cursor: grab; }
  svg.dragging { cursor: grabbing; }
  .link { stroke: #ccc; stroke-width: 1; opacity: 0.5; }
  .link.highlight { stroke: #444; stroke-width: 1.5; opacity: 1; }
  .link.src-eau { stroke: #8d6cc4; stroke-dasharray: 4 3; }
  .node { cursor: pointer; }
  .node circle { stroke: #fff; stroke-width: 1.5; }
  .node.organ circle { fill: #e07b3c; }
  .node.gene circle { fill: #3a7bd5; }
  .node.dim { opacity: 0.15; }
  .node.highlight circle { stroke: #111; stroke-width: 2; }
  .node text { font-size: 10px; pointer-events: none; user-select: none; fill: #222; paint-order: stroke; stroke: #fafaf7; stroke-width: 3; stroke-linejoin: round; }
  .node.selected text { font-weight: 700; fill: #000; }
  #tooltip { position: absolute; pointer-events: none; background: #fff; border: 1px solid #999; padding: 8px 10px; font-size: 12px; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); max-width: 320px; display: none; z-index: 10; }
  #tooltip h4 { margin: 0 0 4px; font-size: 13px; }
  #tooltip .small { color: #666; font-size: 11px; }
  #panel { position: absolute; top: 8px; right: 8px; background: #fff; border: 1px solid #ccc; padding: 8px 10px; border-radius: 4px; max-width: 320px; max-height: calc(100% - 24px); overflow: auto; font-size: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); display: none; }
  #panel h3 { margin: 0 0 6px; font-size: 13px; }
  #panel .row { padding: 2px 0; cursor: pointer; }
  #panel .row:hover { background: #f0f0f0; }
  #panel .badge { display: inline-block; min-width: 22px; text-align: center; background: #eee; border-radius: 3px; padding: 0 4px; margin-right: 6px; font-size: 11px; color: #555; }
  #panel .small { color: #666; font-size: 11px; }
</style>
</head>
<body>
<div id="root">
  <header>
    <h1 id="header-title" data-i18n="header_title">Genoversikt - Organ vs Gen</h1>
    <input type="text" id="search" data-i18n-placeholder="search_placeholder" placeholder="Sok organ eller gen...">
    <label><input type="checkbox" id="showLabels"> <span data-i18n="show_all_labels">Visa alla namn</span></label>
    <label><input type="checkbox" id="layer-rcc" checked> RCC</label>
    <label><input type="checkbox" id="layer-eau" checked> EAU prostata</label>
    <button id="reset" data-i18n="reset_button">Aterstall</button>
    <a id="downloadJson" class="btn" href="genoversikt.json" download data-i18n="download_button">Ladda ned data (JSON)</a>
    <span id="lang-toggle" role="group" aria-label="Language">
      <button type="button" data-lang="sv">SV</button>
      <button type="button" data-lang="en">EN</button>
    </span>
    <span id="legend">
      <span><span class="dot" style="background:#e07b3c"></span><span data-i18n="legend_organ">Kanoniskt organ</span> (__N_ORGAN__)</span>
      <span><span class="dot" style="background:#3a7bd5"></span><span data-i18n="legend_gene">Gen</span> (__N_GENE__)</span>
    </span>
    <span id="info"></span>
  </header>
  <div id="stage">
    <svg id="svg"></svg>
    <div id="tooltip"></div>
    <div id="panel"></div>
  </div>
</div>
<script>
const EDGES_DATA = __EDGES__;
const TRANSLATIONS = __TRANSLATIONS__;

// ---------- Language ----------
function detectInitialLang() {
  const urlLang = new URLSearchParams(window.location.search).get('lang');
  if (urlLang === 'sv' || urlLang === 'en') return urlLang;
  const stored = localStorage.getItem('genoversikt_lang');
  if (stored === 'sv' || stored === 'en') return stored;
  const browser = (navigator.language || 'sv').toLowerCase();
  if (browser.startsWith('sv')) return 'sv';
  if (browser.startsWith('en')) return 'en';
  return 'sv';
}
let currentLang = detectInitialLang();

function t(category, text) {
  if (text === undefined || text === null) return text;
  if (currentLang === 'sv') return text;
  const dict = TRANSLATIONS[category];
  if (dict && dict[text] !== undefined) return dict[text];
  return text;
}
function tUI(key) {
  const dict = TRANSLATIONS.ui[currentLang] || TRANSLATIONS.ui.sv;
  return dict[key] !== undefined ? dict[key] : key;
}

function applyStaticI18n() {
  document.documentElement.lang = tUI('html_lang');
  document.title = tUI('page_title');
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = tUI(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.setAttribute('placeholder', tUI(el.dataset.i18nPlaceholder));
  });
  document.querySelectorAll('#lang-toggle button').forEach(b => {
    b.classList.toggle('active', b.dataset.lang === currentLang);
  });
}

function setLanguage(lang) {
  if (lang !== 'sv' && lang !== 'en') return;
  currentLang = lang;
  localStorage.setItem('genoversikt_lang', lang);
  // Update URL parameter (push state, don't reload)
  const url = new URL(window.location.href);
  if (lang === 'sv') url.searchParams.delete('lang');
  else url.searchParams.set('lang', lang);
  window.history.replaceState({}, '', url.toString());
  applyStaticI18n();
  refreshNodeLabels();
  applyLabels();
  // Re-render panel if open
  if (panel.style.display === 'block' && currentSelected) {
    showPanel(currentSelected);
  }
  updateInfoCount();
}

// ---------- Graph data ----------
const nodes = new Map();
const links = [];
function addNode(id, type) {
  if (!nodes.has(id)) nodes.set(id, { id, type, label: id, deg: 0, x: 0, y: 0, vx: 0, vy: 0 });
  return nodes.get(id);
}
EDGES_DATA.forEach(e => {
  const o = addNode("O::" + e.o, "organ"); o.label = e.o;
  const g = addNode("G::" + e.g, "gene"); g.label = e.g;
  o.deg++; g.deg++;
  links.push({ source: o, target: g, data: e });
});
const nodeList = Array.from(nodes.values());
const adj = new Map();
nodeList.forEach(n => adj.set(n.id, new Set()));
links.forEach(l => { adj.get(l.source.id).add(l.target.id); adj.get(l.target.id).add(l.source.id); });

function nodeDisplayLabel(n) {
  const cat = n.type === 'organ' ? 'organs' : 'genes';
  return t(cat, n.label);
}

const cx = 700, cy = 450;
nodeList.forEach((n, i) => {
  const angle = (i / nodeList.length) * Math.PI * 2;
  const r = 350 + (Math.random() - 0.5) * 80;
  n.x = cx + r * Math.cos(angle);
  n.y = cy + r * Math.sin(angle);
});

function step() {
  const k = 1800;
  for (let i = 0; i < nodeList.length; i++) {
    const a = nodeList[i];
    for (let j = i + 1; j < nodeList.length; j++) {
      const b = nodeList[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let dist2 = dx * dx + dy * dy;
      if (dist2 < 1) dist2 = 1;
      const dist = Math.sqrt(dist2);
      const f = k / dist2;
      const fx = (dx / dist) * f, fy = (dy / dist) * f;
      a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
    }
  }
  const targetLen = 95;
  links.forEach(l => {
    const a = l.source, b = l.target;
    let dx = b.x - a.x, dy = b.y - a.y;
    let dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 1) dist = 1;
    const f = (dist - targetLen) * 0.08;
    const fx = (dx / dist) * f, fy = (dy / dist) * f;
    a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
  });
  nodeList.forEach(n => { n.vx += (cx - n.x) * 0.005; n.vy += (cy - n.y) * 0.005; });
  nodeList.forEach(n => {
    if (n.fixed) { n.vx = 0; n.vy = 0; return; }
    n.vx *= 0.78; n.vy *= 0.78;
    n.x += n.vx; n.y += n.vy;
  });
}
for (let i = 0; i < 600; i++) step();

const svg = document.getElementById('svg');
function setViewBox() {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  nodeList.forEach(n => {
    if (n.x < minX) minX = n.x; if (n.x > maxX) maxX = n.x;
    if (n.y < minY) minY = n.y; if (n.y > maxY) maxY = n.y;
  });
  const pad = 40;
  svg.setAttribute('viewBox', `${minX - pad} ${minY - pad} ${maxX - minX + pad * 2} ${maxY - minY + pad * 2}`);
}

const NS = "http://www.w3.org/2000/svg";
links.forEach(l => {
  const el = document.createElementNS(NS, 'line');
  el.setAttribute('class', 'link');
  svg.appendChild(el); l.el = el;
});
nodeList.forEach(n => {
  const g = document.createElementNS(NS, 'g');
  g.setAttribute('class', 'node ' + n.type);
  g.dataset.id = n.id;
  const c = document.createElementNS(NS, 'circle');
  const r = Math.min(14, 4 + Math.sqrt(n.deg) * 2.2);
  c.setAttribute('r', r);
  g.appendChild(c);
  const tx = document.createElementNS(NS, 'text');
  tx.setAttribute('x', r + 3); tx.setAttribute('y', 3);
  tx.textContent = nodeDisplayLabel(n);
  g.appendChild(tx);
  svg.appendChild(g);
  n.el = g; n.textEl = tx; n.r = r;
});

function refreshNodeLabels() {
  nodeList.forEach(n => { n.textEl.textContent = nodeDisplayLabel(n); });
}

function render() {
  links.forEach(l => {
    l.el.setAttribute('x1', l.source.x); l.el.setAttribute('y1', l.source.y);
    l.el.setAttribute('x2', l.target.x); l.el.setAttribute('y2', l.target.y);
  });
  nodeList.forEach(n => n.el.setAttribute('transform', `translate(${n.x},${n.y})`));
}
function applyLabels() {
  const showAll = document.getElementById('showLabels').checked;
  nodeList.forEach(n => {
    const sel = n.el.classList.contains('selected') || n.el.classList.contains('highlight');
    n.textEl.style.display = (showAll || sel || n.deg >= 4) ? '' : 'none';
  });
}
function activeLayers() {
  return { rcc: document.getElementById('layer-rcc').checked,
           eau: document.getElementById('layer-eau').checked };
}
function shownSources(l, act) {
  return (l.data.sources || [{ id: 'rcc' }]).map(s => s.id).filter(s => act[s]);
}
function applyLayers() {
  const act = activeLayers();
  const live = new Set();
  links.forEach(l => {
    const shown = shownSources(l, act);
    const on = shown.length > 0;
    l.el.style.display = on ? '' : 'none';
    l.el.classList.toggle('src-eau', on && !shown.includes('rcc'));
    if (on) { live.add(l.source.id); live.add(l.target.id); }
  });
  nodeList.forEach(n => { n.el.style.display = live.has(n.id) ? '' : 'none'; });
  if (currentSelected && live.has(currentSelected.id)) highlightNode(currentSelected);
  else if (currentSelected) clearHighlight();
}

const tooltip = document.getElementById('tooltip');
const panel = document.getElementById('panel');
let currentSelected = null;

function updateInfoCount() {
  document.getElementById('info').textContent =
    `${nodeList.length} ${tUI('info_nodes')}, ${links.length} ${tUI('info_edges')}`;
}

function clearHighlight() {
  nodeList.forEach(n => n.el.classList.remove('selected', 'highlight', 'dim'));
  links.forEach(l => l.el.classList.remove('highlight'));
  panel.style.display = 'none';
  currentSelected = null;
  updateInfoCount();
  applyLabels();
}
function highlightNode(n) {
  clearHighlight();
  currentSelected = n;
  const act = activeLayers();
  const neighbors = new Set();
  links.forEach(l => {
    if (shownSources(l, act).length === 0) return;
    if (l.source === n) neighbors.add(l.target.id);
    if (l.target === n) neighbors.add(l.source.id);
  });
  nodeList.forEach(m => {
    if (m.el.style.display === 'none') return;
    if (m === n) m.el.classList.add('selected');
    else if (neighbors.has(m.id)) m.el.classList.add('highlight');
    else m.el.classList.add('dim');
  });
  links.forEach(l => { if ((l.source === n || l.target === n) && l.el.style.display !== 'none') l.el.classList.add('highlight'); });
  applyLabels(); showPanel(n);
}
function escapeHTML(s) { return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }

function translateLR(arr) {
  return (arr || []).map(x => t('risk_phrases', x));
}
function translateSub(arr) {
  return (arr || []).map(x => t('subcategories', x));
}

function showPanel(n) {
  const act = activeLayers();
  const myLinks = links.filter(l => (l.source === n || l.target === n) && shownSources(l, act).length > 0);
  const isOrgan = n.type === 'organ';
  const otherKey = isOrgan ? 'panel_connected_to_genes' : 'panel_connected_to_organs';
  const headerLabel = isOrgan ? tUI('panel_organ') : tUI('panel_gene');
  const displayLabel = nodeDisplayLabel(n);
  let html = `<h3>${escapeHTML(displayLabel)}</h3><div class="small">${escapeHTML(headerLabel)} - ${myLinks.length} ${escapeHTML(tUI(otherKey))}</div><div style="margin-top:8px">`;
  // Sort by translated label, locale-aware
  const sortLocale = currentLang === 'en' ? 'en' : 'sv';
  myLinks.sort((a, b) => {
    const la = nodeDisplayLabel(isOrgan ? a.target : a.source);
    const lb = nodeDisplayLabel(isOrgan ? b.target : b.source);
    return la.localeCompare(lb, sortLocale);
  });
  myLinks.forEach(l => {
    const other = isOrgan ? l.target : l.source;
    const otherLabel = nodeDisplayLabel(other);
    const lr = translateLR(l.data.lr).join(' / ');
    const sub = translateSub(l.data.sub).join(', ');
    html += `<div class="row" data-id="${other.id}"><span class="badge">${other.deg}</span>${escapeHTML(otherLabel)}`;
    if (sub) html += ` <span class="small">[${escapeHTML(sub)}]</span>`;
    if (lr) html += `<div class="small" style="margin-left:30px">${escapeHTML(lr)}</div>`;
    const eau = act.eau ? (l.data.sources || []).find(s => s.id === 'eau') : null;
    if (eau) {
      const en = currentLang === 'en';
      const eauLbl = en ? { risk: 'EAU risk', beh: 'Treatment' } : { risk: 'EAU-risk', beh: 'Behandling' };
      const eauRisk = en && eau.risk_en ? eau.risk_en : eau.risk;
      const eauBeh = en && eau.behandling_en ? eau.behandling_en : eau.behandling;
      if (eauRisk) html += `<div class="small" style="margin-left:30px">${eauLbl.risk}: ${escapeHTML(eauRisk)}</div>`;
      if (eauBeh) html += `<div class="small" style="margin-left:30px">${eauLbl.beh}: ${escapeHTML(eauBeh)}</div>`;
    }
    html += `</div>`;
  });
  html += '</div>';
  panel.innerHTML = html;
  panel.style.display = 'block';
  panel.querySelectorAll('.row').forEach(r => {
    r.addEventListener('click', () => {
      const tn = nodes.get(r.dataset.id);
      if (tn) highlightNode(tn);
    });
  });
}

nodeList.forEach(n => {
  n.el.addEventListener('mouseenter', () => {
    const typeLabel = n.type === 'organ' ? tUI('tooltip_organ') : tUI('tooltip_gene');
    tooltip.innerHTML = `<h4>${escapeHTML(nodeDisplayLabel(n))}</h4><div class="small">${escapeHTML(typeLabel)} - ${n.deg} ${escapeHTML(tUI('tooltip_connections'))}</div>`;
    tooltip.style.display = 'block';
  });
  n.el.addEventListener('mousemove', e => {
    const rect = document.getElementById('stage').getBoundingClientRect();
    tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
    tooltip.style.top = (e.clientY - rect.top + 12) + 'px';
  });
  n.el.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
  n.el.addEventListener('click', e => { e.stopPropagation(); highlightNode(n); });
});

document.getElementById('stage').addEventListener('click', e => { if (e.target === svg || e.target === document.getElementById('stage')) clearHighlight(); });
document.getElementById('reset').addEventListener('click', () => { document.getElementById('search').value = ''; clearHighlight(); });
document.getElementById('showLabels').addEventListener('change', applyLabels);
document.getElementById('layer-rcc').addEventListener('change', applyLayers);
document.getElementById('layer-eau').addEventListener('change', applyLayers);

// Language toggle
document.querySelectorAll('#lang-toggle button').forEach(b => {
  b.addEventListener('click', () => setLanguage(b.dataset.lang));
});

document.getElementById('search').addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase();
  if (!q) { clearHighlight(); return; }
  // Match against both Swedish original and translated label
  const matches = nodeList.filter(n => {
    const lbl = n.label.toLowerCase();
    const tlbl = nodeDisplayLabel(n).toLowerCase();
    return lbl.includes(q) || tlbl.includes(q);
  });
  if (matches.length === 0) {
    clearHighlight();
    document.getElementById('info').textContent = tUI('info_matches_zero');
    return;
  }
  if (matches.length === 1) { highlightNode(matches[0]); return; }
  clearHighlight();
  const matchIds = new Set(matches.map(m => m.id));
  const nbrIds = new Set();
  matches.forEach(m => adj.get(m.id).forEach(id => nbrIds.add(id)));
  nodeList.forEach(n => {
    if (matchIds.has(n.id)) n.el.classList.add('selected');
    else if (nbrIds.has(n.id)) n.el.classList.add('highlight');
    else n.el.classList.add('dim');
  });
  links.forEach(l => { if (matchIds.has(l.source.id) || matchIds.has(l.target.id)) l.el.classList.add('highlight'); });
  applyLabels();
  document.getElementById('info').textContent = `${matches.length} ${tUI('info_matches')}`;
});

let dragNode = null, dragOffset = { x: 0, y: 0 };
function svgPoint(evt) {
  const pt = svg.createSVGPoint(); pt.x = evt.clientX; pt.y = evt.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}
nodeList.forEach(n => {
  n.el.addEventListener('mousedown', e => {
    e.stopPropagation(); dragNode = n;
    const p = svgPoint(e); dragOffset.x = p.x - n.x; dragOffset.y = p.y - n.y;
    n.fixed = true; svg.classList.add('dragging');
  });
});
window.addEventListener('mousemove', e => {
  if (!dragNode) return;
  const p = svgPoint(e);
  dragNode.x = p.x - dragOffset.x; dragNode.y = p.y - dragOffset.y;
  dragNode.vx = 0; dragNode.vy = 0;
  for (let i = 0; i < 3; i++) step();
  render();
});
window.addEventListener('mouseup', () => { if (dragNode) dragNode.fixed = false; dragNode = null; svg.classList.remove('dragging'); });

let panState = null;
svg.addEventListener('mousedown', e => {
  if (e.target === svg) {
    panState = { x: e.clientX, y: e.clientY, vb: { x: svg.viewBox.baseVal.x, y: svg.viewBox.baseVal.y, width: svg.viewBox.baseVal.width, height: svg.viewBox.baseVal.height } };
    svg.classList.add('dragging');
  }
});
window.addEventListener('mousemove', e => {
  if (!panState) return;
  const dx = (e.clientX - panState.x) * (panState.vb.width / svg.clientWidth);
  const dy = (e.clientY - panState.y) * (panState.vb.height / svg.clientHeight);
  svg.setAttribute('viewBox', `${panState.vb.x - dx} ${panState.vb.y - dy} ${panState.vb.width} ${panState.vb.height}`);
});
window.addEventListener('mouseup', () => { if (panState) svg.classList.remove('dragging'); panState = null; });

svg.addEventListener('wheel', e => {
  e.preventDefault();
  const vb = svg.viewBox.baseVal;
  const factor = e.deltaY > 0 ? 1.15 : 0.87;
  const pt = svgPoint(e);
  const newW = vb.width * factor, newH = vb.height * factor;
  const newX = pt.x - (pt.x - vb.x) * factor, newY = pt.y - (pt.y - vb.y) * factor;
  svg.setAttribute('viewBox', `${newX} ${newY} ${newW} ${newH}`);
}, { passive: false });

// Initial render
applyStaticI18n();
render(); setViewBox(); applyLabels(); applyLayers();
updateInfoCount();
</script>
</body>
</html>
"""


def main():
    d = json.load(SRC.open(encoding="utf-8"))
    translations = json.load(TRANSLATIONS.open(encoding="utf-8"))
    edges = defaultdict(lambda: {"livstidsrisker": [], "syndrom": set(), "subkategorier": set(), "originalnycklar": set(), "sources": {}})
    for orig, mutations in d["data"].items():
        for m in mutations:
            key = (m["kanoniskt_organ"], m["gen"])
            edges[key]["livstidsrisker"].append(m["livstidsrisk"] or "-")
            if m["syndrom"] and m["syndrom"] != "-":
                edges[key]["syndrom"].add(m["syndrom"])
            if m["subkategori"]:
                edges[key]["subkategorier"].add(m["subkategori"])
            edges[key]["originalnycklar"].add(orig)
            edges[key]["sources"].setdefault("rcc", {"id": "rcc"})

    # --- EAU-överlägg: slås ihop i samma (organ, gen)-kant ---
    if EAU_SRC.exists():
        eau = json.load(EAU_SRC.open(encoding="utf-8"))
        for g in eau["gener"]:
            key = (eau["organ"], g.get("kanonisk_gen", g["gen"]))
            src = {"id": "eau"}
            for f in ("lage", "risk", "risk_en", "behandling", "behandling_en", "kommentar", "ref"):
                if g.get(f):
                    src[f] = g[f]
            edges[key]["sources"]["eau"] = src

    full = []
    slim = []
    for (organ, gen), info in edges.items():
        full.append({
            "organ": organ, "gen": gen,
            "syndrom": sorted(info["syndrom"]),
            "subkategorier": sorted(info["subkategorier"]),
            "originalnycklar": sorted(info["originalnycklar"]),
            "livstidsrisker": info["livstidsrisker"],
            "sources": list(info["sources"].values()),
        })
        slim.append({
            "o": organ, "g": gen,
            "s": sorted(info["syndrom"]),
            "sub": sorted(info["subkategorier"]),
            "lr": [x for x in info["livstidsrisker"] if x and x != "-"],
            "sources": list(info["sources"].values()),
        })

    EDGES_OUT.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote: {EDGES_OUT} ({len(full)} kanter)")

    # Trim translations for embedding: only the parts the front-end needs
    trans_slim = {
        "ui": translations["ui"],
        "organs": translations["organs"],
        "subcategories": translations["subcategories"],
        "syndromes": translations["syndromes"],
        "genes": translations["genes"],
        "risk_phrases": translations["risk_phrases"],
    }

    n_organ = len({k[0] for k in edges})
    n_gene = len({k[1] for k in edges})
    html = HTML_TEMPLATE \
        .replace("__EDGES__", json.dumps(slim, ensure_ascii=False)) \
        .replace("__TRANSLATIONS__", json.dumps(trans_slim, ensure_ascii=False)) \
        .replace("__N_ORGAN__", str(n_organ)) \
        .replace("__N_GENE__", str(n_gene))
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Wrote: {HTML_OUT} ({len(html)} tecken)")

    # Sync data/genoversikt.json -> public/genoversikt.json sa download-lanken funkar
    JSON_PUBLIC.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote: {JSON_PUBLIC}")


if __name__ == "__main__":
    main()
