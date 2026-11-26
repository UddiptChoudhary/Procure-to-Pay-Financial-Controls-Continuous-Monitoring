-- ====================================================================
-- CONTROL TEST 04: VENDOR MASTER ANOMALIES & CONFLICT OF INTEREST
-- Objective: Detect duplicate vendor bank accounts, employee-vendor match
--            (phantom vendors / self-dealing), and activity on dormant vendors.
-- Forensic Accounting: Anti-Fraud & FCPA / SOX Compliance.
-- ====================================================================

-- --------------------------------------------------------------------
-- Test 4A: Duplicate Bank Accounts across Vendors
-- Logic: Different vendor records sharing identical bank routing & account numbers.
--        Indicates potential shell companies or fraudulent payee rerouting.
-- --------------------------------------------------------------------
WITH SharedBankVendors AS (
    SELECT 
        v.bank_routing_number,
        v.bank_account_number,
        COUNT(v.vendor_id) AS vendor_count,
        GROUP_CONCAT(v.vendor_id || ' (' || v.vendor_name || ')', ' | ') AS linked_vendors
    FROM vendors v
    GROUP BY v.bank_routing_number, v.bank_account_number
    HAVING COUNT(v.vendor_id) > 1
)
SELECT 
    'VND_DUP_BANK' AS test_code,
    'Duplicate Vendor Bank Account' AS exception_type,
    'HIGH' AS severity,
    sbv.bank_routing_number,
    sbv.bank_account_number,
    sbv.vendor_count,
    sbv.linked_vendors,
    COALESCE(SUM(p.payment_amount), 0) AS total_disbursed_to_shared_account,
    'Multiple distinct vendor entities share the exact same bank account.' AS audit_finding
FROM SharedBankVendors sbv
LEFT JOIN vendors v ON sbv.bank_account_number = v.bank_account_number
LEFT JOIN payments p ON v.vendor_id = p.vendor_id
GROUP BY sbv.bank_routing_number, sbv.bank_account_number, sbv.vendor_count, sbv.linked_vendors;

-- --------------------------------------------------------------------
-- Test 4B: Employee-Vendor Match (Conflict of Interest / Phantom Vendor)
-- Logic: An employee's personal bank account or home address matches
--        a vendor registered in the master file.
-- --------------------------------------------------------------------
SELECT 
    'CONFLICT_EMP_VENDOR' AS test_code,
    'Employee-Vendor Match (Conflict of Interest)' AS exception_type,
    'HIGH' AS severity,
    e.employee_id,
    e.first_name || ' ' || e.last_name AS employee_name,
    e.department AS employee_department,
    e.job_title AS employee_title,
    v.vendor_id,
    v.vendor_name,
    CASE 
        WHEN e.bank_account_number = v.bank_account_number AND LOWER(TRIM(e.street_address)) = LOWER(TRIM(v.street_address))
            THEN 'Both Bank Account AND Physical Street Address Match'
        WHEN e.bank_account_number = v.bank_account_number
            THEN 'Personal Bank Account Matches Vendor Bank Account'
        ELSE 'Residential Address Matches Vendor Business Address'
    END AS match_criteria,
    e.street_address AS matched_address,
    e.bank_account_number AS matched_bank_account,
    COALESCE((SELECT SUM(payment_amount) FROM payments WHERE vendor_id = v.vendor_id), 0) AS cumulative_fraud_exposure,
    'Employee master data matches vendor payee profile indicating phantom vendor.' AS audit_finding
FROM employees e
JOIN vendors v 
    ON e.bank_account_number = v.bank_account_number 
    OR (LOWER(TRIM(e.street_address)) = LOWER(TRIM(v.street_address)) AND LOWER(TRIM(e.postal_code)) = LOWER(TRIM(v.postal_code)));

-- --------------------------------------------------------------------
-- Test 4C: Transactions with Inactive / Dormant Vendors
-- Logic: Purchase Orders issued or disbursements made to vendors flagged as INACTIVE.
-- --------------------------------------------------------------------
SELECT 
    'VND_INACTIVE_ACTIVITY' AS test_code,
    'Transaction on Inactive/Dormant Vendor' AS exception_type,
    'HIGH' AS severity,
    v.vendor_id,
    v.vendor_name,
    v.vendor_status,
    v.last_review_date,
    po.po_id,
    po.po_date,
    po.total_amount AS po_amount,
    'Spend initiated against a vendor flagged as inactive in master records.' AS audit_finding
FROM purchase_orders po
JOIN vendors v ON po.vendor_id = v.vendor_id
WHERE v.vendor_status = 'INACTIVE';
