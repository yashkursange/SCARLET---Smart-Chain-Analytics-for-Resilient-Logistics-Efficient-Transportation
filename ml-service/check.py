import psycopg2
conn = psycopg2.connect('postgresql://scarlet_user:%40Yashop123@localhost:5432/scarlet')
cur = conn.cursor()

def get_columns(table):
    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}';")
    return cur.fetchall()

print("inventory:", get_columns('inventory'))
print("shipments:", get_columns('shipments'))
print("shipment_items:", get_columns('shipment_items'))
