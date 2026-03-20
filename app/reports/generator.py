"""
MONTANIA — Gerador de Relatório PDF
Relatório gerencial de performance para gestores
"""
import io
import base64
from datetime import datetime, timedelta
import pytz

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import (
    HexColor, white, black, Color
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

TZ_BR = pytz.timezone('America/Sao_Paulo')

# ── Paleta Montania ──
C_BRAND      = HexColor('#8B4DB8')
C_BRAND_DARK = HexColor('#5B21B6')
C_BRAND_LIGHT= HexColor('#A855F7')
C_ROSE       = HexColor('#EC4899')
C_TEAL       = HexColor('#2BBFA4')
C_GOLD       = HexColor('#D4A843')
C_BG         = HexColor('#F8F3FF')
C_SURFACE    = HexColor('#FFFFFF')
C_TEXT       = HexColor('#1A0E2E')
C_TEXT2      = HexColor('#4A3760')
C_MUTED      = HexColor('#8B7BA8')
C_SUCCESS    = HexColor('#16A085')
C_DANGER     = HexColor('#E8537A')
C_WARNING    = HexColor('#D4A843')
C_BORDER     = HexColor('#E8DFFF')

W, H = A4  # 595 x 842 pts

def logo_image(logo_b64: str, width=40, height=22):
    """Cria ImageFlowable a partir de base64."""
    if not logo_b64:
        return None
    try:
        if ',' in logo_b64:
            logo_b64 = logo_b64.split(',', 1)[1]
        data = base64.b64decode(logo_b64)
        buf  = io.BytesIO(data)
        img  = RLImage(buf, width=width, height=height)
        return img
    except Exception:
        return None


def _styles():
    """Retorna dicionário de estilos."""
    base = getSampleStyleSheet()
    return {
        'cover_title': ParagraphStyle('ct', fontName='Helvetica-Bold', fontSize=32,
                        textColor=white, leading=38, alignment=TA_LEFT),
        'cover_sub':   ParagraphStyle('cs', fontName='Helvetica', fontSize=13,
                        textColor=HexColor('#D8B4FE'), leading=18, alignment=TA_LEFT),
        'cover_meta':  ParagraphStyle('cm', fontName='Helvetica', fontSize=10,
                        textColor=HexColor('#C4B5FD'), leading=14, alignment=TA_LEFT),
        'section':     ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=14,
                        textColor=C_BRAND_DARK, leading=18, spaceBefore=14, spaceAfter=6),
        'subsection':  ParagraphStyle('sub', fontName='Helvetica-Bold', fontSize=11,
                        textColor=C_TEXT2, leading=14, spaceBefore=8, spaceAfter=4),
        'body':        ParagraphStyle('body', fontName='Helvetica', fontSize=9,
                        textColor=C_TEXT2, leading=13, spaceAfter=4),
        'body_bold':   ParagraphStyle('bb', fontName='Helvetica-Bold', fontSize=9,
                        textColor=C_TEXT, leading=13),
        'small':       ParagraphStyle('sm', fontName='Helvetica', fontSize=8,
                        textColor=C_MUTED, leading=11),
        'insight':     ParagraphStyle('ins', fontName='Helvetica', fontSize=9,
                        textColor=C_TEXT2, leading=13, leftIndent=10),
        'insight_bold':ParagraphStyle('insb', fontName='Helvetica-Bold', fontSize=9,
                        textColor=C_TEXT, leading=13, leftIndent=10),
        'table_header':ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8,
                        textColor=white, leading=11, alignment=TA_CENTER),
        'table_cell':  ParagraphStyle('tc', fontName='Helvetica', fontSize=8.5,
                        textColor=C_TEXT2, leading=12, alignment=TA_CENTER),
        'table_left':  ParagraphStyle('tl', fontName='Helvetica', fontSize=8.5,
                        textColor=C_TEXT2, leading=12, alignment=TA_LEFT),
        'footer':      ParagraphStyle('ft', fontName='Helvetica', fontSize=7.5,
                        textColor=C_MUTED, leading=10, alignment=TA_CENTER),
    }


def _stat_card_table(cards):
    """Cria uma linha de cards de estatísticas (2 ou 4 por linha)."""
    col_w = (W - 60) / len(cards)
    data  = [[]]
    for card in cards:
        cell = [
            Paragraph(f"<b>{card['value']}</b>", ParagraphStyle(
                'cv', fontName='Helvetica-Bold', fontSize=22,
                textColor=card.get('color', C_BRAND), leading=26, alignment=TA_CENTER)),
            Paragraph(card['label'], ParagraphStyle(
                'cl', fontName='Helvetica-Bold', fontSize=7.5,
                textColor=C_MUTED, leading=10, alignment=TA_CENTER,
                spaceAfter=2, spaceBefore=2)),
            Paragraph(card.get('sub',''), ParagraphStyle(
                'cs2', fontName='Helvetica', fontSize=7,
                textColor=C_MUTED, leading=9, alignment=TA_CENTER)),
        ]
        data[0].append(cell)

    t = Table(data, colWidths=[col_w]*len(cards))
    t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), C_SURFACE),
        ('ROWBACKGROUNDS', (0,0),(-1,-1), [C_SURFACE]),
        ('BOX',         (0,0), (-1,-1), 0.5, C_BORDER),
        ('LINEBEFORE',  (1,0), (-1,-1), 0.5, C_BORDER),
        ('TOPPADDING',  (0,0), (-1,-1), 12),
        ('BOTTOMPADDING',(0,0),(-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING',(0,0), (-1,-1), 8),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [6]),
    ]))
    return t


def _bar_chart(labels, values, color=None, width=480, height=140):
    """Gráfico de barras simples."""
    if not values or all(v == 0 for v in values):
        return None
    d = Drawing(width, height)
    bc = VerticalBarChart()
    bc.x, bc.y = 40, 20
    bc.width, bc.height = width - 60, height - 35
    bc.data = [values]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.angle  = 45 if len(labels) > 8 else 0
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.fillColor = C_MUTED
    bc.valueAxis.labels.fontSize = 7
    bc.valueAxis.labels.fillColor = C_MUTED
    bc.valueAxis.gridStrokeColor  = HexColor('#F0EAF8')
    bc.bars[0].fillColor = color or C_BRAND
    bc.bars[0].strokeColor = None
    bc.groupSpacing = 2
    d.add(bc)
    return d


def _line_chart(labels, values, color=None, width=480, height=130):
    """Gráfico de linha."""
    clean = [(l, v) for l, v in zip(labels, values) if v is not None]
    if len(clean) < 2:
        return None
    ls, vs = zip(*clean)
    d  = Drawing(width, height)
    lc = HorizontalLineChart()
    lc.x, lc.y = 40, 18
    lc.width, lc.height = width - 60, height - 32
    lc.data = [list(vs)]
    lc.categoryAxis.categoryNames = list(ls)
    lc.categoryAxis.labels.angle  = 45 if len(ls) > 8 else 0
    lc.categoryAxis.labels.fontSize = 7
    lc.categoryAxis.labels.fillColor = C_MUTED
    lc.valueAxis.labels.fontSize  = 7
    lc.valueAxis.labels.fillColor = C_MUTED
    lc.valueAxis.gridStrokeColor  = HexColor('#F0EAF8')
    lc.lines[0].strokeColor = color or C_BRAND
    lc.lines[0].strokeWidth = 2
    lc.lines[0].symbol      = None
    d.add(lc)
    return d


def _insight_box(items, title="Análise Automática"):
    """Caixa de insights com fundo colorido."""
    s = _styles()
    rows = [[Paragraph(f"<b>{title}</b>", ParagraphStyle(
        'ibt', fontName='Helvetica-Bold', fontSize=10,
        textColor=C_BRAND_DARK, leading=14))]]
    for item in items:
        icon  = item.get('icon', '•')
        text  = item.get('text', '')
        color = item.get('color', C_TEXT2)
        rows.append([Paragraph(f"{icon}  {text}", ParagraphStyle(
            'ibi', fontName='Helvetica', fontSize=8.5,
            textColor=color, leading=13, leftIndent=4, spaceBefore=3))])

    t = Table(rows, colWidths=[W - 60])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), HexColor('#F5EEFF')),
        ('BACKGROUND',   (0,0), (-1,0),  HexColor('#EDD9FF')),
        ('BOX',          (0,0), (-1,-1), 0.5, C_BRAND_LIGHT),
        ('LINEBEFORE',   (0,0), (-1,-1), 3,   C_BRAND),
        ('TOPPADDING',   (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',(0,0), (-1,-1), 7),
        ('LEFTPADDING',  (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    return t


def _athlete_table(athletes_data):
    """Tabela comparativa de atletas."""
    s = _styles()
    headers = ['#', 'Atleta', 'Km', 'Corridas', 'Pace médio', 'Elevação', 'Calorias', 'FC Média']
    rows = [[Paragraph(h, s['table_header']) for h in headers]]

    colors = [C_BRAND, C_ROSE, C_TEAL, C_GOLD,
              HexColor('#A78BFA'), HexColor('#34D399'),
              HexColor('#FB7185'), HexColor('#60A5FA')]

    for i, ath in enumerate(athletes_data):
        medal = ['🥇','🥈','🥉'][i] if i < 3 else f'#{i+1}'
        row = [
            Paragraph(medal, s['table_cell']),
            Paragraph(f"<b>{ath['name']}</b>", s['table_left']),
            Paragraph(f"<b>{ath['km']}</b>", ParagraphStyle(
                'kv', fontName='Helvetica-Bold', fontSize=9,
                textColor=colors[i%len(colors)], leading=12, alignment=TA_CENTER)),
            Paragraph(str(ath['runs']),   s['table_cell']),
            Paragraph(ath['avg_pace'],    s['table_cell']),
            Paragraph(f"{int(ath.get('elevation',0))}m", s['table_cell']),
            Paragraph(f"{int(ath.get('calories',0))}", s['table_cell']),
            Paragraph(f"{int(ath.get('avg_hr',0)) if ath.get('avg_hr') else '—'}", s['table_cell']),
        ]
        rows.append(row)

    col_ws = [20, 90, 45, 45, 52, 48, 48, 48]
    t = Table(rows, colWidths=col_ws)
    style = [
        ('BACKGROUND',   (0,0), (-1,0),  C_BRAND_DARK),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [C_SURFACE, HexColor('#F8F3FF')]),
        ('BOX',          (0,0), (-1,-1), 0.5, C_BORDER),
        ('INNERGRID',    (0,0), (-1,-1), 0.3, HexColor('#EDE8FF')),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
    ]
    t.setStyle(TableStyle(style))
    return t


def _header_footer(canvas, doc, logo_b64=None, period_label='', athlete_label=''):
    """Cabeçalho e rodapé em todas as páginas (exceto capa)."""
    canvas.saveState()
    page = canvas.getPageNumber()

    if page > 1:
        # Cabeçalho
        canvas.setFillColor(C_BRAND_DARK)
        canvas.rect(0, H - 32, W, 32, fill=1, stroke=0)

        # Logo no cabeçalho
        if logo_b64:
            try:
                raw = logo_b64.split(',',1)[1] if ',' in logo_b64 else logo_b64
                buf = io.BytesIO(base64.b64decode(raw))
                canvas.drawImage(buf, 20, H-26, width=50, height=14,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        canvas.setFillColor(white)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(80, H - 20, 'MONTANIA — Relatório de Performance')
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(W - 20, H - 20,
            f"{period_label}  |  {athlete_label}")

        # Linha separadora
        canvas.setStrokeColor(HexColor('#C4B5FD'))
        canvas.setLineWidth(0.3)
        canvas.line(20, H - 34, W - 20, H - 34)

        # Rodapé
        canvas.setStrokeColor(C_BORDER)
        canvas.line(20, 26, W - 20, 26)
        canvas.setFillColor(C_MUTED)
        canvas.setFont('Helvetica', 7.5)
        now_br = datetime.now(TZ_BR).strftime('%d/%m/%Y às %H:%M')
        canvas.drawString(20, 14, f'MONTANIA · Gerado em {now_br} · Confidencial')
        canvas.drawRightString(W - 20, 14, f'Página {page}')

    canvas.restoreState()


def generate_report(athletes_data, group_stats, volume_data,
                    pace_data, filters, logo_b64=None):
    """
    Gera o PDF do relatório e retorna bytes.

    athletes_data: lista de dicts com stats por atleta
    group_stats:   dict com totais do grupo
    volume_data:   dict {labels, data} volume semanal
    pace_data:     dict {labels, data} pace médio
    filters:       dict com period, sport_type, athlete_name, date_range
    logo_b64:      string base64 do logo
    """
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4,
                              leftMargin=30, rightMargin=30,
                              topMargin=48, bottomMargin=40)

    s     = _styles()
    story = []

    now_br    = datetime.now(TZ_BR)
    now_str   = now_br.strftime('%d/%m/%Y às %H:%M')
    period_lb = filters.get('period_label', 'Período selecionado')
    ath_lb    = filters.get('athlete_label', 'Todas as atletas')

    # ══════════════════════════════════════
    # CAPA
    # ══════════════════════════════════════
    def draw_cover(canvas, doc):
        canvas.saveState()
        # Fundo gradiente simulado com retângulos
        canvas.setFillColor(HexColor('#0D0520'))
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        canvas.setFillColor(HexColor('#2D0B5A'))
        canvas.rect(0, H*0.4, W, H*0.6, fill=1, stroke=0)

        # Blob decorativo
        canvas.setFillColor(HexColor('#4A1082'))
        canvas.setStrokeColor(HexColor('#4A1082'))
        canvas.circle(80, H - 80, 140, fill=1, stroke=0)
        canvas.setFillColor(HexColor('#8B1A6B'))
        canvas.circle(W - 60, 120, 100, fill=1, stroke=0)

        # Logo
        if logo_b64:
            try:
                raw = logo_b64.split(',',1)[1] if ',' in logo_b64 else logo_b64
                buf2 = io.BytesIO(base64.b64decode(raw))
                canvas.drawImage(buf2, 40, H - 90, width=100, height=56,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # MONTANIA wordmark
        canvas.setFillColor(white)
        canvas.setFont('Helvetica-Bold', 11)
        canvas.drawString(150, H - 60, 'MONTANIA')
        canvas.setFillColor(HexColor('#C4B5FD'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(150, H - 73, 'MENTORIA · PERFORMANCE FEMININA')

        # Linha decorativa
        canvas.setStrokeColor(HexColor('#8B4DB8'))
        canvas.setLineWidth(1.5)
        canvas.line(40, H - 110, W - 40, H - 110)

        # Título principal
        canvas.setFillColor(white)
        canvas.setFont('Helvetica-Bold', 36)
        canvas.drawString(40, H - 170, 'Relatório de')
        canvas.setFont('Helvetica-BoldOblique', 36)
        canvas.setFillColor(HexColor('#D8B4FE'))
        canvas.drawString(40, H - 210, 'Performance')

        canvas.setFillColor(white)
        canvas.setFont('Helvetica-Bold', 20)
        canvas.drawString(40, H - 250, 'Mentoria MONTANIA')

        # Linha separadora
        canvas.setStrokeColor(HexColor('#6B21A8'))
        canvas.setLineWidth(0.5)
        canvas.line(40, H - 275, W - 40, H - 275)

        # Metadados
        canvas.setFillColor(HexColor('#C4B5FD'))
        canvas.setFont('Helvetica', 10)
        canvas.drawString(40, H - 300, f'Período: {period_lb}')
        canvas.drawString(40, H - 318, f'Atletas: {ath_lb}')
        canvas.drawString(40, H - 336, f'Gerado em: {now_str}')
        canvas.drawString(40, H - 354, f'Gestor: {filters.get("manager_name", "—")}')

        # Cards de resumo na capa
        cards = [
            (group_stats.get('total_athletes', 0), 'Atletas'),
            (f"{group_stats.get('total_km', 0)}", 'Km no período'),
            (f"{group_stats.get('total_runs', 0)}", 'Corridas'),
            (f"{group_stats.get('avg_pace', '—')}", 'Pace médio'),
        ]
        cw = (W - 80) / 4
        cy = H - 460
        for i, (val, lbl) in enumerate(cards):
            cx = 40 + i * cw
            canvas.setFillColor(HexColor('#2D1B4E'))
            canvas.roundRect(cx, cy, cw - 8, 70, 8, fill=1, stroke=0)
            canvas.setStrokeColor(HexColor('#7C3AED'))
            canvas.setLineWidth(0.5)
            canvas.roundRect(cx, cy, cw - 8, 70, 8, fill=0, stroke=1)
            canvas.setFillColor(HexColor('#D8B4FE'))
            canvas.setFont('Helvetica-Bold', 20)
            canvas.drawCentredString(cx + (cw-8)/2, cy + 40, str(val))
            canvas.setFillColor(HexColor('#9B8BB0'))
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(cx + (cw-8)/2, cy + 24, lbl.upper())

        # Rodapé da capa
        canvas.setFillColor(HexColor('#4A3760'))
        canvas.rect(0, 0, W, 50, fill=1, stroke=0)
        canvas.setFillColor(HexColor('#8B7BA8'))
        canvas.setFont('Helvetica', 7.5)
        canvas.drawCentredString(W/2, 20, 'Documento confidencial · Uso exclusivo da equipe MONTANIA · montania.onrender.com')

        canvas.restoreState()

    # Página de capa em branco com desenho customizado
    story.append(Spacer(1, H - 60))  # será sobrescrita pelo onFirstPage
    story.append(PageBreak())

    # ══════════════════════════════════════
    # PÁG 2 — INDICADORES PRINCIPAIS
    # ══════════════════════════════════════
    story.append(Paragraph('Indicadores Principais', s['section']))
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=10))

    # Cards linha 1
    def fmt_pace(secs):
        if not secs: return '—'
        m = int(secs//60); sc = int(secs%60)
        return f"{m}'{sc:02d}\""

    cards1 = [
        {'value': str(group_stats.get('total_runs', 0)),
         'label': 'CORRIDAS NO PERÍODO', 'sub': 'total do grupo', 'color': C_BRAND},
        {'value': f"{group_stats.get('total_km', 0)} km",
         'label': 'KM PERCORRIDOS', 'sub': 'soma do grupo', 'color': C_TEAL},
        {'value': fmt_pace(group_stats.get('avg_pace_secs')),
         'label': 'PACE MÉDIO', 'sub': 'min/km do grupo', 'color': C_ROSE},
        {'value': f"{int(group_stats.get('total_elevation', 0))}m",
         'label': 'ELEVAÇÃO TOTAL', 'sub': 'metros acumulados', 'color': C_GOLD},
    ]
    story.append(_stat_card_table(cards1))
    story.append(Spacer(1, 10))

    cards2 = [
        {'value': str(group_stats.get('total_athletes', 0)),
         'label': 'ATLETAS ATIVAS', 'sub': 'no período', 'color': C_BRAND_DARK},
        {'value': str(group_stats.get('athletes_trained', 0)),
         'label': 'TREINARAM', 'sub': 'pelo menos 1x', 'color': C_SUCCESS},
        {'value': str(group_stats.get('total_calories', 0)),
         'label': 'CALORIAS TOTAIS', 'sub': 'kcal estimadas', 'color': C_ROSE},
        {'value': group_stats.get('best_athlete', '—'),
         'label': 'DESTAQUE', 'sub': 'maior volume', 'color': C_GOLD},
    ]
    story.append(_stat_card_table(cards2))
    story.append(Spacer(1, 14))

    # ── Análise automática ──
    insights = _auto_insights(group_stats, athletes_data)
    story.append(_insight_box(insights, '✦ Análise Automática'))
    story.append(Spacer(1, 14))

    # ── Volume semanal ──
    if volume_data and volume_data.get('labels'):
        story.append(Paragraph('Volume Semanal do Grupo', s['subsection']))
        chart = _bar_chart(volume_data['labels'], volume_data['data'],
                           color=C_BRAND, width=510, height=130)
        if chart:
            story.append(chart)
        story.append(Spacer(1, 10))

    # ── Tendência de pace ──
    if pace_data and pace_data.get('labels'):
        story.append(Paragraph('Evolução do Pace Médio', s['subsection']))
        chart = _line_chart(pace_data['labels'], pace_data['data'],
                            color=C_TEAL, width=510, height=120)
        if chart:
            story.append(chart)
        story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ══════════════════════════════════════
    # PÁG 3 — RANKING E COMPARATIVO
    # ══════════════════════════════════════
    story.append(Paragraph('Ranking de Performance — Atletas', s['section']))
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=10))

    if athletes_data:
        story.append(_athlete_table(athletes_data))
        story.append(Spacer(1, 14))

        # Gráfico comparativo de km
        names  = [a['name'].split()[0] for a in athletes_data[:8]]
        kms    = [a['km'] for a in athletes_data[:8]]
        if kms:
            story.append(Paragraph('Comparativo de Volume (Km)', s['subsection']))
            chart = _bar_chart(names, kms, color=C_BRAND_LIGHT, width=510, height=130)
            if chart:
                story.append(chart)
            story.append(Spacer(1, 10))

        # Gráfico de corridas
        runs = [a['runs'] for a in athletes_data[:8]]
        if runs:
            story.append(Paragraph('Comparativo de Frequência (Corridas)', s['subsection']))
            chart = _bar_chart(names, runs, color=C_TEAL, width=510, height=110)
            if chart:
                story.append(chart)

    story.append(PageBreak())

    # ══════════════════════════════════════
    # PÁG 4 — PERFIS INDIVIDUAIS
    # ══════════════════════════════════════
    story.append(Paragraph('Perfis Individuais', s['section']))
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=8))

    for i, ath in enumerate(athletes_data):
        name     = ath['name']
        km       = ath['km']
        runs     = ath['runs']
        pace     = ath['avg_pace']
        elev     = int(ath.get('elevation', 0))
        cal      = int(ath.get('calories', 0))
        avg_hr   = int(ath.get('avg_hr', 0)) if ath.get('avg_hr') else None
        connected = ath.get('connected', False)
        streak   = ath.get('streak', 0)

        # Mini card por atleta
        ath_rows = [
            [
                Paragraph(f"<b>{name}</b>", ParagraphStyle(
                    'an', fontName='Helvetica-Bold', fontSize=11,
                    textColor=C_BRAND_DARK, leading=14)),
                Paragraph(
                    f"{'● Strava conectado' if connected else '○ Sem Strava'}",
                    ParagraphStyle('as', fontName='Helvetica', fontSize=8,
                    textColor=C_SUCCESS if connected else C_DANGER, leading=11,
                    alignment=TA_RIGHT)),
            ],
            [
                Table([[
                    Paragraph(f"<b>{km}</b> km", ParagraphStyle(
                        'av', fontName='Helvetica-Bold', fontSize=10,
                        textColor=C_BRAND, leading=13)),
                    Paragraph(f"<b>{runs}</b> corridas", ParagraphStyle(
                        'av2', fontName='Helvetica-Bold', fontSize=10,
                        textColor=C_TEAL, leading=13)),
                    Paragraph(f"<b>{pace}</b>/km", ParagraphStyle(
                        'av3', fontName='Helvetica-Bold', fontSize=10,
                        textColor=C_ROSE, leading=13)),
                    Paragraph(f"<b>{elev}m</b> elev.", ParagraphStyle(
                        'av4', fontName='Helvetica-Bold', fontSize=10,
                        textColor=C_GOLD, leading=13)),
                    Paragraph(f"<b>{cal}</b> kcal", ParagraphStyle(
                        'av5', fontName='Helvetica-Bold', fontSize=10,
                        textColor=HexColor('#A78BFA'), leading=13)),
                ]], colWidths=[80,80,70,70,80]),
                Paragraph('', s['small']),
            ]
        ]
        ath_t = Table(ath_rows, colWidths=[W-66, 100] if len(ath_rows[0]) == 2 else [W-66])
        ath_t.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), HexColor('#FDFAFF')),
            ('BOX',          (0,0), (-1,-1), 0.5, C_BORDER),
            ('LINEBEFORE',   (0,0), (0,-1), 3, C_BRAND),
            ('TOPPADDING',   (0,0), (-1,-1), 8),
            ('BOTTOMPADDING',(0,0), (-1,-1), 8),
            ('LEFTPADDING',  (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
            ('SPAN',         (0,1), (-1,1)),
        ]))
        story.append(KeepTogether([ath_t, Spacer(1, 8)]))

    story.append(PageBreak())

    # ══════════════════════════════════════
    # PÁG 5 — ANÁLISE INTERPRETATIVA
    # ══════════════════════════════════════
    story.append(Paragraph('Análise e Recomendações', s['section']))
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=10))

    recs = _recommendations(group_stats, athletes_data)
    for rec in recs:
        box = _insight_box(rec['items'], rec['title'])
        story.append(box)
        story.append(Spacer(1, 8))

    # Rodapé final
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'Relatório gerado em {now_str} · MONTANIA Mentoria de Corrida Feminina · Documento confidencial',
        s['footer']))

    # Build com capa customizada
    doc.build(
        story,
        onFirstPage=draw_cover,
        onLaterPages=lambda c, d: _header_footer(
            c, d, logo_b64=logo_b64,
            period_label=period_lb,
            athlete_label=ath_lb
        )
    )

    return buf.getvalue()


def _auto_insights(group_stats, athletes_data):
    """Gera insights automáticos baseados nos dados."""
    insights = []
    total_km  = group_stats.get('total_km', 0)
    total_runs= group_stats.get('total_runs', 0)
    trained   = group_stats.get('athletes_trained', 0)
    total_ath = group_stats.get('total_athletes', 1)
    best      = group_stats.get('best_athlete', '')
    worst_km  = group_stats.get('min_km', 0)

    participation = (trained / total_ath * 100) if total_ath else 0

    if participation >= 80:
        insights.append({'icon': '✅', 'text': f'Alta participação: {trained} de {total_ath} atletas treinaram no período ({participation:.0f}%).', 'color': C_SUCCESS})
    elif participation >= 50:
        insights.append({'icon': '🟡', 'text': f'Participação moderada: {trained} de {total_ath} atletas ativas ({participation:.0f}%). Há espaço para engajamento.', 'color': C_WARNING})
    else:
        insights.append({'icon': '🔴', 'text': f'Baixa participação: apenas {trained} de {total_ath} atletas treinaram ({participation:.0f}%). Atenção recomendada.', 'color': C_DANGER})

    if total_km > 0:
        avg_km = total_km / total_ath
        insights.append({'icon': '📍', 'text': f'Volume médio por atleta: {avg_km:.1f} km. Total do grupo: {total_km} km em {total_runs} corridas.', 'color': C_TEXT2})

    if best:
        insights.append({'icon': '🏆', 'text': f'Destaque do período: {best} liderou o ranking de volume.', 'color': C_BRAND_DARK})

    if athletes_data:
        kms  = [a['km'] for a in athletes_data if a['km'] > 0]
        if kms and (max(kms) - min(kms)) > 20:
            insights.append({'icon': '📊', 'text': f'Grande variação de volume: {max(kms):.1f} km vs {min(kms):.1f} km. Considere redistribuir estímulos.', 'color': C_WARNING})

        no_runs = [a['name'] for a in athletes_data if a['runs'] == 0]
        if no_runs:
            insights.append({'icon': '⚠️', 'text': f'Sem atividade no período: {", ".join(no_runs[:3])}{"..." if len(no_runs) > 3 else ""}. Verificar engajamento.', 'color': C_DANGER})

    return insights


def _recommendations(group_stats, athletes_data):
    """Seções de recomendações estruturadas."""
    recs = []

    # Engajamento
    no_runs = [a for a in athletes_data if a['runs'] == 0]
    low_runs = [a for a in athletes_data if 0 < a['runs'] <= 2]
    if no_runs or low_runs:
        items = []
        if no_runs:
            items.append({'icon': '→', 'text': f'Atletas sem treinos: {", ".join(a["name"] for a in no_runs)}. Recomenda-se contato individual para verificar barreiras.', 'color': C_DANGER})
        if low_runs:
            items.append({'icon': '→', 'text': f'Atletas com baixa frequência (1-2 treinos): {", ".join(a["name"] for a in low_runs[:3])}. Considere ajuste de carga ou motivação.', 'color': C_WARNING})
        recs.append({'title': '⚠️ Atenção — Engajamento', 'items': items})

    # Performance
    paced = [a for a in athletes_data if a.get('avg_pace_secs') and a['avg_pace_secs'] > 0]
    if paced:
        best_pacer  = min(paced, key=lambda a: a['avg_pace_secs'])
        worst_pacer = max(paced, key=lambda a: a['avg_pace_secs'])
        items = [
            {'icon': '↑', 'text': f'Melhor pace: {best_pacer["name"]} com {best_pacer["avg_pace"]}. Ótima referência para o grupo.', 'color': C_SUCCESS},
            {'icon': '→', 'text': f'Pace para desenvolvimento: {worst_pacer["name"]} em {worst_pacer["avg_pace"]}. Trabalhos de velocidade podem ajudar.', 'color': C_TEXT2},
        ]
        recs.append({'title': '⚡ Performance — Pace', 'items': items})

    # Volume
    top = sorted(athletes_data, key=lambda a: a['km'], reverse=True)
    if top:
        items = [
            {'icon': '★', 'text': f'Maior volume: {top[0]["name"]} com {top[0]["km"]} km — excelente consistência.', 'color': C_SUCCESS},
        ]
        if len(top) > 1:
            items.append({'icon': '→', 'text': f'Oportunidade: aumentar gradualmente o volume das atletas com menos de {round(sum(a["km"] for a in top)/len(top),1)} km (média do grupo).', 'color': C_TEXT2})
        recs.append({'title': '📈 Progressão de Volume', 'items': items})

    return recs
