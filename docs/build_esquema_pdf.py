import html
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

OUT_DIR = "/tmp/claude-0/-home-claude/188f0eb6-61fe-5e64-a8e6-37c7540249a9/scratchpad"
OUT = os.path.join(OUT_DIR, "esquema_capa1.pdf")

# ---------- estilos ----------
INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#52606d")
HEAD_BG = colors.HexColor("#243b53")
GROUP_BG = colors.HexColor("#2f6db5")
TABLE_BG = colors.HexColor("#dbe7f5")
GRID = colors.HexColor("#c7d2de")
KEY_BG = colors.HexColor("#fff6dd")

base = ParagraphStyle("base", fontName="Helvetica", fontSize=8.5, leading=10.8, textColor=INK)
cell = ParagraphStyle("cell", parent=base)
cell_bold = ParagraphStyle("cell_bold", parent=base, fontName="Helvetica-Bold")
cell_mono = ParagraphStyle("cell_mono", parent=base, fontName="Courier-Bold", fontSize=8.5)
cell_type = ParagraphStyle("cell_type", parent=base, fontName="Courier", fontSize=8)
head = ParagraphStyle("head", parent=base, fontName="Helvetica-Bold", textColor=colors.white, fontSize=9)
group_style = ParagraphStyle("group", parent=base, fontName="Helvetica-Bold", textColor=colors.white, fontSize=10.5, leading=13)
table_name = ParagraphStyle("tname", parent=base, fontName="Courier-Bold", fontSize=9.5, leading=12)
table_desc = ParagraphStyle("tdesc", parent=base, fontName="Helvetica-Oblique", textColor=MUTED, fontSize=8.5)
title = ParagraphStyle("title", parent=base, fontName="Helvetica-Bold", fontSize=20, leading=24)
subtitle = ParagraphStyle("subtitle", parent=base, fontSize=10.5, leading=14, textColor=MUTED)
h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12.5, leading=16, spaceBefore=4, spaceAfter=4)
body = ParagraphStyle("body", parent=base, fontSize=9.5, leading=13.5)
small_center = ParagraphStyle("sc", parent=base, alignment=1, fontName="Courier-Bold", fontSize=9)
arrow = ParagraphStyle("arrow", parent=base, alignment=1, fontName="Helvetica-Bold", fontSize=12, textColor=MUTED)


def P(text, style=cell):
    return Paragraph(html.escape(text), style)


# ---------- datos ----------
SCHEMA = [
    ("ESTRUCTURA  -  quién y dónde", [
        ("unidad", "Organigrama: brigadas, batallones y compañías", [
            ("id", "INT PK", "Identificador de la unidad", "3"),
            ("nombre", "TEXT", "Nombre de la unidad", "2.º Batallón"),
            ("tipo", "TEXT", "Nivel: brigada, batallón, compañía", "batallón"),
            ("unidad_padre_id", "INT FK", "Unidad de la que depende (crea la jerarquía). Vacío en la más alta", "1"),
        ]),
        ("deposito", "Dónde se guarda el material", [
            ("id", "INT PK", "Identificador del depósito", "2"),
            ("nombre", "TEXT", "Nombre del depósito", "Depósito Central Norte"),
            ("unidad_id", "INT FK", "Unidad a la que pertenece. Vacío si es un depósito central", "vacío"),
        ]),
        ("articulo", "Catálogo de todo lo que puede haber en stock", [
            ("id", "INT PK", "Identificador del artículo", "42"),
            ("codigo", "TEXT", "Código único del artículo", "FRE-0042"),
            ("nombre", "TEXT", "Descripción", "Pastillas de freno delanteras"),
            ("tipo", "TEXT", "repuesto, consumible o equipo_serie. Permite añadir munición y armas sin cambiar el esquema", "repuesto"),
            ("categoria", "TEXT", "Familia del artículo", "frenos"),
            ("criticidad", "INT (1-3)", "Cuánto afecta su falta a la operatividad (3 = crítico)", "3"),
            ("plazo_entrega_dias", "INT", "Días que tarda en llegar un pedido", "45"),
        ]),
    ]),
    ("VEHÍCULOS  -  el histórico", [
        ("vehiculo", "Cada vehículo, seguido individualmente", [
            ("id", "INT PK", "Identificador interno", "317"),
            ("serie", "TEXT", "Número de serie / matrícula", "VEH-00317"),
            ("modelo", "TEXT", "Modelo del vehículo", "Camión 4x4 ligero"),
            ("unidad_id", "INT FK", "Unidad a la que está asignado", "3"),
            ("estado", "TEXT", "operativo, en_taller o baja", "operativo"),
            ("km_actuales", "INT", "Kilometraje actual", "61000"),
            ("fecha_alta", "DATE", "Cuándo entró en servicio", "2019-03-12"),
        ]),
        ("itv", "Cada inspección de un vehículo (muchas por vehículo)", [
            ("id", "INT PK", "Identificador de la inspección", "908"),
            ("vehiculo_id", "INT FK", "Vehículo inspeccionado", "317"),
            ("fecha", "DATE", "Día de la inspección", "2025-01-15"),
            ("km", "INT", "Kilómetros en ese momento (el modelo lo usa)", "61000"),
            ("resultado", "TEXT", "apto o con_defectos", "con_defectos"),
        ]),
        ("defecto", "Cada defecto hallado en una ITV", [
            ("id", "INT PK", "Identificador del defecto", "1500"),
            ("itv_id", "INT FK", "ITV en la que se detectó", "908"),
            ("sistema", "TEXT", "Frenos, luces, neumáticos, motor, transmisión, suspensión, eléctrico, dirección", "frenos"),
            ("gravedad", "INT (1-3)", "Severidad (3 = grave)", "2"),
            ("descripcion", "TEXT", "Texto libre", "Pastillas desgastadas"),
        ]),
        ("reparacion", "Cada arreglo, ligado a un defecto de ITV o suelto (avería entre ITV)", [
            ("id", "INT PK", "Identificador de la reparación", "2210"),
            ("vehiculo_id", "INT FK", "Vehículo reparado", "317"),
            ("defecto_id", "INT FK", "Defecto de ITV que se arregla. Vacío si es una avería suelta", "1500"),
            ("fecha", "DATE", "Día de la reparación", "2025-01-20"),
            ("tipo", "TEXT", "cambio_pieza, ajuste o reparación", "cambio_pieza"),
            ("articulo_id", "INT FK", "Pieza usada (vacío si no se usó ninguna)", "42"),
            ("cantidad", "INT", "Unidades de la pieza usadas", "2"),
            ("horas_taller", "REAL", "Horas de trabajo", "1.5"),
            ("resultado", "TEXT", "solucionado o reincidió (sirve para detectar piezas o reparaciones que fallan)", "solucionado"),
        ]),
    ]),
    ("STOCK  -  lo que hay y lo que debería haber", [
        ("dotacion", "Lo que cada depósito debería tener", [
            ("deposito_id", "INT FK", "Depósito", "2"),
            ("articulo_id", "INT FK", "Artículo", "42"),
            ("cantidad_reglamentaria", "INT", "Lo que ese depósito debería tener", "20"),
            ("minimo", "INT", "Por debajo de esto salta la alerta", "8"),
        ]),
        ("movimiento", "Todo lo que entra, sale o se mueve. De aquí se calculan las existencias", [
            ("id", "INT PK", "Identificador del movimiento", "70123"),
            ("fecha", "DATE", "Día del movimiento", "2025-01-20"),
            ("deposito_id", "INT FK", "Depósito donde ocurre (el de origen en una transferencia)", "2"),
            ("articulo_id", "INT FK", "Artículo movido", "42"),
            ("tipo", "TEXT", "entrada, salida, consumo, transferencia o ajuste", "consumo"),
            ("cantidad", "INT", "Unidades. Siempre positiva; el tipo decide si suma o resta (el ajuste puede llevar signo)", "2"),
            ("deposito_destino_id", "INT FK", "Solo en transferencias: depósito que recibe", "vacío"),
            ("reparacion_id", "INT FK", "Reparación que causó el consumo, si la hubo", "2210"),
        ]),
        ("pedido", "Material pedido: en tránsito o ya recibido", [
            ("id", "INT PK", "Identificador del pedido", "55"),
            ("deposito_id", "INT FK", "Depósito que lo pide", "2"),
            ("articulo_id", "INT FK", "Artículo pedido", "42"),
            ("cantidad", "INT", "Unidades pedidas", "30"),
            ("fecha_pedido", "DATE", "Cuándo se pidió", "2025-01-10"),
            ("fecha_prevista", "DATE", "Cuándo debería llegar (fecha del pedido + plazo de entrega)", "2025-02-24"),
            ("fecha_recibido", "DATE", "Cuándo llegó de verdad. Vacío = sigue en tránsito", "vacío"),
        ]),
    ]),
]

COL_W = [122, 78, 408, 174]  # suma 782 pt (A4 apaisado con márgenes de 30 pt)


def build_main_table():
    rows = [[P("Columna", head), P("Tipo", head), P("Qué es", head), P("Ejemplo", head)]]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRID),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
    ]
    r = 1
    for group, tables in SCHEMA:
        rows.append([P(group, group_style), "", "", ""])
        style += [
            ("SPAN", (0, r), (-1, r)),
            ("BACKGROUND", (0, r), (-1, r), GROUP_BG),
            ("TOPPADDING", (0, r), (-1, r), 5),
            ("BOTTOMPADDING", (0, r), (-1, r), 5),
        ]
        r += 1
        for tname, tdesc, cols in tables:
            rows.append([P(tname, table_name), P(tdesc, table_desc), "", ""])
            style += [
                ("SPAN", (1, r), (-1, r)),
                ("BACKGROUND", (0, r), (-1, r), TABLE_BG),
            ]
            first = r
            r += 1
            for col, tipo, desc, ejemplo in cols:
                rows.append([P(col, cell_mono), P(tipo, cell_type), P(desc, cell), P(ejemplo, cell)])
                if "PK" in tipo or "FK" in tipo:
                    style.append(("BACKGROUND", (1, r), (1, r), KEY_BG))
                r += 1
            style.append(("NOSPLIT", (0, first), (-1, first + 1)))
    t = Table(rows, colWidths=COL_W, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


def build_chain():
    boxes = ["vehiculo", "itv", "defecto", "reparacion", "articulo"]
    cells, widths = [], []
    for i, b in enumerate(boxes):
        cells.append(P(b, small_center))
        widths.append(96)
        if i < len(boxes) - 1:
            cells.append(P(">", arrow))
            widths.append(34)
    t = Table([cells], colWidths=widths, hAlign="LEFT")
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 7),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]
    for i in range(0, len(cells), 2):
        st += [("BOX", (i, 0), (i, 0), 0.8, GROUP_BG), ("BACKGROUND", (i, 0), (i, 0), TABLE_BG)]
    t.setStyle(TableStyle(st))
    return t


def build_example():
    data = [
        ["Fecha", "Registro", "Detalle"],
        ["Ene 2024", "ITV", "42.000 km, con defectos"],
        ["Ene 2024", "Defecto", "Frenos: pastillas desgastadas"],
        ["Ene 2024", "Reparación", "Cambio de pastillas (2 uds), 1,5 h, solucionado"],
        ["Ago 2024", "Reparación suelta", "Avería de batería, cambio (1 ud), 0,5 h"],
        ["Ene 2025", "ITV", "61.000 km, apto"],
    ]
    rows = [[P(c, head if i == 0 else cell) for c in row] for i, row in enumerate(data)]
    t = Table(rows, colWidths=[80, 120, 360], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRID),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def build_legend():
    data = [
        [P("PK", cell_mono), P("Clave primaria: el identificador único de cada fila de la tabla.", cell)],
        [P("FK", cell_mono), P("Clave foránea: un enlace a una fila de otra tabla (por ejemplo, vehiculo_id apunta a un vehículo).", cell)],
        [P("INT / REAL / TEXT / DATE", cell_mono), P("Número entero, número con decimales, texto y fecha.", cell)],
        [P("vacío", cell_mono), P("El campo puede quedar sin valor (en bases de datos, NULL).", cell)],
        [P("(1-3)", cell_mono), P("Escala del 1 al 3; el número más alto es el más crítico o grave.", cell)],
    ]
    t = Table(data, colWidths=[150, 630], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("BACKGROUND", (0, 0), (0, -1), KEY_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(30, 18, "Capa 1 - Esquema de datos - Proyecto de logística militar (ficticio)")
    canvas.drawRightString(landscape(A4)[0] - 30, 18, "Página %d" % doc.page)
    canvas.restoreState()


def main():
    doc = SimpleDocTemplate(
        OUT, pagesize=landscape(A4),
        leftMargin=30, rightMargin=30, topMargin=28, bottomMargin=34,
        title="Capa 1 - Esquema de datos", author="Claude",
    )
    story = [
        Paragraph("Capa 1: esquema de datos", title),
        Spacer(1, 4),
        Paragraph(
            "Proyecto de portfolio: herramienta ficticia pero funcional de logística militar. "
            "Esta capa es la base, sin ML todavía: estructura, vehículos con su histórico de ITV y reparaciones, y stock.",
            subtitle),
        Spacer(1, 10),
        Paragraph("Cómo leer las tablas", h2),
        build_legend(),
        Spacer(1, 12),
        Paragraph("1. Las tablas, columna a columna", h2),
        build_main_table(),
        Spacer(1, 14),
        KeepTogether([
            Paragraph("2. Cómo se conectan los registros de un vehículo", h2),
            Paragraph(
                "Cada vehículo tiene muchas ITV, cada ITV puede tener varios defectos y cada defecto se arregla con una o más "
                "reparaciones que usan un artículo del catálogo. Las averías entre ITV son reparaciones sueltas (sin defecto asociado).",
                body),
            Spacer(1, 6),
            build_chain(),
            Spacer(1, 6),
            Paragraph(
                "Cada reparación que usa una pieza genera un <b>movimiento</b> de consumo, y así los datos de vehículos y de stock quedan unidos.",
                body),
        ]),
        Spacer(1, 12),
        KeepTogether([
            Paragraph("3. Ejemplo: el histórico de un vehículo", h2),
            build_example(),
            Spacer(1, 6),
            Paragraph(
                "Cada ITV, con el estado del vehículo en ese momento, es un ejemplo de entrenamiento. Las reparaciones posteriores son "
                "la respuesta que el modelo debe aprender a predecir: qué pieza se cambió y cuándo.",
                body),
        ]),
        Spacer(1, 12),
        KeepTogether([
            Paragraph("4. Existencias: no hay tabla", h2),
            Paragraph(
                "El stock de cada artículo en cada depósito se calcula sumando los <b>movimientos</b>. Así nunca se descuadra respecto a "
                "los movimientos y se puede reconstruir el stock de cualquier fecha pasada, que es lo que necesita el modelo para entrenar. "
                "Se expondrá como una vista de la base de datos.",
                body),
        ]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


main()
