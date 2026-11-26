-- ====================================================================
-- CONTROL TEST 01: DUPLICATE INVOICE DETECTION
-- Objective: Detect exact duplicate invoices, suspect near-duplicate invoices,
--            and multiple payments disbursed against a single invoice.
-- Financial Impact: Direct cash outflow loss, supplier overpayment.
-- ====================================================================

-- --------------------------------------------------------------------
-- Test 1A: Exact Duplicate Invoices
-- Logic: Same Vendor ID and exact same Invoice Number submitted multiple times.
-- --------------------------------------------------------------------
WITH ExactInvoiceDuplicates AS (
    SELECT 
        i.vendor_id,
        v.vendor_name,
        i.invoice_number,
        COUNT(i.invoice_id) AS invoice_submission_count,
        MIN(i.invoice_date) AS first_invoice_date,
        MAX(i.invoice_date) AS latest_invoice_date,
        SUM(i.invoice_amount) AS total_billed_amount,
        AVG(i.invoice_amount) AS single_invoice_amount,
        GROUP_CONCAT(i.invoice_id, ', ') AS matched_invoice_ids
    FROM invoices i
    JOIN vendors v ON i.vendor_id = v.vendor_id
    GROUP BY i.vendor_id, v.vendor_name, i.invoice_number
    HAVING COUNT(i.invoice_id) > 1
)
SELECT 
    'DUP_INV_EXACT' AS test_code,
    'Exact Duplicate Invoice' AS exception_type,
    'HIGH' AS severity,
    vendor_id,
    vendor_name,
    invoice_number,
    matched_invoice_ids,
    first_invoice_date,
    latest_invoice_date,
    single_invoice_amount,
    invoice_submission_count,
    -- Amount at risk is the redundant duplicate billing
    ROUND((invoice_submission_count - 1) * single_invoice_amount, 2) AS duplicate_amount_at_risk,
    'Same vendor submitted identical invoice number multiple times.' AS audit_finding
FROM ExactInvoiceDuplicates;

-- --------------------------------------------------------------------
-- Test 1B: Suspect Near-Duplicate Invoices (Fuzzy / Pattern Manipulation)
-- Logic: Same Vendor ID, identical invoice amount, billed within a 30-day window,
--        but with slightly altered invoice numbers (e.g. appended -A, suffix, or typographical variance).
-- --------------------------------------------------------------------
WITH RankedInvoices AS (
    SELECT 
        i1.invoice_id AS invoice_id_1,
        i2.invoice_id AS invoice_id_2,
        i1.vendor_id,
        v.vendor_name,
        i1.invoice_number AS invoice_num_1,
        i2.invoice_number AS invoice_num_2,
        i1.invoice_amount,
        i1.invoice_date AS invoice_date_1,
        i2.invoice_date AS invoice_date_2,
        -- Calculate absolute day difference
        ABS(JULIANDAY(i2.invoice_date) - JULIANDAY(i1.invoice_date)) AS day_difference
    FROM invoices i1
    JOIN invoices i2 
        ON i1.vendor_id = i2.vendor_id 
        AND i1.invoice_amount = i2.invoice_amount 
        AND i1.invoice_id < i2.invoice_id -- Prevent reverse pairings
        AND i1.invoice_number != i2.invoice_number
    JOIN vendors v ON i1.vendor_id = v.vendor_id
    WHERE ABS(JULIANDAY(i2.invoice_date) - JULIANDAY(i1.invoice_date)) <= 30
)
SELECT 
    'DUP_INV_SUSPECT' AS test_code,
    'Suspect Near-Duplicate Invoice' AS exception_type,
    'HIGH' AS severity,
    vendor_id,
    vendor_name,
    invoice_id_1 || ' & ' || invoice_id_2 AS matched_invoice_ids,
    invoice_num_1 || ' vs ' || invoice_num_2 AS compared_invoice_numbers,
    invoice_date_1,
    invoice_date_2,
    day_difference,
    invoice_amount AS potential_duplicate_amount,
    'Identical dollar amount to same vendor within 30 days with altered invoice number.' AS audit_finding
FROM RankedInvoices;

-- --------------------------------------------------------------------
-- Test 1C: Duplicate Payments on Single Invoice
-- Logic: An individual invoice ID that has been paid more than once in the payments ledger.
-- --------------------------------------------------------------------
WITH DuplicateDisbursements AS (
    SELECT 
        p.invoice_id,
        p.vendor_id,
        v.vendor_name,
        i.invoice_number,
        i.invoice_amount,
        COUNT(p.payment_id) AS payment_count,
        SUM(p.payment_amount) AS total_disbursed,
        GROUP_CONCAT(p.payment_reference, ', ') AS payment_references,
        MIN(p.payment_date) AS first_payment_date,
        MAX(p.payment_date) AS latest_payment_date
    FROM payments p
    JOIN invoices i ON p.invoice_id = i.invoice_id
    JOIN vendors v ON p.vendor_id = v.vendor_id
    WHERE p.payment_status = 'COMPLETED'
    GROUP BY p.invoice_id, p.vendor_id, v.vendor_name, i.invoice_number, i.invoice_amount
    HAVING COUNT(p.payment_id) > 1
)
SELECT 
    'DUP_PAYMENT_INV' AS test_code,
    'Duplicate Payment on Single Invoice' AS exception_type,
    'HIGH' AS severity,
    invoice_id,
    vendor_id,
    vendor_name,
    invoice_number,
    invoice_amount,
    payment_count,
    total_disbursed,
    ROUND(total_disbursed - invoice_amount, 2) AS duplicate_cash_loss,
    payment_references,
    first_payment_date,
    latest_payment_date,
    'Single vendor invoice paid multiple times in payments ledger.' AS audit_finding
FROM DuplicateDisbursements;
