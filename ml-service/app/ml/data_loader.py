import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.engine import URL

def get_engine():
    user = os.environ.get("DB_USER", "scarlet_user")
    password = os.environ.get("DB_PASSWORD", "@Yashop123")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "scarlet")
    
    url = URL.create(
        drivername="postgresql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=db_name
    )
    return create_engine(url)

def load_data():
    engine = get_engine()
    
    query = """
    SELECT d.id, d.market_id, d.product_id, d.period_start AS demand_date, d.demand_quantity AS actual_quantity,
           m.node_id as market_name, 'Region' as region,
           p.name as product_name, 'Category' as category
    FROM demand d
    JOIN markets m ON d.market_id = m.id
    JOIN products p ON d.product_id = p.id
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    # Ensure correct types
    df['demand_date'] = pd.to_datetime(df['demand_date'])
    df['actual_quantity'] = pd.to_numeric(df['actual_quantity'])
    
    # Sort observations chronologically
    df = df.sort_values(by=['market_id', 'product_id', 'demand_date']).reset_index(drop=True)
    
    return df
