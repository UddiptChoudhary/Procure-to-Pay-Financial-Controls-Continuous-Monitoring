-- ====================================================================
-- Procure-to-Pay (P2P) Continuous Controls Monitoring & Financial Audit
-- Database Schema: SQLite (Production Embedded Database)
-- ====================================================================

-- 1. Employees (Approvers, Requesters, Master Data)
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
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Vendors (Suppliers Master Data)
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
    vendor_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, BLACKLISTED
    created_date DATE NOT NULL,
    last_review_date DATE
);

-- 3. Purchase Orders (PO Header)
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id VARCHAR(30) PRIMARY KEY,
    po_number VARCHAR(50) NOT NULL UNIQUE,
    vendor_id VARCHAR(20) NOT NULL,
    requester_id VARCHAR(20) NOT NULL,
    approver_id VARCHAR(20),
    po_date DATE NOT NULL,
    po_status VARCHAR(30) NOT NULL, -- APPROVED, PENDING, REJECTED, CLOSED
    approval_date DATE,
    total_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id),
    FOREIGN KEY (requester_id) REFERENCES employees (employee_id),
    FOREIGN KEY (approver_id) REFERENCES employees (employee_id)
);

-- 4. Purchase Order Line Items
CREATE TABLE IF NOT EXISTS purchase_order_lines (
    po_line_id VARCHAR(40) PRIMARY KEY,
    po_id VARCHAR(30) NOT NULL,
    line_number INTEGER NOT NULL,
    item_description VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    quantity_ordered NUMERIC(12, 3) NOT NULL,
    unit_price NUMERIC(15, 2) NOT NULL,
    line_total NUMERIC(15, 2) NOT NULL,
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id)
);

-- 5. Goods Receipts (Receiving Log)
CREATE TABLE IF NOT EXISTS goods_receipts (
    gr_id VARCHAR(30) PRIMARY KEY,
    gr_number VARCHAR(50) NOT NULL UNIQUE,
    po_id VARCHAR(30) NOT NULL,
    po_line_id VARCHAR(40) NOT NULL,
    received_date DATE NOT NULL,
    received_by_employee_id VARCHAR(20) NOT NULL,
    quantity_received NUMERIC(12, 3) NOT NULL,
    condition_status VARCHAR(30) NOT NULL DEFAULT 'ACCEPTED', -- ACCEPTED, DAMAGED, REJECTED
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id),
    FOREIGN KEY (po_line_id) REFERENCES purchase_order_lines (po_line_id),
    FOREIGN KEY (received_by_employee_id) REFERENCES employees (employee_id)
);

-- 6. Invoices (Vendor Invoices Header)
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id VARCHAR(30) PRIMARY KEY,
    vendor_id VARCHAR(20) NOT NULL,
    invoice_number VARCHAR(60) NOT NULL,
    po_id VARCHAR(30), -- May be NULL for non-PO spend
    invoice_date DATE NOT NULL,
    received_date DATE NOT NULL,
    due_date DATE NOT NULL,
    invoice_amount NUMERIC(15, 2) NOT NULL,
    invoice_status VARCHAR(30) NOT NULL, -- APPROVED, PENDING_REVIEW, ON_HOLD, PAID, CANCELLED
    approved_by VARCHAR(20),
    approval_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id),
    FOREIGN KEY (po_id) REFERENCES purchase_orders (po_id),
    FOREIGN KEY (approved_by) REFERENCES employees (employee_id)
);

-- 7. Invoice Line Items
CREATE TABLE IF NOT EXISTS invoice_lines (
    invoice_line_id VARCHAR(40) PRIMARY KEY,
    invoice_id VARCHAR(30) NOT NULL,
    line_number INTEGER NOT NULL,
    item_description VARCHAR(255) NOT NULL,
    quantity_invoiced NUMERIC(12, 3) NOT NULL,
    unit_price NUMERIC(15, 2) NOT NULL,
    line_total NUMERIC(15, 2) NOT NULL,
    po_line_id VARCHAR(40),
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id),
    FOREIGN KEY (po_line_id) REFERENCES purchase_order_lines (po_line_id)
);

-- 8. Payments (Disbursements Log)
CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR(30) PRIMARY KEY,
    payment_reference VARCHAR(60) NOT NULL UNIQUE,
    invoice_id VARCHAR(30), -- Anomalies may include payments without invoice
    vendor_id VARCHAR(20) NOT NULL,
    payment_date DATE NOT NULL,
    payment_amount NUMERIC(15, 2) NOT NULL,
    payment_method VARCHAR(30) NOT NULL, -- ACH, WIRE, CHECK, VIRTUAL_CARD
    bank_account_remitted VARCHAR(34) NOT NULL,
    payment_status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED', -- COMPLETED, FAILED, VOIDED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors (vendor_id)
);

-- 9. Control Exceptions Registry (Audit Log of Violations)
CREATE TABLE IF NOT EXISTS control_exceptions (
    exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_code VARCHAR(30) NOT NULL,
    test_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- HIGH, MEDIUM, LOW
    entity_type VARCHAR(30) NOT NULL, -- INVOICE, PO, PAYMENT, VENDOR, EMPLOYEE
    entity_id VARCHAR(50) NOT NULL,
    vendor_id VARCHAR(20),
    amount_at_risk NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    violation_details TEXT NOT NULL,
    detection_date DATE NOT NULL,
    resolution_status VARCHAR(30) NOT NULL DEFAULT 'OPEN' -- OPEN, UNDER_INVESTIGATION, REMEDIATED, FALSE_POSITIVE
);

-- Indexes for high-performance audit querying
CREATE INDEX IF NOT EXISTS idx_po_vendor ON purchase_orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_po_date ON purchase_orders(po_date);
CREATE INDEX IF NOT EXISTS idx_po_requester ON purchase_orders(requester_id);
CREATE INDEX IF NOT EXISTS idx_gr_po ON goods_receipts(po_id);
CREATE INDEX IF NOT EXISTS idx_inv_vendor ON invoices(vendor_id);
CREATE INDEX IF NOT EXISTS idx_inv_po ON invoices(po_id);
CREATE INDEX IF NOT EXISTS idx_inv_num ON invoices(vendor_id, invoice_number);
CREATE INDEX IF NOT EXISTS idx_pay_inv ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_pay_vendor ON payments(vendor_id);
CREATE INDEX IF NOT EXISTS idx_exc_test ON control_exceptions(test_code);
CREATE INDEX IF NOT EXISTS idx_exc_severity ON control_exceptions(severity);
