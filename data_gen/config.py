from datetime import date

SEED = 20260930

TODAY = date(2026, 9, 30)
HISTORY_YEARS = 3
START_DATE = date(TODAY.year - HISTORY_YEARS, TODAY.month, TODAY.day)
FLEET_START_DATE = date(TODAY.year - 10, TODAY.month, TODAY.day)

DB_PATH = "db/proto_phoros.db"
SCHEMA_PATH = "db/schema.sql"

N_BRIGADES = 3
N_BATTALIONS_PER_BRIGADE = 3
N_COMPANIES_PER_BATTALION = 2

VEHICLES_PER_BATTALION = 20
WEAPONS_PER_COMPANY = 25

BRIGADE_TERRAIN = ["desert", "coastal", "mountain"]
