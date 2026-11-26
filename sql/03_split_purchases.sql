-- ====================================================================
-- CONTROL TEST 03: SPLIT PURCHASES / THRESHOLD CIRCUMVENTION
-- Objective: Detect structuring where multiple purchase orders are issued
--            by the same requester to the same vendor within a short rolling
--            window (<= 72 hours), each just below authorization limits ($10k),
--            to avoid required executive approval.
-- Financial Controls: Internal Delegation of Authority (DoA) Compliance.
-- ====================================================================

WITH ConsecutiveBuyerOrders AS (
    SELECT 
        po.po_id,
        po.po_number,
        po.requester_id,
        e.first_name || ' ' || e.last_name AS requester_name,
        e.approval_limit,
        po.vendor_id,
        v.vendor_name,
        po.po_date,
        po.total_amount,
        -- Previous order details using Window Functions
        LAG(po.po_id, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) AS prev_po_id,
        LAG(po.po_date, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) AS prev_po_date,
        LAG(po.total_amount, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) AS prev_po_amount
    FROM purchase_orders po
    JOIN employees e ON po.requester_id = e.employee_id
    JOIN vendors v ON po.vendor_id = v.vendor_id
    WHERE po.po_status = 'APPROVED'
),
SplitPurchasePairs AS (
    SELECT 
        requester_id,
        requester_name,
        approval_limit,
        vendor_id,
        vendor_name,
        prev_po_id,
        po_id AS current_po_id,
        prev_po_date,
        po_date AS current_po_date,
        ROUND(JULIANDAY(po_date) - JULIANDAY(prev_po_date), 1) AS days_between_orders,
        prev_po_amount,
        total_amount AS current_po_amount,
        ROUND(prev_po_amount + total_amount, 2) AS combined_purchase_amount
    FROM ConsecutiveBuyerOrders
    WHERE prev_po_id IS NOT NULL
      AND (JULIANDAY(po_date) - JULIANDAY(prev_po_date)) <= 3 -- Within 72 hours
      -- Individual orders were below or near the buyer's approval limit ($10,000)
      AND total_amount < 10000.00
      AND prev_po_amount < 10000.00
      -- But combined exceeds the limit requiring higher management signoff!
      AND (prev_po_amount + total_amount) >= 10000.00
)
SELECT 
    'SPLIT_PURCHASE_VIOLATION' AS test_code,
    'Split Purchase Below Authorization Threshold' AS exception_type,
    'HIGH' AS severity,
    requester_id,
    requester_name,
    approval_limit AS buyer_authorization_limit,
    vendor_id,
    vendor_name,
    prev_po_id || ' & ' || current_po_id AS structured_po_ids,
    prev_po_date || ' to ' || current_po_date AS order_window,
    days_between_orders,
    prev_po_amount,
    current_po_amount,
    combined_purchase_amount,
    ROUND(combined_purchase_amount - approval_limit, 2) AS unauthorized_excess_amount,
    'Multiple POs structured within 72 hours to bypass managerial approval threshold.' AS audit_finding
FROM SplitPurchasePairs;
