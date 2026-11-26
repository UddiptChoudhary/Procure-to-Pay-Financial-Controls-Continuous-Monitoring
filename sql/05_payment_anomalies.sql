-- ====================================================================
-- CONTROL TEST 05: PAYMENT ANOMALIES & DISBURSEMENT DEFECTS
-- Objective: Detect unapproved disbursements without invoice reference,
--            overpayments exceeding invoice amount, and premature payments.
-- Cash Management & Treasury Controls.
-- ====================================================================

-- --------------------------------------------------------------------
-- Test 5A: Ghost Payments (Payments Without Invoice Reference)
-- Logic: Disbursement executed in treasury system without any backing invoice ID.
-- --------------------------------------------------------------------
SELECT 
    'PAY_UNMATCHED_NO_INV' AS test_code,
    'Ghost Payment Without Invoice' AS exception_type,
    'HIGH' AS severity,
    p.payment_id,
    p.payment_reference,
    p.vendor_id,
    v.vendor_name,
    p.payment_date,
    p.payment_amount AS amount_at_risk,
    p.payment_method,
    p.bank_account_remitted,
    'Disbursement executed with no associated invoice record in ledger.' AS audit_finding
FROM payments p
JOIN vendors v ON p.vendor_id = v.vendor_id
WHERE p.invoice_id IS NULL;

-- --------------------------------------------------------------------
-- Test 5B: Overpayment (Payment Amount > Invoice Net Payable)
-- Logic: Total disbursed exceeds the billed invoice amount.
-- --------------------------------------------------------------------
SELECT 
    'PAY_OVERPAYMENT' AS test_code,
    'Invoice Overpayment Variance' AS exception_type,
    'HIGH' AS severity,
    p.payment_id,
    p.payment_reference,
    p.invoice_id,
    i.invoice_number,
    p.vendor_id,
    v.vendor_name,
    i.invoice_amount,
    p.payment_amount,
    ROUND(p.payment_amount - i.invoice_amount, 2) AS overpaid_excess_amount,
    'Payment disbursed exceeds the authorized invoice total.' AS audit_finding
FROM payments p
JOIN invoices i ON p.invoice_id = i.invoice_id
JOIN vendors v ON p.vendor_id = v.vendor_id
WHERE p.payment_amount > i.invoice_amount;

-- --------------------------------------------------------------------
-- Test 5C: Premature Payment (Disbursed Prior to Invoice Date / Approval)
-- Logic: Payment date occurred before the invoice was even received or approved.
-- --------------------------------------------------------------------
SELECT 
    'PAY_PREMATURE_DATE' AS test_code,
    'Premature Disbursement Before Invoice' AS exception_type,
    'MEDIUM' AS severity,
    p.payment_id,
    p.payment_reference,
    p.invoice_id,
    i.invoice_number,
    p.vendor_id,
    v.vendor_name,
    p.payment_date,
    i.invoice_date,
    i.approval_date,
    ROUND(JULIANDAY(i.invoice_date) - JULIANDAY(p.payment_date), 1) AS days_paid_prior_to_invoice,
    p.payment_amount,
    'Cash disbursement date precedes invoice issuance or approval.' AS audit_finding
FROM payments p
JOIN invoices i ON p.invoice_id = i.invoice_id
JOIN vendors v ON p.vendor_id = v.vendor_id
WHERE p.payment_date < i.invoice_date;
