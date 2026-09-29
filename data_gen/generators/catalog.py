ITEMS = [
    # code, name, type, category, criticality, lead_time_days, unit_of_measure
    ("SP-BRK-01", "Brake Pad Set", "spare_part", "brakes", 2, 21, "each"),
    ("SP-BRK-02", "Brake Disc", "spare_part", "brakes", 2, 28, "each"),
    ("SP-LGT-01", "Headlight Assembly", "spare_part", "lights", 1, 21, "each"),
    ("SP-LGT-02", "Signal Lamp Unit", "spare_part", "lights", 1, 14, "each"),
    ("SP-TIR-01", "Standard Road Tire", "spare_part", "tires", 2, 30, "each"),
    ("SP-TIR-02", "All-Terrain Tire", "spare_part", "tires", 2, 35, "each"),
    ("SP-ENG-01", "Engine Air Filter", "spare_part", "engine", 1, 14, "each"),
    ("SP-ENG-02", "Fuel Injector", "spare_part", "engine", 3, 45, "each"),
    ("SP-ENG-03", "Timing Belt", "spare_part", "engine", 2, 30, "each"),
    ("SP-TRN-01", "Clutch Kit", "spare_part", "transmission", 2, 40, "each"),
    ("SP-TRN-02", "Gearbox Seal Set", "spare_part", "transmission", 1, 25, "each"),
    ("SP-SUS-01", "Shock Absorber", "spare_part", "suspension", 2, 28, "each"),
    ("SP-SUS-02", "Leaf Spring", "spare_part", "suspension", 2, 35, "each"),
    ("SP-ELE-01", "Alternator", "spare_part", "electrical", 3, 45, "each"),
    ("SP-ELE-02", "Battery Terminal Kit", "spare_part", "electrical", 1, 14, "each"),
    ("SP-ELE-03", "Wiring Harness Section", "spare_part", "electrical", 2, 40, "each"),
    ("SP-STE-01", "Steering Rack", "spare_part", "steering", 3, 50, "each"),
    ("SP-STE-02", "Tie Rod End", "spare_part", "steering", 2, 21, "each"),
    ("CO-FUE-01", "Diesel Fuel", "consumable", "fuel", 3, 7, "liter"),
    ("CO-FUE-02", "Gasoline", "consumable", "fuel", 2, 7, "liter"),
    ("CO-LUB-01", "Engine Oil", "consumable", "lubricant", 2, 14, "liter"),
    ("CO-LUB-02", "Hydraulic Fluid", "consumable", "lubricant", 2, 14, "liter"),
    ("CO-MED-01", "Field Dressing Kit", "consumable", "medical", 3, 10, "box"),
    ("CO-MED-02", "IV Fluid Bag", "consumable", "medical", 3, 14, "each"),
    ("CO-RAT-01", "Field Ration Pack", "consumable", "rations", 2, 10, "box"),
    ("CO-AMM-01", "5.56mm Ball Ammunition", "consumable", "ammunition", 3, 21, "round"),
    ("CO-AMM-02", "7.62mm Ball Ammunition", "consumable", "ammunition", 3, 21, "round"),
    ("CO-AMM-03", "9mm Ball Ammunition", "consumable", "ammunition", 2, 14, "round"),
    ("CO-AMM-04", "12.7mm Ammunition", "consumable", "ammunition", 2, 30, "round"),
    ("CO-AMM-05", "40mm HE Grenade", "consumable", "ammunition", 3, 35, "each"),
    ("SE-RAD-01", "Tactical Radio Unit", "serial_equipment", "comms", 2, 60, "each"),
    ("SE-OPT-01", "Night Vision Goggles", "serial_equipment", "optics", 2, 75, "each"),
    ("SE-OPT-02", "Rifle Optic Sight", "serial_equipment", "optics", 1, 45, "each"),
    ("SE-ARM-01", "Body Armor Set", "serial_equipment", "protection", 3, 60, "each"),
    ("SE-NAV-01", "GPS Navigation Unit", "serial_equipment", "navigation", 1, 40, "each"),
]

# maps a weapon caliber to the ammunition item code that feeds it
CALIBER_TO_AMMO_CODE = {
    "5.56x45mm": "CO-AMM-01",
    "7.62x51mm": "CO-AMM-02",
    "9x19mm": "CO-AMM-03",
    "12.7x99mm": "CO-AMM-04",
    "40mm": "CO-AMM-05",
}


def generate(conn):
    items = []
    for code, name, itype, category, criticality, lead_time, uom in ITEMS:
        cur = conn.execute(
            "INSERT INTO item (code, name, type, category, criticality, "
            "lead_time_days, unit_of_measure) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, name, itype, category, criticality, lead_time, uom),
        )
        items.append(
            {
                "id": cur.lastrowid,
                "code": code,
                "name": name,
                "type": itype,
                "category": category,
                "criticality": criticality,
                "lead_time_days": lead_time,
                "unit_of_measure": uom,
            }
        )

    by_code = {i["code"]: i for i in items}
    spare_parts_by_category = {}
    for i in items:
        if i["type"] == "spare_part":
            spare_parts_by_category.setdefault(i["category"], []).append(i)

    ammo_by_caliber = {
        caliber: by_code[code] for caliber, code in CALIBER_TO_AMMO_CODE.items()
    }

    return {
        "items": items,
        "by_code": by_code,
        "spare_parts_by_category": spare_parts_by_category,
        "ammo_by_caliber": ammo_by_caliber,
        "fuel_item": by_code["CO-FUE-01"],
        "ration_item": by_code["CO-RAT-01"],
    }
