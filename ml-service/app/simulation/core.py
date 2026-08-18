import random
import datetime
import uuid
import psycopg2
from psycopg2.extras import execute_values
import networkx as nx

def generate_and_load_data(db_kwargs: dict, seed: int = 42):
    random.seed(seed)
    
    conn = psycopg2.connect(**db_kwargs)
    cur = conn.cursor()
    
    # Generate UUIDs
    suppliers = [str(uuid.uuid4()) for _ in range(10)]
    factories = [str(uuid.uuid4()) for _ in range(3)]
    warehouses = [str(uuid.uuid4()) for _ in range(5)]
    markets = [str(uuid.uuid4()) for _ in range(3)]
    products = [str(uuid.uuid4()) for _ in range(10)]
    
    # 1. Clear existing data (if needed, but assuming empty DB)
    cur.execute("TRUNCATE TABLE nodes CASCADE")
    cur.execute("TRUNCATE TABLE products CASCADE")
    
    # 2. Insert Nodes
    nodes_data = []
    supplier_nodes = []
    for s in suppliers:
        nid = str(uuid.uuid4())
        supplier_nodes.append((s, nid))
        nodes_data.append((nid, 'SUPPLIER', f"Supplier_{s[:4]}", "Loc"))
        
    factory_nodes = []
    for f in factories:
        nid = str(uuid.uuid4())
        factory_nodes.append((f, nid))
        nodes_data.append((nid, 'FACTORY', f"Factory_{f[:4]}", "Loc"))
        
    warehouse_nodes = []
    for w in warehouses:
        nid = str(uuid.uuid4())
        warehouse_nodes.append((w, nid))
        nodes_data.append((nid, 'WAREHOUSE', f"Warehouse_{w[:4]}", "Loc"))
        
    market_nodes = []
    for m in markets:
        nid = str(uuid.uuid4())
        market_nodes.append((m, nid))
        nodes_data.append((nid, 'MARKET', f"Market_{m[:4]}", "Loc"))
        
    execute_values(cur, "INSERT INTO nodes (id, type, name, location) VALUES %s", nodes_data)
    
    # Insert specific entity tables
    execute_values(cur, "INSERT INTO suppliers (id, node_id, reliability) VALUES %s", 
                   [(s, nid, round(random.uniform(0.8, 1.0), 2)) for s, nid in supplier_nodes])
                   
    execute_values(cur, "INSERT INTO factories (id, node_id, capacity_per_day) VALUES %s", 
                   [(f, nid, random.randint(100, 500)) for f, nid in factory_nodes])
                   
    execute_values(cur, "INSERT INTO warehouses (id, node_id, total_capacity) VALUES %s", 
                   [(w, nid, random.randint(1000, 5000)) for w, nid in warehouse_nodes])
                   
    execute_values(cur, "INSERT INTO markets (id, node_id) VALUES %s", 
                   [(m, nid) for m, nid in market_nodes])
                   
    # Insert Products
    execute_values(cur, "INSERT INTO products (id, sku, name, unit_price) VALUES %s",
                   [(p, f"SKU_{p[:4]}", f"Product_{p[:4]}", round(random.uniform(10, 100), 2)) for p in products])
                   
    # Routes
    routes_data = []
    # Supplier to Factory
    for s, snid in supplier_nodes:
        f, fnid = random.choice(factory_nodes)
        routes_data.append((str(uuid.uuid4()), snid, fnid, 'ROAD', random.randint(50, 500), random.randint(2, 24)))
    
    # Factory to Warehouse
    for f, fnid in factory_nodes:
        w, wnid = random.choice(warehouse_nodes)
        routes_data.append((str(uuid.uuid4()), fnid, wnid, 'ROAD', random.randint(50, 500), random.randint(2, 24)))
        
    # Warehouse to Market
    for m, mnid in market_nodes:
        w, wnid = random.choice(warehouse_nodes)
        routes_data.append((str(uuid.uuid4()), wnid, mnid, 'ROAD', random.randint(10, 100), random.randint(1, 12)))
        
    execute_values(cur, """
        INSERT INTO routes (id, origin_node_id, destination_node_id, transport_mode, distance_km, estimated_transit_time_hours)
        VALUES %s ON CONFLICT DO NOTHING
    """, routes_data)
    
    # Inventory init (start with some)
    inv_data = []
    for w, wnid in warehouse_nodes:
        for p in products:
            if random.random() > 0.5:
                inv_data.append((str(uuid.uuid4()), wnid, p, random.randint(50, 200), 0))
    execute_values(cur, "INSERT INTO inventory (id, node_id, product_id, available_quantity, reserved_quantity) VALUES %s", inv_data)

    conn.commit()
    cur.close()
    conn.close()
    print("Data generation and loading complete.")

def build_graph(db_kwargs: dict):
    conn = psycopg2.connect(**db_kwargs)
    cur = conn.cursor()
    
    cur.execute("SELECT id, type, name FROM nodes")
    nodes = cur.fetchall()
    
    cur.execute("SELECT origin_node_id, destination_node_id, estimated_transit_time_hours FROM routes")
    routes = cur.fetchall()
    
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n[0], type=n[1], name=n[2])
        
    for r in routes:
        G.add_edge(r[0], r[1], transit_hours=r[2])
        
    cur.close()
    conn.close()
    return G
