-- ====================================================================
-- CONTROL TEST 06: APPROVAL VIOLATIONS & DELEGATION OF AUTHORITY (DoA)
-- Objective: Detect approvals exceeding delegated financial authority limits
--            and self-approvals (requester = approver) violating Segregation of Duties.
-- Corporate Governance: SOX 404 Key Financial Controls.
-- ====================================================================

-- --------------------------------------------------------------------
-- Test 6A: Approval Limit Exceeded
-- Logic: Purchase order approved by an employee whose designated approval limit
--        is less than the purchase order total amount.
-- --------------------------------------------------------------------
SELECT 
    'APPR_LIMIT_EXCEEDED' AS test_code,
    'Approval Exceeds Authorization Limit' AS exception_type,
    'HIGH' AS severity,
    po.po_id,
    po.po_number,
    po.po_date,
    po.total_amount AS po_total_amount,
    po.department,
    po.approver_id,
    e.first_name || ' ' || e.last_name AS approver_name,
    e.job_title AS approver_title,
    e.approval_limit AS authorized_limit,
    ROUND(po.total_amount - e.approval_limit, 2) AS unauthorized_excess_amount,
    'PO total exceeds the approver delegated financial signing authority.' AS audit_finding
FROM purchase_orders po
JOIN employees e ON po.approver_id = e.employee_id
WHERE po.total_amount > e.approval_limit;

-- --------------------------------------------------------------------
-- Test 6B: Self-Approval Violation (Segregation of Duties)
-- Logic: The requester who created the purchase order also approved it.
-- --------------------------------------------------------------------
SELECT 
    'APPR_SELF_APPROVAL' AS test_code,
    'Self-Approval SoD Violation' AS exception_type,
    'HIGH' AS severity,
    po.po_id,
    po.po_number,
    po.po_date,
    po.total_amount,
    po.department,
    po.requester_id,
    e.first_name || ' ' || e.last_name AS employee_name,
    e.job_title,
    'Employee originated and approved their own purchase order.' AS audit_finding
FROM purchase_orders po
JOIN employees e ON po.requester_id = e.employee_id
WHERE po.requester_id = po.approver_id;
