"""Export dokumen GuruWali ke Word (.docx) dan PDF.

Konten AI berbentuk markdown-ish (##, ###, -, 1., **bold**, ---).
Fungsi utama:
    to_docx(title, content) -> bytes
    to_pdf(title, content) -> bytes
Dependensi: python-docx, reportlab  (pip install python-docx reportlab)
"""
import io
import re


def _parse_blocks(content):
    """Pecah konten jadi blok: ('h1', teks), ('h2', teks), ('bullet', teks),
    ('number', teks), ('para', teks), ('hr', None). Inline **bold** diproses
    terpisah oleh masing-masing renderer."""
    blocks = []
    for raw in (content or "").splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        if re.match(r"^-{3,}$", s):
            blocks.append(("hr", None))
            continue
        m = re.match(r"^##\s+(.*)", s)
        if m:
            blocks.append(("h1", m.group(1).strip()))
            continue
        m = re.match(r"^###\s+(.*)", s)
        if m:
            blocks.append(("h2", m.group(1).strip()))
            continue
        m = re.match(r"^#{4,6}\s+(.*)", s)
        if m:
            blocks.append(("h2", m.group(1).strip()))
            continue
        m = re.match(r"^[-*]\s+(.*)", s)
        if m:
            blocks.append(("bullet", m.group(1).strip()))
            continue
        m = re.match(r"^\d+[.)]\s+(.*)", s)
        if m:
            blocks.append(("number", m.group(1).strip()))
            continue
        blocks.append(("para", s))
    return blocks


def _rich_parts(text):
    """Pecah teks jadi [(teks, bold), ...] berdasarkan **bold**."""
    parts = []
    for i, seg in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if seg:
            parts.append((seg, i % 2 == 1))
    return parts or [(text, False)]


# ---------------- DOCX ----------------

def _extract_ttd(content):
    """Ekstrak blok [[TTD]]...[[/TTD]] jadi (kiri_lines, kanan_lines, sisa_content)."""
    m = re.search(r"\[\[TTD\]\](.*?)\[\[/TTD\]\]", content or "", re.DOTALL)
    if not m:
        return None, content
    inner = m.group(1).strip()
    lines = [l.strip() for l in inner.splitlines() if l.strip()]
    # Format: baris dengan | sebagai pemisah kolom
    kiri, kanan = [], []
    for l in lines:
        if "|" in l:
            k, kn = l.split("|", 1)
            kiri.append(k.strip())
            kanan.append(kn.strip())
        else:
            kiri.append(l)
    sisa = content[:m.start()] + content[m.end():]
    return (kiri, kanan), sisa


def _extract_kop(content):
    """Ekstrak blok [[KOP]]...[[/KOP]] jadi (kop_lines, sisa_content)."""
    import re
    m = re.search(r"\[\[KOP\]\](.*?)\[\[/KOP\]\]", content or "", re.DOTALL)
    if not m:
        return None, content
    inner = m.group(1).strip()
    lines = [l.strip() for l in inner.splitlines() if l.strip()]
    sisa = content[:m.start()] + content[m.end():]
    return lines, sisa


def to_docx(title, content):
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Skip judul otomatis jika ada blok KOP (hindari judul ganda)
    has_kop = "[[KOP]]" in (content or "")
    t = None
    if not has_kop:
        t = doc.add_heading(title or "Dokumen GuruWali", level=0)
    if t: t.alignment = WD_ALIGN_PARAGRAPH.CENTER

    ttd_data, content = _extract_ttd(content)
    kop_data, content = _extract_kop(content)

    # Render kop rata tengah di paling atas (sebelum judul)
    if kop_data:
        for kl in kop_data:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(kl)
            r.bold = True
        # Garis pemisah
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("=" * 50)
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    for kind, text in _parse_blocks(content):
        if kind == "h1":
            doc.add_heading(text, level=1)
        elif kind == "h2":
            doc.add_heading(text, level=2)
        elif kind == "hr":
            p = doc.add_paragraph()
            run = p.add_run("─" * 40)
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        elif kind == "bullet":
            p = doc.add_paragraph(style="List Bullet")
            for seg, bold in _rich_parts(text):
                r = p.add_run(seg)
                r.bold = bold
        elif kind == "number":
            p = doc.add_paragraph(style="List Number")
            for seg, bold in _rich_parts(text):
                r = p.add_run(seg)
                r.bold = bold
        else:  # para
            p = doc.add_paragraph()
            for seg, bold in _rich_parts(text):
                r = p.add_run(seg)
                r.bold = bold

    # Tabel tanda tangan di akhir dokumen
    if ttd_data:
        kiri, kanan = ttd_data
        # Baris tanggal
        if kiri and "," in kiri[0]:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = p.add_run(kiri.pop(0))
        table = doc.add_table(rows=1, cols=2)
        table.autofit = True
        # Hapus border
        for row in table.rows:
            for cell in row.cells:
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Isi sel
        max_rows = max(len(kiri), len(kanan))
        # Baris pertama sudah ada, tambah sisanya
        for _ in range(max_rows - 1):
            table.add_row()
        for i in range(max_rows):
            if i < len(kiri):
                table.rows[i].cells[0].text = kiri[i]
                table.rows[i].cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if i < len(kanan):
                table.rows[i].cells[1].text = kanan[i]
                table.rows[i].cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Hilangkan border tabel
        from docx.oxml.ns import qn
        for row in table.rows:
            for cell in row.cells:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                tcBorders = tcPr.first_child_found_in("w:tcBorders")
                if tcBorders is None:
                    tcBorders = tcPr.makeelement(qn('w:tcBorders'), {})
                    tcPr.append(tcBorders)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------- PDF ----------------

def to_pdf(title, content):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=title or "Dokumen GuruWali",
    )
    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("GWTitle", parent=styles["Title"], fontSize=18,
                             spaceAfter=12, alignment=1)
    s_h1 = ParagraphStyle("GWH1", parent=styles["Heading1"], fontSize=14,
                          spaceBefore=12, spaceAfter=6)
    s_h2 = ParagraphStyle("GWH2", parent=styles["Heading2"], fontSize=12,
                          spaceBefore=10, spaceAfter=4)
    s_body = ParagraphStyle("GWBody", parent=styles["Normal"], fontSize=10.5,
                            leading=15, spaceAfter=6)
    s_bullet = ParagraphStyle("GWBullet", parent=s_body, leftIndent=18,
                              bulletIndent=8, spaceAfter=3)
    s_number = ParagraphStyle("GWNumber", parent=s_body, leftIndent=18,
                              spaceAfter=3)

    def md2html(text):
        """Inline markdown -> HTML sederhana untuk reportlab Paragraph."""
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        return text

    ttd_data, content = _extract_ttd(content)
    story = [Paragraph(md2html(title or "Dokumen GuruWali"), s_title),
             Spacer(1, 6)]
    for kind, text in _parse_blocks(content):
        if kind == "h1":
            story.append(Paragraph(md2html(text), s_h1))
        elif kind == "h2":
            story.append(Paragraph(md2html(text), s_h2))
        elif kind == "hr":
            story.append(HRFlowable(width="100%", thickness=0.5, spaceAfter=6,
                                   spaceBefore=6, color=(0.6, 0.6, 0.6)))
        elif kind == "bullet":
            story.append(Paragraph(md2html(text), s_bullet, bulletText="•"))
        elif kind == "number":
            story.append(Paragraph(md2html(text), s_number))
        else:
            story.append(Paragraph(md2html(text), s_body))
    # Tabel tanda tangan
    if ttd_data:
        from reportlab.platypus import Table, TableStyle
        kiri, kanan = ttd_data
        # Baris tanggal rata kanan
        if kiri and "," in kiri[0]:
            story.append(Paragraph(md2html(kiri.pop(0)), s_body))
        max_rows = max(len(kiri), len(kanan), 1)
        data = []
        for i in range(max_rows):
            k = kiri[i] if i < len(kiri) else ""
            kn = kanan[i] if i < len(kanan) else ""
            data.append([Paragraph(md2html(k), s_body), Paragraph(md2html(kn), s_body)])
        t = Table(data, colWidths=[260, 260])
        t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(t)
    doc.build(story)
    return buf.getvalue()
