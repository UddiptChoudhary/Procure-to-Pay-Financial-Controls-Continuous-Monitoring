-- ====================================================================
-- CONTROL TEST 02: THREE-WAY MATCHING RECONCILIATION
-- Objective: Identify variances between Purchase Orders, Goods Receipts,
--            and Vendor Invoices across Quantity, Unit Price, and Completeness.
-- SOX / COSO Alignment: Preventive & Detective controls over unauthorized disbursements.
-- ====================================================================

-- --------------------------------------------------------------------
-- Test 2A: Quantity Mismatch (Invoiced Quantity > Received Quantity)
-- Logic: Billed quantity exceeds physical receipts logged by warehouse / operations dock.
-- --------------------------------------------------------------------
WITH ReceiptAggregates AS (
    SELECT 
        po_id,
        po_line_id,
        SUM(quantity_received) AS total_received_quantity
    FROM goods_receipts
    WHERE condition_status = 'ACCEPTED'
    GROUP BY po_id, po_line_id
),
LineThreeWayComparison AS (
    SELECT 
        i.invoice_id,
        i.invoice_number,
        i.vendor_id,
        v.vendor_name,
        i.po_id,
        il.invoice_line_id,
        il.po_line_id,
        il.item_description,
        pol.quantity_ordered,
        COALESCE(ra.total_received_quantity, 0) AS quantity_received,
        il.quantity_invoiced,
        il.unit_price AS invoiced_unit_price,
        pol.unit_price AS po_unit_price,
        il.line_total AS invoiced_line_total
    FROM invoice_lines il
    JOIN invoices i ON il.invoice_id = i.invoice_id
    JOIN vendors v ON i.vendor_id = v.vendor_id
    LEFT JOIN purchase_order_lines pol ON il.po_line_id = pol.po_line_id
    LEFT JOIN ReceiptAggregates ra ON il.po_line_id = ra.po_line_id
    WHERE i.po_id IS NOT NULL
)
SELECT 
    '3WAY_QTY_OVERBILL' AS test_code,
    'Quantity Over-billing Variance' AS exception_type,
    'HIGH' AS severity,
    invoice_id,
    invoice_number,
    vendor_id,
    vendor_name,
    po_id,
    item_description,
    quantity_ordered,
    quantity_received,
    quantity_invoiced,
    ROUND(quantity_invoiced - quantity_received, 3) AS unreceived_quantity_billed,
    invoiced_unit_price,
    ROUND((quantity_invoiced - quantity_received) * invoiced_unit_price, 2) AS financial_exposure,
    'Invoiced quantity exceeds dock-verified received quantity.' AS audit_finding
FROM LineThreeWayComparison
WHERE quantity_invoiced > quantity_received;

-- --------------------------------------------------------------------
-- Test 2B: Price Variance (Invoiced Unit Price > PO Contracted Unit Price)
-- Logic: Vendor billed a unit price higher than approved on PO (>2% tolerance).
-- --------------------------------------------------------------------
WITH PriceVarianceAnalysis AS (
    SELECT 
        i.invoice_id,
        i.invoice_number,
        i.vendor_id,
        v.vendor_name,
        i.po_id,
        il.item_description,
        il.quantity_invoiced,
        pol.unit_price AS po_contracted_unit_price,
        il.unit_price AS invoiced_unit_price,
        ROUND(((il.unit_price - pol.unit_price) / pol.unit_price) * 100.0, 2) AS price_variance_pct,
        ROUND((il.unit_price - pol.unit_price) * il.quantity_invoiced, 2) AS price_variance_exposure
    FROM invoice_lines il
    JOIN invoices i ON il.invoice_id = i.invoice_id
    JOIN vendors v ON i.vendor_id = v.vendor_id
    JOIN purchase_order_lines pol ON il.po_line_id = pol.po_line_id
    WHERE il.unit_price > pol.unit_price
)
SELECT 
    '3WAY_PRICE_VARIANCE' AS test_code,
    'Unit Price Exceeds Purchase Order' AS exception_type,
    CASE WHEN price_variance_pct >= 10.0 THEN 'HIGH' ELSE 'MEDIUM' END AS severity,
    invoice_id,
    invoice_number,
    vendor_id,
    vendor_name,
    po_id,
    item_description,
    quantity_invoiced,
    po_contracted_unit_price,
    invoiced_unit_price,
    price_variance_pct,
    price_variance_exposure,
    'Invoiced unit price exceeds authorized purchase order pricing.' AS audit_finding
FROM PriceVarianceAnalysis
WHERE price_variance_pct > 2.0;

-- --------------------------------------------------------------------
-- Test 2C: Invoices Without Goods Receipt (Phantom Billing / Premature)
-- Logic: Vendor invoice processed for physical goods without any receiving record.
-- --------------------------------------------------------------------
WITH InvoicesWithNoReceipt AS (
    SELECT 
        i.invoice_id,
        i.invoice_number,
        i.vendor_id,
        v.vendor_name,
        i.po_id,
        i.invoice_date,
        i.invoice_amount,
        COUNT(gr.gr_id) AS total_goods_receipts_found
    FROM invoices i
    JOIN vendors v ON i.vendor_id = v.vendor_id
    LEFT JOIN goods_receipts gr ON i.po_id = gr.po_id
    WHERE i.po_id IS NOT NULL
    GROUP BY i.invoice_id, i.invoice_number, i.vendor_id, v.vendor_name, i.po_id, i.invoice_date, i.invoice_amount
    HAVING COUNT(gr.gr_id) = 0
)
SELECT 
    '3WAY_MISSING_GR' AS test_code,
    'Invoice Without Goods Receipt' AS exception_type,
    'HIGH' AS severity,
    invoice_id,
    invoice_number,
    vendor_id,
    vendor_name,
    po_id,
    invoice_date,
    invoice_amount AS exposure_amount,
    'Invoice billed for PO but zero goods receipt records exist.' AS audit_finding
FROM InvoicesWithNoReceipt;

-- --------------------------------------------------------------------
-- Test 2D: Maverick / Unapproved Spend (Invoices Without Purchase Order)
-- Logic: Invoices submitted and processed without pre-approved PO requisition.
-- --------------------------------------------------------------------
SELECT 
    '3WAY_NO_PO' AS test_code,
    'Maverick Spend - Non-PO Invoice' AS exception_type,
    'MEDIUM' AS severity,
    i.invoice_id,
    i.invoice_number,
    i.vendor_id,
    v.vendor_name,
    i.invoice_date,
    i.invoice_amount,
    'Spend initiated without purchase order pre-authorization.' AS audit_finding
FROM invoices i
JOIN vendors v ON i.vendor_id = v.vendor_id
WHERE i.po_id IS NULL;
