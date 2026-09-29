-- =========================================================
-- Military logistics portfolio project (fictional data)
-- Layer 1 schema -- SQLite
--
-- Dates are stored as TEXT in ISO-8601 format ('YYYY-MM-DD'),
-- since SQLite has no native DATE type.
-- =========================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------
-- STRUCTURE -- who and where
-- ---------------------------------------------------------

CREATE TABLE unit (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL
                      CHECK (type IN ('division','brigade','battalion','company')),
    parent_unit_id  INTEGER REFERENCES unit(id),
    terrain_type    TEXT
                      CHECK (terrain_type IN ('desert','coastal','mountain','temperate'))
);

CREATE TABLE warehouse (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    unit_id  INTEGER REFERENCES unit(id)   -- NULL = central depot, not owned by one unit
);

CREATE TABLE item (
    id                INTEGER PRIMARY KEY,
    code              TEXT NOT NULL UNIQUE,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL
                        CHECK (type IN ('spare_part','consumable','serial_equipment')),
    category          TEXT NOT NULL,
    criticality       INTEGER NOT NULL CHECK (criticality BETWEEN 1 AND 3),
    lead_time_days    INTEGER NOT NULL,
    unit_of_measure   TEXT NOT NULL
                        CHECK (unit_of_measure IN ('each','liter','round','box'))
);

-- ---------------------------------------------------------
-- ACCESS -- who can see what
-- ---------------------------------------------------------

CREATE TABLE app_user (
    id         INTEGER PRIMARY KEY,
    username   TEXT NOT NULL UNIQUE,
    full_name  TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('admin','unit')),
    unit_id    INTEGER REFERENCES unit(id)   -- required if role = 'unit', NULL if 'admin'
);

-- ---------------------------------------------------------
-- VEHICLES -- the history
-- ---------------------------------------------------------

CREATE TABLE vehicle (
    id               INTEGER PRIMARY KEY,
    serial_number    TEXT NOT NULL UNIQUE,
    model            TEXT NOT NULL,
    category         TEXT,
    unit_id          INTEGER NOT NULL REFERENCES unit(id),
    status           TEXT NOT NULL
                       CHECK (status IN ('active','in_repair','decommissioned')),
    mileage_km       INTEGER NOT NULL DEFAULT 0,
    in_service_date  TEXT NOT NULL
);

CREATE TABLE inspection (
    id          INTEGER PRIMARY KEY,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicle(id),
    date        TEXT NOT NULL,
    mileage_km  INTEGER NOT NULL,
    result      TEXT NOT NULL CHECK (result IN ('passed','defects_found'))
);

CREATE TABLE defect (
    id             INTEGER PRIMARY KEY,
    inspection_id  INTEGER NOT NULL REFERENCES inspection(id),
    system         TEXT NOT NULL
                     CHECK (system IN ('brakes','lights','tires','engine',
                                        'transmission','suspension',
                                        'electrical','steering')),
    severity       INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 3),
    description    TEXT
);

CREATE TABLE repair (
    id           INTEGER PRIMARY KEY,
    vehicle_id   INTEGER NOT NULL REFERENCES vehicle(id),
    defect_id    INTEGER REFERENCES defect(id),      -- NULL = standalone breakdown
    date         TEXT NOT NULL,
    type         TEXT NOT NULL
                   CHECK (type IN ('part_replacement','adjustment','repair')),
    item_id      INTEGER REFERENCES item(id),        -- NULL if no part was used
    quantity     INTEGER,
    labor_hours  REAL,
    outcome      TEXT NOT NULL CHECK (outcome IN ('fixed','recurred'))
);

-- ---------------------------------------------------------
-- EXERCISES -- what drives consumption
-- ---------------------------------------------------------

CREATE TABLE training_exercise (
    id          INTEGER PRIMARY KEY,
    unit_id     INTEGER NOT NULL REFERENCES unit(id),
    name        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN ('live_fire','field_exercise','drill')),
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL
);

-- ---------------------------------------------------------
-- WEAPONS -- serialized equipment
-- ---------------------------------------------------------

CREATE TABLE weapon (
    id                    INTEGER PRIMARY KEY,
    serial_number         TEXT NOT NULL UNIQUE,
    type                  TEXT NOT NULL,
    caliber               TEXT NOT NULL,
    unit_id               INTEGER NOT NULL REFERENCES unit(id),
    status                TEXT NOT NULL
                            CHECK (status IN ('active','in_repair','decommissioned')),
    last_inspection_date  TEXT
);

CREATE TABLE range_session (
    id           INTEGER PRIMARY KEY,
    weapon_id    INTEGER NOT NULL REFERENCES weapon(id),
    exercise_id  INTEGER REFERENCES training_exercise(id),   -- NULL = routine range day
    date         TEXT NOT NULL
);

-- ---------------------------------------------------------
-- AMMUNITION -- lot-tracked consumable
-- ---------------------------------------------------------

CREATE TABLE ammo_lot (
    id                INTEGER PRIMARY KEY,
    item_id           INTEGER NOT NULL REFERENCES item(id),
    lot_number        TEXT NOT NULL,
    manufacture_date  TEXT NOT NULL,
    expiry_date       TEXT NOT NULL
);

-- ---------------------------------------------------------
-- STOCK -- what exists and what should exist
-- ---------------------------------------------------------

CREATE TABLE allowance (
    warehouse_id    INTEGER NOT NULL REFERENCES warehouse(id),
    item_id         INTEGER NOT NULL REFERENCES item(id),
    authorized_qty  INTEGER NOT NULL,
    minimum_qty     INTEGER NOT NULL,
    PRIMARY KEY (warehouse_id, item_id)
);

CREATE TABLE movement (
    id                 INTEGER PRIMARY KEY,
    date               TEXT NOT NULL,
    warehouse_id       INTEGER NOT NULL REFERENCES warehouse(id),
    item_id            INTEGER NOT NULL REFERENCES item(id),
    type               TEXT NOT NULL
                         CHECK (type IN ('receipt','issue','consumption',
                                          'transfer','adjustment')),
    quantity           INTEGER NOT NULL,
    dest_warehouse_id  INTEGER REFERENCES warehouse(id),          -- transfers only
    repair_id          INTEGER REFERENCES repair(id),             -- if caused by a repair
    lot_id             INTEGER REFERENCES ammo_lot(id),           -- if item is lot-tracked
    exercise_id        INTEGER REFERENCES training_exercise(id)   -- if caused by an exercise
);

CREATE TABLE purchase_order (
    id             INTEGER PRIMARY KEY,
    warehouse_id   INTEGER NOT NULL REFERENCES warehouse(id),
    item_id        INTEGER NOT NULL REFERENCES item(id),
    quantity       INTEGER NOT NULL,
    order_date     TEXT NOT NULL,
    expected_date  TEXT NOT NULL,
    received_date  TEXT     -- NULL = still in transit
);

-- ---------------------------------------------------------
-- NEEDS -- the requirements document, with human review
-- ---------------------------------------------------------

CREATE TABLE requirement_line (
    id                INTEGER PRIMARY KEY,
    warehouse_id      INTEGER NOT NULL REFERENCES warehouse(id),
    item_id           INTEGER NOT NULL REFERENCES item(id),
    created_date      TEXT NOT NULL,
    computed_gap_qty  INTEGER NOT NULL,
    reason            TEXT NOT NULL
                        CHECK (reason IN ('below_minimum','forecasted_demand','manual_request')),
    status            TEXT NOT NULL DEFAULT 'proposed'
                        CHECK (status IN ('proposed','approved','edited','rejected')),
    reviewed_by       INTEGER REFERENCES app_user(id),
    reviewed_date     TEXT,
    final_qty         INTEGER,
    notes             TEXT,
    order_id          INTEGER REFERENCES purchase_order(id)   -- set once approved and ordered
);

-- ---------------------------------------------------------
-- Extra signal for the ML models
-- ---------------------------------------------------------

CREATE TABLE weather_reading (
    id                INTEGER PRIMARY KEY,
    unit_id           INTEGER NOT NULL REFERENCES unit(id),
    date              TEXT NOT NULL,
    temperature_c     REAL NOT NULL,
    precipitation_mm  REAL NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------
-- Evaluation only -- NOT part of the "real" operational data.
-- Records where a synthetic anomaly was planted, so the
-- anomaly-detection model can be scored with real
-- precision/recall instead of guesswork.
-- ---------------------------------------------------------

CREATE TABLE synthetic_anomaly_log (
    id            INTEGER PRIMARY KEY,
    table_name    TEXT NOT NULL,
    row_id        INTEGER NOT NULL,
    anomaly_type  TEXT NOT NULL,
    notes         TEXT
);

-- ---------------------------------------------------------
-- Views
-- ---------------------------------------------------------

-- On-hand stock is never stored directly -- it is always derived
-- from `movement`, so it can never drift out of sync and can be
-- reconstructed for any past date by filtering on `date`.
CREATE VIEW stock_on_hand AS
WITH moves AS (
    -- every movement's effect at its own warehouse
    -- (a transfer is negative here: it leaves the source warehouse)
    SELECT warehouse_id, item_id,
           CASE type
               WHEN 'receipt'    THEN  quantity
               WHEN 'adjustment' THEN  quantity
               ELSE                   -quantity
           END AS signed_qty
    FROM movement

    UNION ALL

    -- a transfer's effect at the destination warehouse
    SELECT dest_warehouse_id AS warehouse_id, item_id, quantity AS signed_qty
    FROM movement
    WHERE type = 'transfer' AND dest_warehouse_id IS NOT NULL
)
SELECT warehouse_id, item_id, SUM(signed_qty) AS on_hand_qty
FROM moves
GROUP BY warehouse_id, item_id;
