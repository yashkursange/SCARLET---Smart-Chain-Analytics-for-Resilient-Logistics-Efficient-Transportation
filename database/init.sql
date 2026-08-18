-- =============================================================================
-- SCARLET — Phase 1 & 2 Database Schema
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Health Check Table (Phase 1)
CREATE TABLE IF NOT EXISTS health_check (
    id         SERIAL      PRIMARY KEY,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO health_check DEFAULT VALUES;

-- ENUMs
CREATE TYPE node_type AS ENUM ('SUPPLIER', 'FACTORY', 'WAREHOUSE', 'MARKET');
CREATE TYPE transport_mode AS ENUM ('ROAD', 'RAIL', 'SEA', 'AIR');
CREATE TYPE vehicle_status AS ENUM ('AVAILABLE', 'IN_TRANSIT', 'MAINTENANCE', 'UNAVAILABLE');
CREATE TYPE transaction_type AS ENUM ('RECEIPT', 'SHIPMENT', 'ADJUSTMENT');
CREATE TYPE order_status AS ENUM ('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED');
CREATE TYPE shipment_status AS ENUM ('PLANNED', 'IN_TRANSIT', 'DELIVERED', 'DELAYED', 'CANCELLED');
CREATE TYPE disruption_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- Nodes
CREATE TABLE nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type node_type NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    latitude NUMERIC,
    longitude NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Suppliers
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL UNIQUE REFERENCES nodes(id) ON DELETE RESTRICT,
    reliability NUMERIC NOT NULL CHECK (reliability >= 0 AND reliability <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Factories
CREATE TABLE factories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL UNIQUE REFERENCES nodes(id) ON DELETE RESTRICT,
    capacity_per_day NUMERIC NOT NULL CHECK (capacity_per_day > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Warehouses
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL UNIQUE REFERENCES nodes(id) ON DELETE RESTRICT,
    total_capacity NUMERIC NOT NULL CHECK (total_capacity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Markets
CREATE TABLE markets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL UNIQUE REFERENCES nodes(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    unit_price NUMERIC NOT NULL CHECK (unit_price > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Supplier Factory Products
CREATE TABLE supplier_factory_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    cost NUMERIC NOT NULL CHECK (cost >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(supplier_id, factory_id, product_id)
);

-- Factory Production Capabilities
CREATE TABLE factory_production_capabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    factory_id UUID NOT NULL REFERENCES factories(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    production_rate_per_day NUMERIC NOT NULL CHECK (production_rate_per_day > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(factory_id, product_id)
);

-- Routes
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE RESTRICT,
    destination_node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE RESTRICT,
    transport_mode transport_mode NOT NULL,
    distance_km NUMERIC NOT NULL CHECK (distance_km >= 0),
    estimated_transit_time_hours NUMERIC NOT NULL CHECK (estimated_transit_time_hours >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(origin_node_id, destination_node_id, transport_mode)
);

-- Vehicles
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(100) NOT NULL,
    transport_mode transport_mode NOT NULL,
    capacity NUMERIC NOT NULL CHECK (capacity > 0),
    status vehicle_status NOT NULL DEFAULT 'AVAILABLE',
    current_node_id UUID REFERENCES nodes(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Inventory
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    available_quantity NUMERIC NOT NULL DEFAULT 0 CHECK (available_quantity >= 0),
    reserved_quantity NUMERIC NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(node_id, product_id)
);

-- Inventory Transactions (Historical)
CREATE TABLE inventory_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    inventory_id UUID NOT NULL REFERENCES inventory(id) ON DELETE RESTRICT,
    transaction_type transaction_type NOT NULL,
    quantity NUMERIC NOT NULL,
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_id UUID NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,
    order_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status order_status NOT NULL DEFAULT 'PENDING',
    target_delivery_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Order Items
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Shipments
CREATE TABLE shipments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id UUID NOT NULL REFERENCES routes(id) ON DELETE RESTRICT,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE RESTRICT,
    status shipment_status NOT NULL DEFAULT 'PLANNED',
    departure_time TIMESTAMPTZ,
    expected_arrival_time TIMESTAMPTZ,
    actual_arrival_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Shipment Items
CREATE TABLE shipment_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE RESTRICT,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Demand History
CREATE TABLE demand (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_id UUID NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    demand_quantity NUMERIC NOT NULL CHECK (demand_quantity >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Disruptions
CREATE TABLE disruptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity disruption_severity NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    CHECK (end_time IS NULL OR end_time >= start_time),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Disrupted Nodes
CREATE TABLE disrupted_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    disruption_id UUID NOT NULL REFERENCES disruptions(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(disruption_id, node_id)
);

-- Disrupted Routes
CREATE TABLE disrupted_routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    disruption_id UUID NOT NULL REFERENCES disruptions(id) ON DELETE CASCADE,
    route_id UUID NOT NULL REFERENCES routes(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(disruption_id, route_id)
);

-- Disrupted Vehicles
CREATE TABLE disrupted_vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    disruption_id UUID NOT NULL REFERENCES disruptions(id) ON DELETE CASCADE,
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(disruption_id, vehicle_id)
);

-- Disrupted Shipments
CREATE TABLE disrupted_shipments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    disruption_id UUID NOT NULL REFERENCES disruptions(id) ON DELETE CASCADE,
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(disruption_id, shipment_id)
);

-- Indexes for performance (especially foreign keys and common query fields)
CREATE INDEX idx_nodes_type ON nodes(type);
CREATE INDEX idx_inventory_node_product ON inventory(node_id, product_id);
CREATE INDEX idx_orders_market_id ON orders(market_id);
CREATE INDEX idx_shipments_route_id ON shipments(route_id);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_demand_market_product ON demand(market_id, product_id);
CREATE INDEX idx_inventory_transactions_inventory_id ON inventory_transactions(inventory_id);
CREATE INDEX idx_routes_origin_dest ON routes(origin_node_id, destination_node_id);
