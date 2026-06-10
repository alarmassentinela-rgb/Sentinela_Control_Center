#!/usr/bin/env python3
"""Genera los PDF de las guías de GolfBookVIP desde los .md de docs/manual/.

No requiere pandoc/weasyprint: convierte Markdown -> HTML (subset) y lo
renderiza con PyMuPDF Story (fitz), el mismo motor que usamos para CFDI.

Uso:  python3 build_pdf.py
Salida: docs/manual/pdf/<archivo>.pdf  (4 PDFs: jugador/organizador x es/en)
"""
import html
import os
import re
import sys

import fitz  # PyMuPDF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "pdf")

BRAND_GREEN = "#10b981"
BRAND_DARK = "#09090b"

FILES = [
    ("jugador.es.md", "GolfBookVIP-Guia-del-Jugador-ES.pdf", "Guía del Jugador", "es"),
    ("jugador.en.md", "GolfBookVIP-Player-Guide-EN.pdf", "Player Guide", "en"),
    ("organizador.es.md", "GolfBookVIP-Guia-del-Organizador-ES.pdf", "Guía del Organizador", "es"),
    ("organizador.en.md", "GolfBookVIP-Organizer-Guide-EN.pdf", "Organizer Guide", "en"),
]


def inline(text):
    """Convierte spans inline de Markdown a HTML, escapando lo demás."""
    # proteger code spans primero
    codes = []

    def stash_code(m):
        codes.append(m.group(1))
        return f"\x00{len(codes)-1}\x00"

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = html.escape(text)
    # bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # restaurar code
    def restore_code(m):
        return f"<code>{html.escape(codes[int(m.group(1))])}</code>"

    text = re.sub(r"\x00(\d+)\x00", restore_code, text)
    return text


def md_to_html(md):
    """Subset de Markdown -> HTML suficiente para estas guías."""
    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)

    def close_list(stack):
        while stack:
            out.append(f"</{stack.pop()}>")

    list_stack = []  # 'ul' | 'ol'

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # regla horizontal
        if stripped == "---":
            close_list(list_stack)
            out.append('<hr/>')
            i += 1
            continue

        # encabezados
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            close_list(list_stack)
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # tabla
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            close_list(list_stack)
            header = [c.strip() for c in stripped.strip("|").split("|")]
            out.append('<table>')
            out.append("<tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr>")
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</table>")
            continue

        # blockquote (puede ser multilinea)
        if stripped.startswith(">"):
            close_list(list_stack)
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                q = re.sub(r"^\s*>\s?", "", lines[i])
                quote.append(q)
                i += 1
            joined = " ".join(q.strip() for q in quote if q.strip())
            out.append(f'<div class="note">{inline(joined)}</div>')
            continue

        # lista ordenada
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            if not list_stack or list_stack[-1] != "ol":
                close_list(list_stack)
                list_stack.append("ol")
                out.append("<ol>")
            out.append(f"<li>{inline(m.group(2))}</li>")
            i += 1
            continue

        # lista no ordenada
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if not list_stack or list_stack[-1] != "ul":
                close_list(list_stack)
                list_stack.append("ul")
                out.append("<ul>")
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        # linea vacia
        if not stripped:
            close_list(list_stack)
            i += 1
            continue

        # parrafo
        close_list(list_stack)
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_list(list_stack)
    return "\n".join(out)


CSS = f"""
* {{ font-family: sans-serif; }}
body {{ color: #1c1917; font-size: 10.5px; line-height: 1.5; }}
h1 {{ color: {BRAND_DARK}; font-size: 19px; margin: 14px 0 6px 0; }}
h2 {{ color: {BRAND_GREEN}; font-size: 14px; margin: 16px 0 4px 0;
      border-bottom: 2px solid {BRAND_GREEN}; padding-bottom: 2px; }}
h3 {{ color: {BRAND_DARK}; font-size: 12px; margin: 10px 0 3px 0; }}
h4 {{ color: #44403c; font-size: 11px; margin: 8px 0 2px 0; }}
p {{ margin: 4px 0; }}
ul, ol {{ margin: 4px 0 4px 0; padding-left: 18px; }}
li {{ margin: 2px 0; }}
code {{ background: #f4f4f5; color: {BRAND_DARK}; font-family: monospace;
        font-size: 9.5px; padding: 1px 3px; border-radius: 3px; }}
hr {{ border: none; border-top: 1px solid #e7e5e4; margin: 8px 0; }}
.note {{ background: #ecfdf5; border-left: 3px solid {BRAND_GREEN};
         padding: 6px 10px; margin: 6px 0; color: #065f46; font-size: 10px; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.5px; }}
th {{ background: {BRAND_GREEN}; color: white; text-align: left;
      padding: 5px 7px; }}
td {{ border-bottom: 1px solid #e7e5e4; padding: 5px 7px; vertical-align: top; }}
b {{ color: {BRAND_DARK}; }}
"""

PAGE = fitz.paper_rect("a4")
MARGIN = 50
HEADER_H = 30
FOOTER_H = 28
CONTENT = fitz.Rect(MARGIN, MARGIN + HEADER_H, PAGE.width - MARGIN, PAGE.height - MARGIN - FOOTER_H)

LOGO = os.path.join(HERE, "..", "..", "frontend", "public", "icons", "icon-512.png")


def draw_chrome(page, subtitle, page_no):
    """Encabezado y pie de página de marca en cada hoja."""
    # encabezado
    hdr = fitz.Rect(MARGIN, MARGIN, PAGE.width - MARGIN, MARGIN + HEADER_H - 6)
    logo_w = 18
    if os.path.exists(LOGO):
        page.insert_image(fitz.Rect(hdr.x0, hdr.y0, hdr.x0 + logo_w, hdr.y0 + logo_w), filename=LOGO)
    page.insert_text((hdr.x0 + logo_w + 8, hdr.y0 + 13), "GolfBookVIP",
                     fontsize=12, fontname="hebo", color=fitz.utils.getColor("black"))
    page.insert_text((hdr.x1 - fitz.get_text_length(subtitle, "helv", 9), hdr.y0 + 12),
                     subtitle, fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
    page.draw_line((MARGIN, MARGIN + HEADER_H - 4), (PAGE.width - MARGIN, MARGIN + HEADER_H - 4),
                   color=(0.063, 0.725, 0.506), width=1.2)
    # pie
    fy = PAGE.height - MARGIN - 6
    page.draw_line((MARGIN, fy - 8), (PAGE.width - MARGIN, fy - 8), color=(0.9, 0.9, 0.9), width=0.6)
    page.insert_text((MARGIN, fy), "golfbookvip.com", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
    foot_r = f"Página {page_no}"
    page.insert_text((PAGE.width - MARGIN - fitz.get_text_length(foot_r, "helv", 8), fy),
                     foot_r, fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))


def cover(doc, title, subtitle, lang):
    page = doc.new_page(width=PAGE.width, height=PAGE.height)
    page.draw_rect(PAGE, color=None, fill=(0.035, 0.035, 0.043))  # dark
    cx = PAGE.width / 2
    if os.path.exists(LOGO):
        s = 110
        page.insert_image(fitz.Rect(cx - s / 2, 200, cx + s / 2, 200 + s), filename=LOGO)
    def center(txt, y, size, font, col):
        w = fitz.get_text_length(txt, font, size)
        page.insert_text((cx - w / 2, y), txt, fontsize=size, fontname=font, color=col)
    center("GolfBookVIP", 360, 30, "hebo", (1, 1, 1))
    center(title, 400, 18, "helv", (0.063, 0.725, 0.506))
    tagline = "Tu compañero de golf digital" if lang == "es" else "Your digital golf companion"
    center(tagline, 430, 11, "helv", (0.7, 0.7, 0.7))
    center("golfbookvip.com", PAGE.height - 80, 10, "helv", (0.5, 0.5, 0.5))


def build(md_path, out_path, subtitle, lang):
    with open(md_path, encoding="utf-8") as f:
        md = f.read()
    body = md_to_html(md)
    doc_html = f"<html><head><style>{CSS}</style></head><body>{body}</body></html>"

    writer = fitz.DocumentWriter(out_path)
    story = fitz.Story(html=doc_html)
    page_no = 0
    more = True
    pages = []
    # Primero render del contenido para contar/colocar
    while more:
        page_no += 1
        dev = writer.begin_page(PAGE)
        more, _ = story.place(CONTENT)
        story.draw(dev)
        writer.end_page()
        pages.append(page_no)
    writer.close()

    # Reabrir para portada + chrome (header/footer) con números reales
    content_doc = fitz.open(out_path)
    final = fitz.open()
    cover(final, subtitle, subtitle, lang)
    for idx in range(content_doc.page_count):
        final.insert_pdf(content_doc, from_page=idx, to_page=idx)
    # dibujar chrome sobre cada página de contenido (saltando portada=0)
    for idx in range(1, final.page_count):
        draw_chrome(final[idx], subtitle, idx)
    final.save(out_path, deflate=True)
    final.close()
    content_doc.close()
    return len(pages)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, out, subtitle, lang in FILES:
        src = os.path.join(HERE, fname)
        if not os.path.exists(src):
            print(f"  ⚠ falta {fname}, salto")
            continue
        out_path = os.path.join(OUT_DIR, out)
        n = build(src, out_path, subtitle, lang)
        size = os.path.getsize(out_path) // 1024
        print(f"  ✓ {out}  ({n} págs contenido + portada, {size} KB)")


if __name__ == "__main__":
    main()
