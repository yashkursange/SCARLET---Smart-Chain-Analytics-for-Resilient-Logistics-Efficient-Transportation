import pandas as pd
import datetime
from app.ml.forecast_service import ForecastService
from app.ml.data_loader import get_engine

def get_inventory():
    engine = get_engine()
    query = """
    SELECT m.id as market_id, i.product_id, i.available_quantity as current_inventory
    FROM inventory i
    JOIN markets m ON i.node_id = m.node_id
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn.connection)
    return df

def get_inbound_supply():
    engine = get_engine()
    query = """
    SELECT m.id as market_id, oi.product_id, CAST(s.expected_arrival_time AS DATE) as arrival_date, SUM(si.quantity) as expected_inbound
    FROM shipments s
    JOIN routes r ON s.route_id = r.id
    JOIN markets m ON r.destination_node_id = m.node_id
    JOIN shipment_items si ON si.shipment_id = s.id
    JOIN order_items oi ON si.order_item_id = oi.id
    WHERE s.status != 'DELIVERED'
    GROUP BY m.id, oi.product_id, CAST(s.expected_arrival_time AS DATE)
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn.connection)
        
    if not df.empty:
        df['arrival_date'] = pd.to_datetime(df['arrival_date'])
    return df

def determine_risk_level(days_until_stockout):
    if days_until_stockout is None:
        return 'LOW'
    if days_until_stockout <= 3:
        return 'CRITICAL'
    if days_until_stockout <= 7:
        return 'HIGH'
    if days_until_stockout <= 14:
        return 'MEDIUM'
    return 'LOW'

def analyze_risk(horizon=7):
    # Get forecasts
    fs = ForecastService()
    forecast_df = fs.get_forecast(horizon_days=horizon)
    
    if forecast_df.empty:
        return []
        
    # Get inventory and inbound supply
    inventory_df = get_inventory()
    inbound_df = get_inbound_supply()
    
    # Merge
    forecast_df['forecast_date'] = pd.to_datetime(forecast_df['forecast_date']).dt.normalize()
    if not inbound_df.empty:
        inbound_df['arrival_date'] = pd.to_datetime(inbound_df['arrival_date']).dt.normalize()
        
    results = []
    
    # Process each market-product separately
    groups = forecast_df.groupby(['market_id', 'product_id'])
    for (market_id, product_id), group in groups:
        group = group.sort_values('forecast_date')
        
        # Get starting inventory
        inv_match = inventory_df[(inventory_df['market_id'] == market_id) & (inventory_df['product_id'] == product_id)]
        current_inv = inv_match['current_inventory'].iloc[0] if not inv_match.empty else 0
        
        # Get inbound shipments
        if not inbound_df.empty:
            inbound = inbound_df[(inbound_df['market_id'] == market_id) & (inbound_df['product_id'] == product_id)]
        else:
            inbound = pd.DataFrame()
            
        proj_inv = current_inv
        stockout_date = None
        shortage_qty = 0
        days_until_stockout = None
        
        for i, row in group.iterrows():
            date = row['forecast_date']
            demand = row['predicted_demand']
            
            # Add inbound if any arrives today
            inbound_today = 0
            if not inbound.empty:
                match = inbound[inbound['arrival_date'] == date]
                if not match.empty:
                    inbound_today = match['expected_inbound'].sum()
                    
            proj_inv = proj_inv - demand + inbound_today
            
            if proj_inv < 0 and stockout_date is None:
                stockout_date = date
                shortage_qty = abs(proj_inv)
                days_until_stockout = (date.tz_localize(None) - pd.Timestamp.now().normalize()).days
                
        total_demand = group['predicted_demand'].sum()
        risk_level = determine_risk_level(days_until_stockout)
        
        total_inbound = inbound['expected_inbound'].sum() if not inbound.empty else 0
        
        results.append({
            'market_id': market_id,
            'product_id': product_id,
            'forecast_horizon': horizon,
            'total_forecast_demand': total_demand,
            'current_inventory': current_inv,
            'projected_ending_inventory': proj_inv,
            'expected_inbound': total_inbound,
            'shortage_quantity': shortage_qty,
            'stockout_date': str(stockout_date.date()) if stockout_date else None,
            'risk_level': risk_level
        })
        
    return results
