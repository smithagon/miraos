"""
Seed the dairy demo schema into Postgres.

Docker Compose Postgres (service `postgres`, container `dairy_test_db`):

  From your Mac / host (published port 5432):
    postgresql://dairy_user:dairy_pass@localhost:5432/dairy_db

  From another container on the same Compose network (use service name as host):
    postgresql://dairy_user:dairy_pass@postgres:5432/dairy_db

  libpq-style URI (either form works with SQLAlchemy):
    Same as above — also set sslmode=disable if your client defaults to SSL.

Environment (optional overrides):
  DATABASE_URL or DB_URL — full URL; if set, other POSTGRES_* vars are ignored
  POSTGRES_HOST — default localhost (use `postgres` when running inside Docker)
  POSTGRES_PORT — default 5432
  POSTGRES_USER — default dairy_user
  POSTGRES_PASSWORD — default dairy_pass
  POSTGRES_DB — default dairy_db

Run (example, from repo root with backend venv that has sqlalchemy + psycopg2):
  pip install -r fastapi-backend/requirements.txt
  docker compose up -d postgres   # if not already running
  python scripts/backfill_dairy.py
"""
import datetime
import os
import random

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

engine = create_engine(DB_URL)
Base = declarative_base()


# Models
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


def backfill():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Create Farms
    farms = [
        Farm(name="Green Pastures", location="Wisconsin", owner="John Doe"),
        Farm(name="Sunny Meadows", location="Vermont", owner="Jane Smith"),
        Farm(name="Highland Dairy", location="Colorado", owner="Bob Brown"),
    ]
    session.add_all(farms)
    session.commit()

    # 2. Create Cattle
    breeds = ["Holstein", "Jersey", "Guernsey", "Ayrshire"]
    health_statuses = ["Healthy", "Healthy", "Healthy", "Under Observation"]

    cattle_list = []
    for farm in farms:
        for _ in range(10):  # 10 cows per farm
            c = Cattle(
                farm_id=farm.id,
                breed=random.choice(breeds),
                age=random.randint(2, 10),
                health_status=random.choice(health_statuses),
            )
            cattle_list.append(c)
    session.add_all(cattle_list)
    session.commit()

    # 3. Create Production & Sales (last 30 days)
    for i in range(30):
        date = datetime.datetime.now() - datetime.timedelta(days=i)

        # Production
        for cow in cattle_list:
            p = MilkProduction(
                cattle_id=cow.id,
                date=date,
                quantity_liters=random.uniform(20.0, 40.0),
                fat_content=random.uniform(3.5, 4.5),
            )
            session.add(p)

        # Sales
        for farm in farms:
            s = Sale(
                farm_id=farm.id,
                date=date,
                quantity_liters=random.uniform(200.0, 400.0),
                price_per_liter=random.uniform(0.5, 0.8),
                customer_name=random.choice(["Local Coop", "Global Dairy", "Fresh Mart"]),
            )
            session.add(s)

    session.commit()
    print("Backfilling completed successfully!")


if __name__ == "__main__":
    backfill()
