import datetime
import random
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker

import os
# Database connection
DB_URL = os.getenv("DB_URL", "postgresql://dairy_user:dairy_pass@localhost:5432/dairy_db")
engine = create_engine(DB_URL)
Base = declarative_base()

# Models
class Farm(Base):
    __tablename__ = 'farms'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)
    owner = Column(String)

class Cattle(Base):
    __tablename__ = 'cattle'
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey('farms.id'))
    breed = Column(String)
    age = Column(Integer)
    health_status = Column(String)

class MilkProduction(Base):
    __tablename__ = 'milk_production'
    id = Column(Integer, primary_key=True)
    cattle_id = Column(Integer, ForeignKey('cattle.id'))
    date = Column(DateTime)
    quantity_liters = Column(Float)
    fat_content = Column(Float)

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    farm_id = Column(Integer, ForeignKey('farms.id'))
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
        Farm(name="Highland Dairy", location="Colorado", owner="Bob Brown")
    ]
    session.add_all(farms)
    session.commit()

    # 2. Create Cattle
    breeds = ["Holstein", "Jersey", "Guernsey", "Ayrshire"]
    health_statuses = ["Healthy", "Healthy", "Healthy", "Under Observation"]
    
    cattle_list = []
    for farm in farms:
        for _ in range(10): # 10 cows per farm
            c = Cattle(
                farm_id=farm.id,
                breed=random.choice(breeds),
                age=random.randint(2, 10),
                health_status=random.choice(health_statuses)
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
                fat_content=random.uniform(3.5, 4.5)
            )
            session.add(p)
        
        # Sales
        for farm in farms:
            s = Sale(
                farm_id=farm.id,
                date=date,
                quantity_liters=random.uniform(200.0, 400.0),
                price_per_liter=random.uniform(0.5, 0.8),
                customer_name=random.choice(["Local Coop", "Global Dairy", "Fresh Mart"])
            )
            session.add(s)
            
    session.commit()
    print("Backfilling completed successfully!")

if __name__ == "__main__":
    backfill()
