import html
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

OUT_DIR = "/tmp/claude-0/-home-claude/188f0eb6-61fe-5e64-a8e6-37c7540249a9/scratchpad"
OUT = os.path.join(OUT_DIR, "schema_layer1.pdf")

# ---------- styles ----------
INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#52606d")
HEAD_BG = colors.HexColor("#243b53")
GROUP_BG = colors.HexColor("#2f6db5")
TABLE_BG = colors.HexColor("#dbe7f5")
GRID = colors.HexColor("#c7d2de")
KEY_BG = colors.HexColor("#fff6dd")
ACCESS_BG = colors.HexColor("#eef2ff")

base = ParagraphStyle("base", fontName="Helvetica", fontSize=8.5, leading=10.8, textColor=INK)
cell = ParagraphStyle("cell", parent=base)
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
tree = ParagraphStyle("tree", parent=base, fontName="Courier", fontSize=9, leading=13)


def P(text, style=cell):
    return Paragraph(html.escape(text), style)


# ---------- schema ----------
SCHEMA = [
    ("STRUCTURE  -  who and where", [
        ("unit", "Org chart: divisions, brigades, battalions", [
            ("id", "INT PK", "Unit identifier", "3"),
            ("name", "TEXT", "Unit name", "34th Battalion"),
            ("type", "TEXT", "Echelon: division, brigade, battalion", "battalion"),
            ("parent_unit_id", "INT FK", "Unit it reports to (builds the hierarchy). Empty at the top", "2"),
        ]),
        ("warehouse", "Where material is physically stored", [
            ("id", "INT PK", "Warehouse identifier", "2"),
            ("name", "TEXT", "Warehouse name", "North Central Depot"),
            ("unit_id", "INT FK", "Owning unit. Empty if it is a central depot", "empty"),
        ]),
        ("item", "Catalog of everything that can be held in stock", [
            ("id", "INT PK", "Item identifier", "42"),
            ("code", "TEXT", "Unique item code", "BRK-0042"),
            ("name", "TEXT", "Description", "Front brake pads"),
            ("type", "TEXT", "spare_part, consumable or serial_equipment. Lets weapons/ammo reuse the same catalog", "spare_part"),
            ("category", "TEXT", "Item family", "brakes"),
            ("criticality", "INT (1-3)", "How much its absence hurts readiness (3 = critical)", "3"),
            ("lead_time_days", "INT", "Days an order takes to arrive", "45"),
        ]),
    ]),
    ("ACCESS  -  who can see what", [
        ("app_user", "One row per person who logs in", [
            ("id", "INT PK", "User identifier", "5"),
            ("username", "TEXT", "Login name", "cmd.34bn"),
            ("full_name", "TEXT", "Display name", "Cpt. Alaoui"),
            ("role", "TEXT", "admin (sees everything) or unit (scoped)", "unit"),
            ("unit_id", "INT FK", "Unit this user is scoped to. Empty for admin", "3"),
        ]),
    ]),
    ("VEHICLES  -  the history", [
        ("vehicle", "Each vehicle, tracked individually", [
            ("id", "INT PK", "Internal identifier", "317"),
            ("serial_number", "TEXT", "Serial number / plate", "VEH-00317"),
            ("model", "TEXT", "Vehicle model", "Light 4x4 truck"),
            ("unit_id", "INT FK", "Unit it is assigned to", "3"),
            ("status", "TEXT", "active, in_repair or decommissioned", "active"),
            ("mileage_km", "INT", "Current mileage", "61000"),
            ("in_service_date", "DATE", "When it entered service", "2019-03-12"),
        ]),
        ("inspection", "Each roadworthiness inspection (many per vehicle)", [
            ("id", "INT PK", "Inspection identifier", "908"),
            ("vehicle_id", "INT FK", "Vehicle inspected", "317"),
            ("date", "DATE", "Day of the inspection", "2025-01-15"),
            ("mileage_km", "INT", "Mileage at that time (used by the model)", "61000"),
            ("result", "TEXT", "passed or defects_found", "defects_found"),
        ]),
        ("defect", "Each defect found in an inspection", [
            ("id", "INT PK", "Defect identifier", "1500"),
            ("inspection_id", "INT FK", "Inspection where it was found", "908"),
            ("system", "TEXT", "Brakes, lights, tires, engine, transmission, suspension, electrical, steering", "brakes"),
            ("severity", "INT (1-3)", "Severity (3 = severe)", "2"),
            ("description", "TEXT", "Free text", "Worn brake pads"),
        ]),
        ("repair", "Each fix, linked to an inspection defect or standalone (breakdown between inspections)", [
            ("id", "INT PK", "Repair identifier", "2210"),
            ("vehicle_id", "INT FK", "Vehicle repaired", "317"),
            ("defect_id", "INT FK", "Defect being fixed. Empty for a standalone breakdown", "1500"),
            ("date", "DATE", "Day of the repair", "2025-01-20"),
            ("type", "TEXT", "part_replacement, adjustment or repair", "part_replacement"),
            ("item_id", "INT FK", "Part used (empty if none was used)", "42"),
            ("quantity", "INT", "Units of the part used", "2"),
            ("labor_hours", "REAL", "Workshop hours", "1.5"),
            ("outcome", "TEXT", "fixed or recurred (flags bad parts or failed repairs)", "fixed"),
        ]),
    ]),
    ("WEAPONS  -  serialized equipment", [
        ("weapon", "Each weapon, tracked individually by serial number", [
            ("id", "INT PK", "Internal identifier", "88"),
            ("serial_number", "TEXT", "Serial number", "RIF-04521"),
            ("type", "TEXT", "Weapon type", "assault_rifle"),
            ("caliber", "TEXT", "Caliber", "5.56mm"),
            ("unit_id", "INT FK", "Unit it is assigned to", "3"),
            ("status", "TEXT", "active, in_repair or decommissioned", "active"),
            ("last_inspection_date", "DATE", "Last individual check", "2025-06-01"),
            ("rounds_fired", "INT", "Cumulative rounds fired (proxy for wear)", "3200"),
        ]),
    ]),
    ("AMMUNITION  -  lot-tracked consumable", [
        ("ammo_lot", "Each production lot of ammunition, because it expires", [
            ("id", "INT PK", "Lot identifier", "12"),
            ("item_id", "INT FK", "Catalog item (e.g. 5.56mm ball)", "77"),
            ("lot_number", "TEXT", "Manufacturer's lot number", "LOT-2023-118"),
            ("manufacture_date", "DATE", "When it was produced", "2023-05-10"),
            ("expiry_date", "DATE", "When it expires", "2028-05-10"),
        ]),
    ]),
    ("STOCK  -  what exists and what should exist", [
        ("allowance", "What each warehouse should hold", [
            ("warehouse_id", "INT FK", "Warehouse", "2"),
            ("item_id", "INT FK", "Item", "42"),
            ("authorized_qty", "INT", "What that warehouse should hold", "20"),
            ("minimum_qty", "INT", "Below this, an alert fires", "8"),
        ]),
        ("movement", "Everything that enters, leaves or moves. On-hand stock is calculated from this", [
            ("id", "INT PK", "Movement identifier", "70123"),
            ("date", "DATE", "Day of the movement", "2025-01-20"),
            ("warehouse_id", "INT FK", "Warehouse where it happens (source in a transfer)", "2"),
            ("item_id", "INT FK", "Item moved", "42"),
            ("type", "TEXT", "receipt, issue, consumption, transfer or adjustment", "consumption"),
            ("quantity", "INT", "Units. Always positive; type decides +/- (adjustment can carry a sign)", "2"),
            ("dest_warehouse_id", "INT FK", "Transfers only: receiving warehouse", "empty"),
            ("repair_id", "INT FK", "Repair that caused the consumption, if any", "2210"),
            ("lot_id", "INT FK", "Ammo lot moved, if the item is lot-tracked. Empty otherwise", "empty"),
        ]),
        ("order", "Material on order: in transit or already received", [
            ("id", "INT PK", "Order identifier", "55"),
            ("warehouse_id", "INT FK", "Warehouse that placed it", "2"),
            ("item_id", "INT FK", "Item ordered", "42"),
            ("quantity", "INT", "Units ordered", "30"),
            ("order_date", "DATE", "When it was placed", "2025-01-10"),
            ("expected_date", "DATE", "Expected arrival (order date + lead time)", "2025-02-24"),
            ("received_date", "DATE", "When it actually arrived. Empty = still in transit", "empty"),
        ]),
    ]),
]

COL_W = [122, 82, 400, 178]  # sums to 782 pt (landscape A4 with 30 pt margins)


def build_main_table():
    rows = [[P("Column", head), P("Type", head), P("What it is", head), P("Example", head)]]
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
        bg = ACCESS_BG if group.startswith("ACCESS") else GROUP_BG
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
            for col, typ, desc, example in cols:
                rows.append([P(col, cell_mono), P(typ, cell_type), P(desc, cell), P(example, cell)])
                if "PK" in typ or "FK" in typ:
                    style.append(("BACKGROUND", (1, r), (1, r), KEY_BG))
                r += 1
            style.append(("NOSPLIT", (0, first), (-1, first + 1)))
    t = Table(rows, colWidths=COL_W, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


def build_chain():
    boxes = ["vehicle", "inspection", "defect", "repair", "item"]
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
        ["Date", "Record", "Detail"],
        ["Jan 2024", "Inspection", "42,000 km, defects found"],
        ["Jan 2024", "Defect", "Brakes: worn pads"],
        ["Jan 2024", "Repair", "Pads replaced (2 units), 1.5 h, fixed"],
        ["Aug 2024", "Standalone repair", "Battery failure, replaced (1 unit), 0.5 h"],
        ["Jan 2025", "Inspection", "61,000 km, passed"],
    ]
    rows = [[P(c, head if i == 0 else cell) for c in row] for i, row in enumerate(data)]
    t = Table(rows, colWidths=[80, 130, 350], hAlign="LEFT")
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
        [P("PK", cell_mono), P("Primary key: the unique identifier of each row in the table.", cell)],
        [P("FK", cell_mono), P("Foreign key: a link to a row in another table (e.g. vehicle_id points to a vehicle).", cell)],
        [P("INT / REAL / TEXT / DATE", cell_mono), P("Integer, decimal number, text and date.", cell)],
        [P("empty", cell_mono), P("The field can be left unset (NULL, in database terms).", cell)],
        [P("(1-3)", cell_mono), P("A 1-to-3 scale; the higher number is more critical or severe.", cell)],
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


def build_access_tree():
    lines = [
        "3rd Division            (id 1, parent: none)",
        "  12th Brigade          (id 2, parent: 1)",
        "    34th Battalion      (id 3, parent: 2)   <- app_user \"cmd.34bn\" is scoped here",
        "    35th Battalion      (id 4, parent: 2)",
    ]
    return Table([[P("\n".join(lines), tree)]], colWidths=[780], style=TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("BACKGROUND", (0, 0), (-1, -1), TABLE_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))


def build_access_result():
    data = [
        ["Logged in as", "Visible units", "Sees"],
        ["cmd.34bn (34th Battalion)", "34th Battalion only", "Only its own vehicles, weapons, warehouse and orders"],
        ["cmd.12bde (12th Brigade)", "12th Brigade + 34th Bn + 35th Bn", "Its own data, plus both battalions' combined"],
        ["cmd.3div (3rd Division)", "Everything below it", "The full division, rolled up"],
        ["admin", "All units", "Everything, no filtering"],
    ]
    rows = [[P(c, head if i == 0 else cell) for c in row] for i, row in enumerate(data)]
    t = Table(rows, colWidths=[160, 220, 400], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRID),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(30, 18, "Layer 1 - Data schema - Military logistics portfolio project (fictional)")
    canvas.drawRightString(landscape(A4)[0] - 30, 18, "Page %d" % doc.page)
    canvas.restoreState()


def main():
    doc = SimpleDocTemplate(
        OUT, pagesize=landscape(A4),
        leftMargin=30, rightMargin=30, topMargin=28, bottomMargin=34,
        title="Layer 1 - Data schema", author="Claude",
    )
    story = [
        Paragraph("Layer 1: data schema", title),
        Spacer(1, 4),
        Paragraph(
            "Portfolio project: a fictional but functional military logistics tool. This layer is the foundation, "
            "no ML yet: structure, access control, vehicles with their inspection/repair history, weapons, "
            "ammunition, and stock.",
            subtitle),
        Spacer(1, 10),
        Paragraph("How to read the tables", h2),
        build_legend(),
        Spacer(1, 12),
        Paragraph("1. The tables, column by column", h2),
        build_main_table(),
        Spacer(1, 14),
        KeepTogether([
            Paragraph("2. How a vehicle's records connect", h2),
            Paragraph(
                "Each vehicle has many inspections, each inspection can have several defects, and each defect is fixed "
                "by one or more repairs that use an item from the catalog. Breakdowns between inspections are standalone "
                "repairs (no defect attached).",
                body),
            Spacer(1, 6),
            build_chain(),
            Spacer(1, 6),
            Paragraph(
                "Every repair that uses a part creates a <b>movement</b> of type consumption, which is how the vehicle "
                "data and the stock data stay linked.",
                body),
        ]),
        Spacer(1, 12),
        KeepTogether([
            Paragraph("3. Example: one vehicle's history", h2),
            build_example(),
            Spacer(1, 6),
            Paragraph(
                "Each inspection, together with the vehicle's state at that moment, is a training example. The repairs "
                "that follow are the answer the model has to learn to predict: which part gets replaced, and when.",
                body),
        ]),
        Spacer(1, 12),
        KeepTogether([
            Paragraph("4. On-hand stock: no table for it", h2),
            Paragraph(
                "The stock of each item at each warehouse is calculated by summing <b>movements</b>. That way it never "
                "drifts out of sync with the movement log, and stock can be reconstructed for any past date, which is "
                "exactly what the model needs for training. It will be exposed as a database view.",
                body),
        ]),
        Spacer(1, 14),
        KeepTogether([
            Paragraph("5. Access control: who sees what", h2),
            Paragraph(
                "This falls out of the <b>unit</b> hierarchy already in the schema (parent_unit_id). Each app_user is "
                "scoped to one unit. The set of \"visible units\" for that user is the unit itself plus every unit "
                "below it in the tree, computed by walking parent_unit_id downward. Every table that carries a "
                "unit_id (vehicle, weapon) or belongs to a warehouse tied to a unit gets filtered to that set before "
                "being shown.",
                body),
            Spacer(1, 8),
            build_access_tree(),
            Spacer(1, 8),
            build_access_result(),
            Spacer(1, 6),
            Paragraph(
                "This is authorization, not authentication: for a portfolio demo, a simple \"log in as...\" selector "
                "is enough, since there is no need for real passwords. The filtering logic is what matters and what "
                "a recruiter would actually look at.",
                body),
        ]),
    ]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


main()
