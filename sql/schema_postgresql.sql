-- ====================================================================
-- Procure-to-Pay (P2P) Continuous Controls Monitoring & Financial Audit
-- Database Schema: PostgreSQL (Enterprise Relational Warehouse)
-- ====================================================================

-- 1. Employees
CREATE TABLE IF NOT EXISTS employees (
    employee_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    department VARCHAR(50) NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    approval_limit NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    bank_account_number VARCHAR(34),
    street_address VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Vendors
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id VARCHAR(20) PRIMARY KEY,
    vendor_name VARCHAR(150) NOT NULL,
    tax_id VARCHAR(50) NOT NULL,
    bank_account_number VARCHAR(34) NOT NULL,
    bank_routing_number VARCHAR(30) NOT NULL,
    payment_terms VARCHAR(20) NOT NULL DEFAULT 'NET30',
    street_address VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(50) NOT NULL DEFAULT 'USA',
    vendor_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_date DATE NOT NULL,
    last_review_date DATE
);

-- 3. Purchase Orders
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id VARCHAR(30) PRIMARY KEY,
    po_number VARCHAR(50) NOT NULL UNIQUE,
    vendor_id VARCHAR(20) NOT NULL REFERENCES vendors (vendor_id),
    requester_id VARCHAR(20) NOT NULL REFERENCES employees (employee_id),
    approver_id VARCHAR(20) REFERENCES employees (employee_id),
    po_date DATE NOT NULL,
    po_status VARCHAR(30) NOT NULL,
    approval_date DATE,
    total_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Purchase Order Line Items
CREATE TABLE IF NOT EXISTS purchase_order_lines (
    po_line_id VARCHAR(40) PRIMARY KEY,
    po_id VARCHAR(30) NOT NULL REFERENCES purchase_orders (po_id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    item_description VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity_ordered NUMERIC(12, 3) NOT NULL,
    unit_price NUMERIC(15, 2) NOT NULL,
    line_total NUMERIC(15, 2) NOT NULL
);

-- 5. Goods Receipts
CREATE TABLE IF NOT EXISTS goods_receipts (
    gr_id VARCHAR(30) PRIMARY KEY,
    gr_number VARCHAR(50) NOT NULL UNIQUE,
    po_id VARCHAR(30) NOT NULL REFERENCES purchase_orders (po_id),
    po_line_id VARCHAR(40) NOT NULL REFERENCES purchase_order_lines (po_line_id),
    received_date DATE NOT NULL,
    received_by_employee_id VARCHAR(20) NOT NULL REFERENCES employees (employee_id),
    quantity_received NUMERIC(12, 3) NOT NULL,
    condition_status VARCHAR(30) NOT NULL DEFAULT 'ACCEPTED',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Invoices
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id VARCHAR(30) PRIMARY KEY,
    vendor_id VARCHAR(20) NOT NULL REFERENCES vendors (vendor_id),
    invoice_number VARCHAR(60) NOT NULL,
    po_id VARCHAR(30) REFERENCES purchase_orders (po_id),
    invoice_date DATE NOT NULL,
    received_date DATE NOT NULL,
    due_date DATE NOT NULL,
    invoice_amount NUMERIC(15, 2) NOT NULL,
    invoice_status VARCHAR(30) NOT NULL,
    approved_by VARCHAR(20) REFERENCES employees (employee_id),
    approval_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Invoice Line Items
CREATE TABLE IF NOT EXISTS invoice_lines (
    invoice_line_id VARCHAR(40) PRIMARY KEY,
    invoice_id VARCHAR(30) NOT NULL REFERENCES invoices (invoice_id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    item_description VARCHAR(255) NOT NULL,
    quantity_invoiced NUMERIC(12, 3) NOT NULL,
    unit_price NUMERIC(15, 2) NOT NULL,
    line_total NUMERIC(15, 2) NOT NULL,
    po_line_id VARCHAR(40) REFERENCES purchase_order_lines (po_line_id)
);

-- 8. Payments
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(30) PRIMARY KEY,
    payment_reference VARCHAR(60) NOT NULL UNIQUE,
    invoice_id VARCHAR(30) REFERENCES invoices (invoice_id),
    vendor_id VARCHAR(20) NOT NULL REFERENCES vendors (vendor_id),
    payment_date DATE NOT NULL,
    payment_amount NUMERIC(15, 2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    bank_account_remitted VARCHAR(34) NOT NULL,
    payment_status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Control Exceptions Registry
CREATE TABLE IF NOT EXISTS control_exceptions (
    exception_id SERIAL PRIMARY KEY,
    test_code VARCHAR(30) NOT NULL,
    test_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    vendor_id VARCHAR(20),
    amount_at_risk NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    violation_details TEXT NOT NULL,
    detection_date DATE NOT NULL,
    resolution_status VARCHAR(30) NOT NULL DEFAULT 'OPEN'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pg_po_vendor ON purchase_orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_pg_po_date ON purchase_orders(po_date);
CREATE INDEX IF NOT EXISTS idx_pg_inv_vendor ON invoices(vendor_id);
CREATE INDEX IF NOT EXISTS idx_pg_inv_num ON invoices(vendor_id, invoice_number);
CREATE INDEX IF NOT EXISTS idx_pg_pay_inv ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_pg_exc_test ON control_exceptions(test_code);
