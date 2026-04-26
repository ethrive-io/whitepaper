#!/usr/bin/env python3
"""
Build a PDF for every ethrive spec Markdown file.

Layout:
  WHITEPAPER.md             — non-implementer front-door whitepaper.
  WHITEPAPER_NON_TECHNICAL.md — plain-language introduction for non-technical readers.
  specs/CORE.md             — core protocol (includes every subsystem).
  specs/<OTHER>.md          — standalone companion docs (PRIMER,
                              ARCHITECTURE, GLOSSARY, SYNC, DECISIONS,
                              EXAMPLES, ROSETTA_STONE, BUILDING_PEERS,
                              BUILDING_APPS, BUILDING_SHARED_APPS,
                              BUILDING_SQL_BACKENDS,
                              BUILDING_WITH_SANDBOX, CHEATSHEET).
  specs/modules/<CATEGORY>/<MODULE>.md — module specs, grouped by
                              category:
                                handlers/  APP, CHAT, CRDT, EVM, FILE,
                                           KV, PROFILE, RPC, SETTINGS,
                                           SOCIAL-RECOVERY, SQL
                                sdk/       CRDT-LWW-BRIDGE,
                                           GOVERNANCE-UX,
                                           NOTIFICATION-DELEGATE,
                                           SDK-CONFLICT-UI
                                devtools/  SANDBOX
                                research/  RESEARCH-DORMANT-FALLBACK

Pipeline:

  1. Read the Markdown.
  2. Pre-render every ```mermaid block to inline SVG via Kroki
     (https://kroki.io — no local dependency beyond an internet
     connection). Cached on disk between runs.
  3. Post-process each SVG so WeasyPrint can render it:
     - strip the <style> block that WeasyPrint would otherwise render
       as visible text;
     - inject presentation attributes (fill, stroke, …) on typed
       elements so nodes, edges, arrows keep correct colours without
       the stripped CSS;
     - convert <foreignObject>-HTML labels to native <text>/<tspan>;
     - add xml:space="preserve" so label spaces don't collapse;
     - replace width="100%" with explicit dimensions from the viewBox.
  4. Auto-tag untyped ``` code blocks as Dart/JSON so Pandoc's
     Skylighting gives them syntax highlighting.
  5. Run Pandoc to produce HTML.
  6. Post-process the HTML: cover, title page, part openers, TOC
     with page numbers via target-counter, and an alphabetical Index.
  7. Render the HTML with WeasyPrint to produce a PDF.

The spec markdown lives under `specs/` (core + standalone docs)
and `specs/modules/<category>/` (module specs by category:
handlers, sdk, devtools, research) at the repository root; this
script lives at `docs/scripts/pdf/` alongside `book.css` and
`highlight.theme`.

Usage:
  ./create_pdfs.py                     # write every PDF to /tmp (8 parallel workers)
  ./create_pdfs.py OUTPUT_DIR          # write every PDF to OUTPUT_DIR
  ./create_pdfs.py --only GLOSSARY     # build one doc by stem
  ./create_pdfs.py --parallel 4        # override concurrency (default 8; 1 = serial)
"""

import argparse
import html as html_lib
import re
import subprocess
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

HERE       = Path(__file__).resolve().parent
# tools/pdf/create_pdfs.py → 2 levels up to repo root.
REPO_ROOT  = HERE.parent.parent
CSS_FILE   = HERE / 'book.css'
THEME_FILE = HERE / 'highlight.theme'

# Set in main() from --version / --date CLI args (or env vars).
# Used to stamp the cover and title page so each rendered PDF
# self-identifies. Defaults are visible placeholders so a forgotten
# stamp is obvious in the output.
VERSION    = 'dev'
DATE_HUMAN = 'unknown date'   # e.g. "April 2026" — display form

def _meta_html(label: str) -> str:
    """Render the cover/title metadata strip with the active VERSION
    and DATE_HUMAN. Used everywhere the original script had the
    hard-coded `'… v1 · April 2026'` literal."""
    return (f'{label}&nbsp;&middot;&nbsp;{VERSION}'
            f'&nbsp;&middot;&nbsp;{DATE_HUMAN}')

def _colophon_html(audience: str) -> str:
    return (
        '<div class="label">Version</div>'
        f'<div class="value">{VERSION}</div>'
        '<div class="label">Released</div>'
        f'<div class="value">{DATE_HUMAN}</div>'
        '<div class="label">Audience</div>'
        f'<div class="value">{audience}</div>'
    )

# ==================================================================
# Mermaid preprocessing + Kroki SVG rendering
# ==================================================================

MERMAID_RE = re.compile(r'```mermaid\s*\n(.*?)\n```', re.DOTALL)

# Init directive prepended to every diagram. Disables htmlLabels on
# flowcharts (WeasyPrint can't render foreignObject HTML inside SVG)
# and pins the book palette.
MERMAID_INIT = (
    '%%{init: {'
    '"theme":"base",'
    '"themeVariables": {'
    '"primaryColor":"#edf1f7",'
    '"primaryTextColor":"#1a1d21",'
    '"primaryBorderColor":"#1a4380",'
    '"lineColor":"#4a5663",'
    '"secondaryColor":"#f4f6f8",'
    '"tertiaryColor":"#ffffff",'
    '"fontFamily":"Inter, Helvetica, sans-serif",'
    '"fontSize":"14px",'
    '"noteBkgColor":"#fff8e6",'
    '"noteBorderColor":"#d4b84a",'
    '"actorBkg":"#edf1f7",'
    '"actorBorder":"#1a4380",'
    '"actorTextColor":"#1a1d21",'
    '"signalColor":"#1a1d21",'
    '"signalTextColor":"#1a1d21",'
    '"labelBoxBkgColor":"#edf1f7",'
    '"labelBoxBorderColor":"#1a4380"'
    '},'
    '"flowchart": {"htmlLabels": false, "useMaxWidth": true},'
    '"sequence": {"useMaxWidth": true, "mirrorActors": false, "wrap": true}'
    '}}%%\n'
)

def fix_mermaid_source(src: str) -> str:
    """Patch characters Mermaid's parser rejects:
      - apostrophes in `participant X as Y's Z` labels;
      - semicolons inside Notes and message text (statement separator);
      - three-or-more comma-separated participants in Note-over
        (Mermaid only accepts two, as a range)."""
    fixed = []
    for line in src.split('\n'):
        m = re.match(r'^(\s*participant\s+\S+\s+as\s+)(.*)$', line)
        if m:
            prefix, label = m.groups()
            fixed.append(prefix + label.replace("'", "").replace(';', ','))
            continue
        # `Note over A,B,C:` → `Note over A,C:`
        note_over = re.match(
            r'^(\s*Note\s+over\s+)([^:]+):(.*)$', line, re.IGNORECASE)
        if note_over:
            prefix, parts, rest = note_over.groups()
            plist = [p.strip() for p in parts.split(',')]
            if len(plist) >= 2:
                plist = [plist[0], plist[-1]]
            fixed.append(f'{prefix}{",".join(plist)}:{rest.replace(";", ",")}')
            continue
        if re.match(r'^\s*(Note|loop|alt|par|rect|critical|break)\b', line):
            fixed.append(line.replace(';', ','))
            continue
        arrow = re.match(r'^(\s*\S+\s*-{1,2}>>?\s*\S+\s*:\s*)(.*)$', line)
        if arrow:
            fixed.append(arrow.group(1)
                         + arrow.group(2).replace(';', ',').replace("'", ""))
            continue
        fixed.append(line)
    return MERMAID_INIT + '\n'.join(fixed)


def fetch_kroki_svg(source: str, cache_path: Path) -> str:
    """Fetch an SVG from kroki.io for a Mermaid source. Cached on disk."""
    if cache_path.exists():
        return cache_path.read_text()
    req = urllib.request.Request(
        'https://kroki.io/mermaid/svg',
        data=source.encode('utf-8'),
        headers={
            'Content-Type': 'text/plain',
            'User-Agent': 'Mozilla/5.0 (ethrive-pdf-builder)',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            svg = r.read().decode('utf-8')
    except Exception as e:
        print(f'[WARN] Kroki failed: {e}', file=sys.stderr)
        return ''
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(svg)
    return svg

# ==================================================================
# SVG sanitisation: make Kroki's output safe for WeasyPrint
# ==================================================================

EMOJI_REPLACEMENTS = {
    '🚀': 'rocket', '✅': 'check', '🔒': 'lock', '📦': 'box',
    '🔑': 'key', '⚙': 'gear', '⚙️': 'gear', '✓': 'ok', '🐈': 'cat',
}

NODE_FILL    = '#edf1f7'
NODE_STROKE  = '#1a4380'
EDGE_STROKE  = '#1f2937'
TEXT_FILL    = '#1a1d21'
LIFELINE     = '#b3bac4'
ARROW_FILL   = '#1f2937'
NOTE_FILL    = '#fff8e6'
NOTE_STROKE  = '#d4b84a'

def _inject_attrs(tag: str, new: dict, force: tuple = ()) -> str:
    out = tag
    for k, v in new.items():
        existing = re.search(rf'\b{re.escape(k)}="([^"]*)"', out)
        if existing:
            if k in force:
                out = out[:existing.start()] + f'{k}="{v}"' + out[existing.end():]
        else:
            out = out[:-1] + f' {k}="{v}">'
    return out


def sanitize_svg(svg: str) -> str:
    """See module docstring for what this does."""
    svg = re.sub(r'<style\b[^>]*>.*?</style>', '', svg,
                 flags=re.DOTALL | re.IGNORECASE)
    svg = re.sub(r'<\?xml[^>]*\?>\s*', '', svg)
    svg = re.sub(r'<!DOCTYPE[^>]*>\s*', '', svg, flags=re.IGNORECASE)

    for em, repl in EMOJI_REPLACEMENTS.items():
        svg = svg.replace(em, repl)

    def safe_char(ch):
        cp = ord(ch)
        if cp >= 0x10000: return ''
        if 0x2600 <= cp <= 0x27BF: return ''
        return ch
    svg = ''.join(safe_char(c) for c in svg)

    def style_element(m):
        tag = m.group(0)
        cls = (re.search(r'class="([^"]*)"', tag) or re.match('', '')).group(1) \
            if re.search(r'class="([^"]*)"', tag) else ''
        el = re.match(r'<(\w+)', tag).group(1)
        if el == 'rect' and ('label-container' in cls or 'actor' in cls):
            return _inject_attrs(tag,
                {'fill': NODE_FILL, 'stroke': NODE_STROKE, 'stroke-width': '1'},
                force=('fill', 'stroke', 'stroke-width'))
        if el == 'rect' and cls == 'background':
            return _inject_attrs(tag, {'fill': 'none', 'stroke': 'none'},
                                 force=('fill', 'stroke'))
        if el == 'rect' and 'note' in cls:
            return _inject_attrs(tag,
                {'fill': NOTE_FILL, 'stroke': NOTE_STROKE, 'stroke-width': '1'})
        if el == 'path' and 'flowchart-link' in cls:
            return _inject_attrs(tag,
                {'stroke': EDGE_STROKE, 'stroke-width': '1.5', 'fill': 'none'},
                force=('stroke', 'stroke-width'))
        if el in ('path', 'line') and cls.startswith('messageLine0'):
            return _inject_attrs(tag,
                {'stroke': EDGE_STROKE, 'stroke-width': '1.5', 'fill': 'none'},
                force=('stroke', 'stroke-width'))
        if el in ('path', 'line') and cls.startswith('messageLine1'):
            return _inject_attrs(tag,
                {'stroke': EDGE_STROKE, 'stroke-width': '1.5',
                 'stroke-dasharray': '4,2', 'fill': 'none'},
                force=('stroke', 'stroke-width'))
        if el == 'line' and 'actor-line' in cls:
            return _inject_attrs(tag,
                {'stroke': LIFELINE, 'stroke-width': '0.6'},
                force=('stroke', 'stroke-width'))
        if el == 'path' and 'arrowMarkerPath' in cls:
            return _inject_attrs(tag, {'fill': ARROW_FILL, 'stroke': ARROW_FILL})
        if el == 'rect' and cls == '':
            return _inject_attrs(tag, {'fill': 'white', 'stroke': 'none'})
        return tag

    svg = re.sub(r'<(rect|path|line|polygon|circle|ellipse)\b[^>]*>',
                 style_element, svg)

    def fix_text(m):
        tag = m.group(0)
        if 'xml:space' not in tag:
            tag = tag[:-1] + ' xml:space="preserve">'
        if 'fill="' not in tag:
            tag = tag[:-1] + f' fill="{TEXT_FILL}">'
        return tag
    svg = re.sub(r'<text\b[^>]*>', fix_text, svg)

    def fix_tspan(m):
        tag = m.group(0)
        if 'xml:space' not in tag:
            tag = tag[:-1] + ' xml:space="preserve">'
        return tag
    svg = re.sub(r'<tspan\b[^>]*>', fix_tspan, svg)

    # Explicit width/height on the root <svg> from the viewBox.
    vb = re.search(r'viewBox="([^"]+)"', svg)
    if vb:
        parts = vb.group(1).split()
        if len(parts) == 4:
            try:
                vbw = float(parts[2]); vbh = float(parts[3])
                def fix_root(m):
                    attrs = m.group(1)
                    attrs = re.sub(r'\s*(width|height)="[^"]*"', '', attrs)
                    attrs = re.sub(r'\s*style="[^"]*"', '', attrs)
                    return f'<svg{attrs} width="{vbw:.0f}" height="{vbh:.0f}">'
                svg = re.sub(r'<svg([^>]*)>', fix_root, svg, count=1)
            except ValueError:
                pass

    # <foreignObject>HTML → <text>/<tspan>
    def foreign_to_text(m):
        open_tag = m.group(0).split('>', 1)[0] + '>'
        wm = re.search(r'width="([\d.]+)"', open_tag)
        hm = re.search(r'height="([\d.]+)"', open_tag)
        w = float(wm.group(1)) if wm else 100
        h = float(hm.group(1)) if hm else 20
        inner = m.group(1)
        raw_lines = re.split(r'<br\s*/?>|</p>|</div>', inner, flags=re.IGNORECASE)
        lines = []
        for ln in raw_lines:
            flat = re.sub(r'<[^>]+>', '', ln).replace('&nbsp;', ' ').strip()
            if flat:
                bold = bool(re.search(r'<(b|strong)\b', ln, re.IGNORECASE))
                lines.append((flat, bold))
        if not lines:
            return ''
        line_h = 14
        total = len(lines) * line_h
        start_y = (h - total) / 2 + line_h * 0.8
        spans = []
        for i, (txt, bold) in enumerate(lines):
            y = start_y + i * line_h
            weight = ' font-weight="600"' if bold else ''
            decoded = html_lib.unescape(txt)
            safe = (decoded.replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;'))
            spans.append(
                f'<tspan x="{w/2:.1f}" y="{y:.1f}" text-anchor="middle"'
                f'{weight} xml:space="preserve">{safe}</tspan>'
            )
        return (
            f'<text font-family="Inter, sans-serif" font-size="11"'
            f' fill="{TEXT_FILL}" xml:space="preserve">'
            + ''.join(spans) + '</text>'
        )
    svg = re.sub(r'<foreignObject\b[^>]*>(.*?)</foreignObject>',
                 foreign_to_text, svg, flags=re.DOTALL)

    # Default font on the root
    svg = re.sub(r'<svg([^>]*)>',
                 r'<svg\1 font-family="Inter, sans-serif" font-size="13">',
                 svg, count=1)
    return svg


# ==================================================================
# Code-block tagging (pandoc / Skylighting)
# ==================================================================

DART_HINTS = re.compile(
    r'\b(abstract|async|await|class|const|enum|extends|final|for|Future|'
    r'import|mixin|package:|print\(|return|sealed|static|Stream|String|'
    r'Uint8List|void|@override|if\s*\()'
)

def tag_code_blocks(md: str) -> str:
    """Untyped triple-backtick blocks get language tags inferred from
    content, so Pandoc's Skylighting renders them with highlighting."""
    def replace(match):
        lang = match.group(1); body = match.group(2)
        if lang.strip():
            return match.group(0)
        if body.lstrip().startswith(('{', '[')):
            return f'```json\n{body}```'
        if DART_HINTS.search(body):
            return f'```dart\n{body}```'
        return match.group(0)
    return re.sub(r'```([^\n`]*)\n(.*?)```', replace, md, flags=re.DOTALL)


# ==================================================================
# Pandoc call
# ==================================================================

def run_pandoc(processed_md: Path) -> str:
    result = subprocess.run(
        ['pandoc', str(processed_md),
         '--from', 'markdown+fenced_code_blocks+fenced_code_attributes'
                  '+auto_identifiers+pipe_tables+raw_html-smart-yaml_metadata_block',
         '--to', 'html5',
         '--highlight-style', str(THEME_FILE)],
        check=True, capture_output=True, text=True)
    return result.stdout


# ==================================================================
# Doc-specific post-processing
# ==================================================================

@dataclass
class OpenerRule:
    """One regex → HTML replacer for identifying chapter/part openers.

    `pattern` matches an <hN ...>…</hN> and its groups will be passed
    to `formatter` which returns the replacement HTML.
    """
    pattern: str
    formatter: Callable[[re.Match], str]


@dataclass
class BuildConfig:
    source_md: Path
    out_pdf: Path
    out_html: Path
    svg_cache_dir: Path
    cover_mark: str
    cover_title_html: str
    cover_subtitle: str
    cover_tagline: str
    cover_meta_html: str
    title_main: str
    title_sub: str
    title_tagline: str
    title_colophon_html: str
    doc_title: str
    hide_h1_regex: Optional[str] = None
    openers: List[OpenerRule] = field(default_factory=list)
    include_index: bool = False
    index_terms: List[str] = field(default_factory=list)


def post_process_body(body: str, config: BuildConfig) -> Tuple[str, str]:
    """Apply opener substitutions, build TOC, and optionally build an
    alphabetical Index. Returns (body_html, toc_html + index_html)."""
    # Strip pandoc boilerplate
    body = re.sub(r'^<!DOCTYPE[^>]*>\s*', '', body)
    body = re.sub(r'</?html[^>]*>', '', body)
    body = re.sub(r'</?head[^>]*>.*?</head>', '', body, flags=re.DOTALL)
    body = re.sub(r'</?body[^>]*>', '', body)
    # Pandoc header-anchor <a> tags embedded in headings
    body = re.sub(
        r'<(h[1-6])([^>]*)>\s*<a[^>]+class="header-anchor"[^>]*></a>',
        r'<\1\2>', body)

    # Hide the top-level <h1> (cover/title page carry the doc title)
    if config.hide_h1_regex:
        body = re.sub(config.hide_h1_regex, '', body,
                      flags=re.DOTALL | re.IGNORECASE)

    # Apply opener substitutions
    for rule in config.openers:
        body = re.sub(rule.pattern, rule.formatter, body,
                      flags=re.DOTALL | re.IGNORECASE)

    # Build TOC from the resulting structure
    toc_items = []
    for m in re.finditer(
            r'<section class="part-opener"([^>]*)>.*?'
            r'<div class="eyebrow">([^<]+)</div>'
            r'.*?<div class="title">([^<]+)</div>'
            r'|<h2 id="([^"]+)"[^>]*>(.*?)</h2>',
            body, flags=re.DOTALL):
        if m.group(2):
            id_match = re.search(r'id="([^"]+)"', m.group(1))
            toc_items.append({
                'type': 'opener',
                'id': id_match.group(1) if id_match else '',
                'eyebrow': m.group(2).strip(),
                'title': m.group(3).strip(),
            })
        else:
            raw = m.group(5)
            plain = re.sub(r'<[^>]+>', '', raw).strip()
            toc_items.append({
                'type': 'section',
                'id': m.group(4), 'title': plain,
            })

    toc_html = ['<nav id="TOC"><ul>']
    current_part_open = False
    for item in toc_items:
        if item['type'] == 'opener':
            if current_part_open:
                toc_html.append('</ul></li>')
            toc_html.append(
                f'<li class="toc-part"><a href="#{item["id"]}">'
                f'<span class="toc-label">{item["eyebrow"]}</span>'
                f'<span class="toc-title">{item["title"]}</span>'
                f'<span class="toc-dots"></span>'
                f'</a><ul>'
            )
            current_part_open = True
        else:
            toc_html.append(
                f'<li class="toc-section"><a href="#{item["id"]}">'
                f'<span class="toc-title">{item["title"]}</span>'
                f'<span class="toc-dots"></span>'
                f'</a></li>'
            )
    if current_part_open:
        toc_html.append('</ul></li>')
    toc_html.append('</ul></nav>')

    if len(toc_items) <= 1:
        # A single-entry TOC adds noise without giving the reader a way
        # to navigate. Skip the front-matter Contents page entirely.
        toc_block = ''
    else:
        toc_block = (
            '<section class="front-matter">'
            '<h2 class="front-title">Contents</h2>'
            + ''.join(toc_html) +
            '</section>'
        )

    # Optional alphabetical Index
    index_block = ''
    if config.include_index and config.index_terms:
        used = {}
        for idx, term in enumerate(config.index_terms):
            anchor = f'idx-{idx:03d}'
            new_body = _wrap_first(body, term, anchor)
            if new_body != body:
                used[term] = anchor
                body = new_body
        grouped = defaultdict(list)
        for t, a in sorted(used.items(), key=lambda x: x[0].lower()):
            first = t[0].upper() if t[:1].isalpha() else '#'
            grouped[first].append((t, a))
        lines = ['<section class="index-section">',
                 '<h2 class="front-title">Index</h2>',
                 '<div class="index-columns">']
        for letter in sorted(grouped):
            lines.append(f'<div class="index-letter">{letter}</div>')
            for t, a in grouped[letter]:
                lines.append(
                    f'<p class="index-entry">'
                    f'<a href="#{a}"><span class="term">{t}</span></a>'
                    f'</p>')
        lines += ['</div></section>']
        index_block = '\n'.join(lines)

    return body, toc_block, index_block


def _wrap_first(haystack: str, term: str, tag_id: str) -> str:
    """Wrap the first outside-of-tags occurrence of `term` with an
    empty <a id="tag_id"/> anchor so the Index can target it."""
    skip = []
    for m in re.finditer(
            r'<(pre|code|script|style|a|svg)[\s>].*?</\1>',
            haystack, flags=re.DOTALL | re.IGNORECASE):
        skip.append((m.start(), m.end()))

    def in_skip(i):
        return any(s <= i < e for s, e in skip)

    pattern = re.compile(rf'(?<![\w-])({re.escape(term)})(?![\w-])',
                         flags=re.IGNORECASE)
    match = pattern.search(haystack)
    while match:
        if not in_skip(match.start()):
            s, e = match.span()
            return (haystack[:s]
                    + f'<a id="{tag_id}" class="index-anchor"></a>'
                    + haystack[s:e]
                    + haystack[e:])
        match = pattern.search(haystack, match.end())
    return haystack


# ==================================================================
# Final HTML assembly and PDF rendering
# ==================================================================

FULL_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{doc_title}</title>
<link rel="stylesheet" href="{css_uri}">
</head>
<body>

<section class="cover">
  <div class="cover-top">
    <div class="cover-mark">{cover_mark}</div>
    <div class="cover-rule"></div>
  </div>
  <div class="cover-middle">
    <h1 class="cover-title">{cover_title_html}</h1>
    <p class="cover-subtitle">{cover_subtitle}</p>
  </div>
  <div class="cover-bottom">
    <p class="cover-tagline">{cover_tagline}</p>
    <div class="cover-meta">{cover_meta_html}</div>
  </div>
</section>

<section class="title-page">
  <div class="title-top"></div>
  <h1 class="title-main">{title_main}</h1>
  <p class="title-sub">{title_sub}</p>
  <div class="title-ornament">§</div>
  <p class="title-tagline">{title_tagline}</p>
  <div class="title-colophon">{title_colophon_html}</div>
</section>

{toc_block}

<main class="book-body">
{body_html}
</main>

{index_block}

</body>
</html>
"""


def build_pdf(config: BuildConfig) -> Path:
    # 1. Render mermaid blocks to SVG and substitute them into MD
    md = config.source_md.read_text()
    config.svg_cache_dir.mkdir(parents=True, exist_ok=True)

    blocks = MERMAID_RE.findall(md)
    print(f'[{config.source_md.name}] rendering {len(blocks)} mermaid diagrams…')
    for i, src in enumerate(blocks):
        fetch_kroki_svg(
            fix_mermaid_source(src),
            config.svg_cache_dir / f'{i:03d}.svg')

    def mermaid_replace(match, counter=[0]):
        i = counter[0]
        counter[0] += 1
        path = config.svg_cache_dir / f'{i:03d}.svg'
        if not path.exists() or path.stat().st_size == 0:
            return f'```text\n{match.group(1)}\n```'
        return f'<div class="mermaid">{sanitize_svg(path.read_text())}</div>'

    # Reset counter between calls (important when build_pdf runs twice)
    mermaid_replace.__defaults__ = (match_counter_reset := [0],)
    md_processed = MERMAID_RE.sub(mermaid_replace, md)
    md_processed = tag_code_blocks(md_processed)

    tmp_md = config.svg_cache_dir.parent / f'_{config.source_md.stem}-processed.md'
    tmp_md.write_text(md_processed)

    # 2. Pandoc → HTML
    print(f'[{config.source_md.name}] running pandoc…')
    body_html = run_pandoc(tmp_md)

    # 3. Post-processing (openers, TOC, optional Index)
    body_html, toc_block, index_block = post_process_body(body_html, config)

    # 4. Compose final HTML
    document = FULL_HTML_TEMPLATE.format(
        doc_title=config.doc_title,
        css_uri=CSS_FILE.as_uri(),
        cover_mark=config.cover_mark,
        cover_title_html=config.cover_title_html,
        cover_subtitle=config.cover_subtitle,
        cover_tagline=config.cover_tagline,
        cover_meta_html=config.cover_meta_html,
        title_main=config.title_main,
        title_sub=config.title_sub,
        title_tagline=config.title_tagline,
        title_colophon_html=config.title_colophon_html,
        toc_block=toc_block,
        body_html=body_html,
        index_block=index_block,
    )
    config.out_html.parent.mkdir(parents=True, exist_ok=True)
    config.out_html.write_text(document)

    # 5. WeasyPrint → PDF
    print(f'[{config.source_md.name}] rendering PDF via WeasyPrint…')
    from weasyprint import HTML  # imported lazily — heavy
    HTML(filename=str(config.out_html)).write_pdf(str(config.out_pdf))
    print(f'[{config.source_md.name}] → {config.out_pdf} '
          f'({config.out_pdf.stat().st_size:,} bytes)')
    return config.out_pdf


# ==================================================================
# Per-document configs
# ==================================================================


def non_technical_whitepaper_config(out_dir: Path) -> BuildConfig:
    """The non-technical whitepaper: same conceptual ground as the
    technical whitepaper, written for an audience that does not want
    (and should not have to learn) protocol jargon."""
    return BuildConfig(
        source_md=REPO_ROOT / 'NON_TECHNICAL.md',
        out_pdf=out_dir / f'ethrive-whitepaper-{VERSION}-non-technical.pdf',
        out_html=out_dir / '.build' / 'NON_TECHNICAL.html',
        svg_cache_dir=out_dir / '.build' / 'whitepaper-non-technical-svgs',
        cover_mark='ethrive',
        cover_title_html='Whitepaper',
        cover_subtitle='Your data, on your devices and the devices of '
                       'people you trust.',
        cover_tagline='No central server in the middle.',
        cover_meta_html=_meta_html('Plain-Language Edition'),
        title_main='ethrive',
        title_sub='Whitepaper · Plain-Language Edition',
        title_tagline='ethrive is a way to build apps without a '
                      'company in the middle. Your photos, messages, '
                      'and notes live on your devices and the devices '
                      'of the people you share them with — never on '
                      'someone else’s server. The apps you use '
                      'become lenses on top of that data, not vaults '
                      'that hold it. This is the plain-language '
                      'introduction: what ethrive is, what it changes, '
                      'and why it matters — without the protocol '
                      'jargon. Twenty minutes, cover to cover. For '
                      'journalists, business readers, families, and '
                      'anyone who uses cloud software without '
                      'thinking about who owns their data.',
        title_colophon_html=_colophon_html('Everyone'),
        doc_title='ethrive Whitepaper · Plain-Language Edition',
        hide_h1_regex=(
            r'<header[^>]*id="title-block-header".*?</header>'
            r'|<h1[^>]*>\s*ethrive\s*</h1>'
        ),
        openers=[],
        include_index=False,
        index_terms=[],
    )


def whitepaper_config(out_dir: Path) -> BuildConfig:
    """Technical whitepaper. Source: TECHNICAL.md at repo root."""
    return BuildConfig(
        source_md=REPO_ROOT / 'TECHNICAL.md',
        out_pdf=out_dir / f'ethrive-whitepaper-{VERSION}.pdf',
        out_html=out_dir / '.build' / 'TECHNICAL.html',
        svg_cache_dir=out_dir / '.build' / 'whitepaper-svgs',
        cover_mark='ethrive',
        cover_title_html='Whitepaper',
        cover_subtitle='A peer-to-peer protocol where every '
                       'participant owns a signed, append-only log.',
        cover_tagline='No servers. No central authority.',
        cover_meta_html=_meta_html('Whitepaper'),
        title_main='ethrive',
        title_sub='Whitepaper',
        title_tagline='ethrive is a peer-to-peer protocol. Every '
                      'participant — a person, a device, a group, a '
                      'program — is identified by a public key and '
                      'owns a signed, append-only log of operations '
                      'called a *space*. Spaces replicate between '
                      'members and converge eventually. There are no '
                      'servers and no central authority; any peer '
                      'with the relevant membership can read, and '
                      'any peer with the relevant signing authority '
                      'can author. This whitepaper is a conceptual '
                      'introduction for a technical audience: what '
                      'ethrive makes possible, how sovereign spaces '
                      'and threshold signing combine into a '
                      'substrate for the next generation of '
                      'decentralized applications, and the single '
                      'extension point that holds it all together.',
        title_colophon_html=_colophon_html(
            'Technical readers · Researchers · Partners · Sophisticated end users'
        ),
        doc_title='ethrive Whitepaper',
        hide_h1_regex=(
            r'<header[^>]*id="title-block-header".*?</header>'
            r'|<h1[^>]*>\s*ethrive\s*</h1>'
        ),
        openers=[],
        include_index=False,
        index_terms=[],
    )


def main():
    parser = argparse.ArgumentParser(
        description='Build the ethrive whitepaper PDFs (TECHNICAL + '
                    'NON_TECHNICAL).',
        epilog='Example: ./create_pdfs.py ~/Desktop --version v0.1.0 --date 2026-04-26')
    parser.add_argument('output_dir', nargs='?', default='/tmp',
        help='Directory to write PDFs to (default: /tmp)')
    parser.add_argument('--only', default=None, choices=[None, 'TECHNICAL', 'NON_TECHNICAL'],
        help='Build only the named whitepaper.')
    parser.add_argument('--parallel', type=int, default=2,
        help='Number of PDFs to build concurrently (default: 2; 1 = serial).')
    parser.add_argument('--version', default=None,
        help='Version string stamped on each PDF cover '
             '(default: env PDF_VERSION, then "dev").')
    parser.add_argument('--date', default=None,
        help='Release date stamped on each PDF cover '
             '(default: env PDF_DATE, then today as "April 2026"-style).')
    args = parser.parse_args()

    # Apply version + date globals (used by _meta_html and _colophon_html
    # in the per-doc configs).
    import datetime, os
    global VERSION, DATE_HUMAN
    VERSION = args.version or os.environ.get('PDF_VERSION') or 'dev'
    if args.date or os.environ.get('PDF_DATE'):
        DATE_HUMAN = args.date or os.environ['PDF_DATE']
    else:
        DATE_HUMAN = datetime.date.today().strftime('%B %Y')

    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Sanity checks on external dependencies
    for binary in ('pandoc',):
        from shutil import which
        if which(binary) is None:
            print(f'Error: {binary} is required and was not found on PATH.',
                  file=sys.stderr)
            sys.exit(1)

    # Sanity checks on local assets
    for f in (CSS_FILE, THEME_FILE):
        if not f.exists():
            print(f'Error: expected asset missing: {f}', file=sys.stderr)
            sys.exit(1)

    configs: List[BuildConfig] = []
    want = args.only

    if want is None or want == 'TECHNICAL':
        source = REPO_ROOT / 'TECHNICAL.md'
        if source.exists():
            configs.append(whitepaper_config(out))
        else:
            print(f'[skip] {source.name} not found', file=sys.stderr)

    if want is None or want == 'NON_TECHNICAL':
        source = REPO_ROOT / 'NON_TECHNICAL.md'
        if source.exists():
            configs.append(non_technical_whitepaper_config(out))
        else:
            print(f'[skip] {source.name} not found', file=sys.stderr)

    if not configs:
        print(f'No matching whitepaper for --only={args.only}', file=sys.stderr)
        sys.exit(1)

    print(f'Stamping PDFs with version={VERSION!r}, date={DATE_HUMAN!r}')

    workers = max(1, min(args.parallel, len(configs)))
    if workers == 1:
        built = [build_pdf(c) for c in configs]
    else:
        print(f'Building {len(configs)} PDFs across {workers} workers…')
        built = []
        with ProcessPoolExecutor(max_workers=workers) as pool:
            future_to_name = {
                pool.submit(build_pdf, c): c.source_md.name for c in configs
            }
            for fut in as_completed(future_to_name):
                name = future_to_name[fut]
                try:
                    built.append(fut.result())
                except Exception as e:
                    print(f'[ERROR] {name}: {e}', file=sys.stderr)
                    raise

    print()
    for pdf in sorted(built):
        print(f'✓ {pdf}')


if __name__ == '__main__':
    main()
