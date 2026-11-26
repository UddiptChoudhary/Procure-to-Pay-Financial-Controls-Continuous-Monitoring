-- ====================================================================
-- CONTROL TEST 07: EXECUTIVE RISK KPIS & CONTINUOUS MONITORING ROLLUP
-- Objective: Aggregate total procurement spend, amount at risk, exception counts,
--            vendor risk scoring, and monthly anomaly trends for executive dashboards.
-- ====================================================================

-- --------------------------------------------------------------------
-- 1. Executive Summary KPIs
-- --------------------------------------------------------------------
WITH SpendStats AS (
    SELECT 
        COUNT(DISTINCT po_id) AS total_purchase_orders,
        COUNT(DISTINCT vendor_id) AS active_vendors_engaged,
        SUM(total_amount) AS total_po_spend
    FROM purchase_orders
),
InvoiceStats AS (
    SELECT 
        COUNT(DISTINCT invoice_id) AS total_invoices_received,
        SUM(invoice_amount) AS total_invoiced_spend
    FROM invoices
),
DisbursementStats AS (
    SELECT 
        COUNT(DISTINCT payment_id) AS total_payments_disbursed,
        SUM(payment_amount) AS total_disbursed_spend
    FROM payments
)
SELECT 
    s.total_po_spend,
    s.total_purchase_orders,
    s.active_vendors_engaged,
    i.total_invoiced_spend,
    i.total_invoices_received,
    d.total_disbursed_spend,
    d.total_payments_disbursed
FROM SpendStats s, InvoiceStats i, DisbursementStats d;

-- --------------------------------------------------------------------
-- 2. Consolidated Control Exceptions & Exposure by Test Category
-- --------------------------------------------------------------------
SELECT 
    category,
    test_code,
    test_name,
    severity,
    COUNT(*) AS exception_count,
    ROUND(SUM(amount_at_risk), 2) AS total_amount_at_risk,
    ROUND(AVG(amount_at_risk), 2) AS avg_exposure_per_incident
FROM control_exceptions
GROUP BY category, test_code, test_name, severity
ORDER BY total_amount_at_risk DESC;

-- --------------------------------------------------------------------
-- 3. High-Risk Vendor Exposure Ranking
-- --------------------------------------------------------------------
SELECT 
    v.vendor_id,
    v.vendor_name,
    v.vendor_status,
    COUNT(ce.exception_id) AS total_control_exceptions,
    ROUND(SUM(ce.amount_at_risk), 2) AS total_risk_exposure,
    ROUND(COALESCE((SELECT SUM(payment_amount) FROM payments WHERE vendor_id = v.vendor_id), 0), 2) AS total_disbursed_to_vendor,
    ROUND((SUM(ce.amount_at_risk) / NULLIF((SELECT SUM(payment_amount) FROM payments WHERE vendor_id = v.vendor_id), 0)) * 100.0, 1) AS risk_exposure_percentage
FROM vendors v
JOIN control_exceptions ce ON v.vendor_id = ce.vendor_id
GROUP BY v.vendor_id, v.vendor_name, v.vendor_status
ORDER BY total_risk_exposure DESC;

-- --------------------------------------------------------------------
-- 4. Monthly Exception Trends (Continuous Monitoring Timeline)
-- --------------------------------------------------------------------
SELECT 
    STRFTIME('%Y-%m', detection_date) AS audit_month,
    severity,
    COUNT(*) AS monthly_exceptions_count,
    ROUND(SUM(amount_at_risk), 2) AS monthly_amount_at_risk
FROM control_exceptions
GROUP BY STRFTIME('%Y-%m', detection_date), severity
ORDER BY audit_month ASC, severity DESC;
