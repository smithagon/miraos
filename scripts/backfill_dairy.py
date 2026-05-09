"""
Seed the dairy demo schema into Postgres with a large time-series mock dataset.

Docker Compose Postgres (service `postgres`, container `dairy_test_db`):

  From your Mac / host (published port 5432):
    postgresql://dairy_user:dairy_pass@localhost:5432/dairy_db

  From another container on the same Compose network (use service name as host):
    postgresql://dairy_user:dairy_pass@postgres:5432/dairy_db

Environment (optional overrides):
  DATABASE_URL or DB_URL — full URL; if set, other POSTGRES_* vars are ignored
  POSTGRES_HOST — default localhost (use `postgres` when running inside Docker)
  POSTGRES_PORT — default 5432
  POSTGRES_USER — default dairy_user
  POSTGRES_PASSWORD — default dairy_pass
  POSTGRES_DB — default dairy_db

Scale (optional — reduce if seeding is slow):
  DAIRY_NUM_FARMS — default 12
  DAIRY_CATTLE_PER_FARM — default 18
  DAIRY_DAYS_HISTORY — default 730 (~2 years of daily rows)
  DAIRY_SALES_PER_FARM_DAY — default 3 (rows per farm per calendar day)
  DAIRY_RANDOM_SEED — default 42 (set empty to randomize each run)

Rough row counts (defaults): farms=12, cattle≈216, milk_production≈157k, sales≈26k.

Farm owners are reused: consecutive farm indices share the same owner so queries like
"all farms for Maria Garcia" can return multiple locations.

Run (example, from repo root with backend venv that has sqlalchemy + psycopg2):
  pip install -r fastapi-backend/requirements.txt
  docker compose up -d postgres   # if not already running
  python scripts/backfill_dairy.py
"""
from __future__ import annotations

import datetime
import math
import os
import random
from typing import List

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# --- Postgres connection (matches docker-compose.yml `postgres` service) ---
_DB_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
if _DB_URL:
    DB_URL = _DB_URL
else:
    _user = os.getenv("POSTGRES_USER", "dairy_user")
    _password = os.getenv("POSTGRES_PASSWORD", "dairy_pass")
    _host = os.getenv("POSTGRES_HOST", "localhost")
    _port = os.getenv("POSTGRES_PORT", "5432")
    _db = os.getenv("POSTGRES_DB", "dairy_db")
    DB_URL = f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}"

# --- Dataset scale ---
NUM_FARMS = max(1, int(os.getenv("DAIRY_NUM_FARMS", "12")))
CATTLE_PER_FARM = max(1, int(os.getenv("DAIRY_CATTLE_PER_FARM", "18")))
DAYS_HISTORY = max(1, int(os.getenv("DAIRY_DAYS_HISTORY", "730")))
SALES_PER_FARM_DAY = max(0, int(os.getenv("DAIRY_SALES_PER_FARM_DAY", "3")))
COMMIT_BATCH = max(500, int(os.getenv("DAIRY_COMMIT_BATCH", "2500")))
_seed_raw = os.getenv("DAIRY_RANDOM_SEED", "42")
if _seed_raw.strip():
    random.seed(int(_seed_raw))

engine = create_engine(DB_URL)
Base = declarative_base()


class Farm(Base):
    __tablename__ = "farms"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)
    owner = Column(String)


class Cattle(Base):
    __tablename__ = "cattle"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    breed = Column(String)
    age = Column(Integer)
    health_status = Column(String)


class MilkProduction(Base):
    __tablename__ = "milk_production"
    id = Column(Integer, primary_key=True)
    cattle_id = Column(Integer, ForeignKey("cattle.id"))
    date = Column(DateTime)
    quantity_liters = Column(Float)
    fat_content = Column(Float)


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey("farms.id"))
    date = Column(DateTime)
    quantity_liters = Column(Float)
    price_per_liter = Column(Float)
    customer_name = Column(String)


FARM_BLUEPRINTS: List[tuple[str, str, str]] = [
    ("Green Pastures", "Wisconsin", "John Doe"),
    ("Sunny Meadows", "Vermont", "Jane Smith"),
    ("Highland Dairy", "Colorado", "Bob Brown"),
    ("Riverbend Holsteins", "New York", "Maria Garcia"),
    ("Cedar Ridge Creamery", "Pennsylvania", "David Chen"),
    ("Oak Valley Farm", "Ohio", "Sarah Johnson"),
    ("Prairie Star Dairy", "Kansas", "Michael O'Neil"),
    ("Bluebell Organics", "Oregon", "Emily Nakamura"),
    ("Summit Peak Ranch", "Montana", "James Wilson"),
    ("Willow Creek Dairy", "Minnesota", "Priya Patel"),
    ("Golden Hour Farm", "California", "Carlos Mendez"),
    ("Northwind Cooperative", "Maine", "Anna Kowalski"),
    ("Red Barn Ayrshires", "Iowa", "Tom Hansen"),
    ("Misty Morning Milk", "Washington", "Lisa Park"),
    ("Eagle Ridge Jerseys", "Idaho", "Robert Taylor"),
]

# Owners deliberately reused across farms (each name typically runs 2+ locations).
MULTI_FARM_OWNERS: List[str] = [
    "John Doe",
    "Maria Garcia",
    "Priya Patel",
    "Michael O'Neil",
    "Emily Nakamura",
    "David Chen",
]

BREEDS = ["Holstein", "Jersey", "Guernsey", "Ayrshire", "Brown Swiss"]
HEALTH_STATUSES = ["Healthy", "Healthy", "Healthy", "Under Observation", "Quarantine Clear"]
CUSTOMERS = [
    "Local Coop",
    "Global Dairy Inc",
    "Fresh Mart",
    "Metro Grocers",
    "School District Nutrition",
    "Artisan Cheese Works",
    "Export Packers Ltd",
    "Regional Bottling Co",
    "Hospital Supply Chain",
    "Farmers Market Collective",
]


def _seasonal_liters(day_offset: int, cattle_age: int, breed: str) -> float:
    """day_offset: 0 = oldest day in range; adds yearly seasonality + breed/age bias."""
    day_of_year = day_offset % 365
    seasonal = 4.2 * math.sin(2 * math.pi * day_of_year / 365.0)
    weekly = 1.1 * math.sin(2 * math.pi * (day_offset % 7) / 7.0)
    age_factor = 1.0 - max(0, cattle_age - 6) * 0.04
    breed_base = {"Holstein": 32.0, "Jersey": 26.0, "Guernsey": 27.5, "Ayrshire": 28.0, "Brown Swiss": 29.0}.get(
        breed, 29.0
    )
    noise = random.gauss(0, 2.1)
    return max(6.0, breed_base * max(0.55, age_factor) + seasonal + weekly + noise)


def _fat_percent(breed: str) -> float:
    base = {"Jersey": 4.85, "Guernsey": 4.35, "Brown Swiss": 4.05, "Ayrshire": 3.95, "Holstein": 3.75}.get(
        breed, 3.9
    )
    return max(3.0, min(5.5, base + random.gauss(0, 0.12)))


def _sale_timestamp(day: datetime.datetime) -> datetime.datetime:
    h = random.randint(5, 21)
    m = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
    return day.replace(hour=h, minute=m, second=random.randint(0, 59), microsecond=0)


def _flush(session, buf: list) -> None:
    if not buf:
        return
    session.add_all(buf)
    session.commit()
    buf.clear()


def backfill() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    farm_specs: List[tuple[str, str, str]] = []
    for i in range(NUM_FARMS):
        n, loc, _ = FARM_BLUEPRINTS[i % len(FARM_BLUEPRINTS)]
        # Pair consecutive farms under the same owner so NL2SQL demos can ask
        # "farms owned by X" and return multiple rows.
        owner = MULTI_FARM_OWNERS[(i // 2) % len(MULTI_FARM_OWNERS)]
        farm_specs.append((n, loc, owner))
    farms = [Farm(name=n, location=loc, owner=own) for n, loc, own in farm_specs]
    session.add_all(farms)
    session.commit()

    cattle_list: list[Cattle] = []
    for farm in farms:
        for _ in range(CATTLE_PER_FARM):
            cattle_list.append(
                Cattle(
                    farm_id=farm.id,
                    breed=random.choice(BREEDS),
                    age=random.randint(2, 11),
                    health_status=random.choice(HEALTH_STATUSES),
                )
            )
    session.add_all(cattle_list)
    session.commit()

    end_day = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    milk_buf: list[MilkProduction] = []
    sale_buf: list[Sale] = []

    for d in range(DAYS_HISTORY):
        day_midnight = end_day - datetime.timedelta(days=d)
        day_offset = DAYS_HISTORY - 1 - d

        for cow in cattle_list:
            milk_buf.append(
                MilkProduction(
                    cattle_id=cow.id,
                    date=day_midnight + datetime.timedelta(hours=random.randint(5, 11), minutes=random.randint(0, 59)),
                    quantity_liters=round(_seasonal_liters(day_offset, cow.age, cow.breed), 2),
                    fat_content=round(_fat_percent(cow.breed), 2),
                )
            )
            if len(milk_buf) >= COMMIT_BATCH:
                _flush(session, milk_buf)

        for farm in farms:
            for _ in range(SALES_PER_FARM_DAY):
                sale_buf.append(
                    Sale(
                        farm_id=farm.id,
                        date=_sale_timestamp(day_midnight),
                        quantity_liters=round(random.uniform(120.0, 980.0), 2),
                        price_per_liter=round(random.uniform(0.48, 1.05), 3),
                        customer_name=random.choice(CUSTOMERS),
                    )
                )
                if len(sale_buf) >= COMMIT_BATCH:
                    _flush(session, sale_buf)

    _flush(session, milk_buf)
    _flush(session, sale_buf)

    n_milk = session.query(MilkProduction).count()
    n_sales = session.query(Sale).count()
    print("Backfilling completed successfully!")
    print(
        f"  farms={NUM_FARMS}, cattle={len(cattle_list)}, days={DAYS_HISTORY}, "
        f"milk_production={n_milk}, sales={n_sales}"
    )


if __name__ == "__main__":
    backfill()
