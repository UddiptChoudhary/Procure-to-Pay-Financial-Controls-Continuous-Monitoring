# Internal Audit & Continuous Controls Monitoring (CCM) Findings Report

**Audit Subject:** Procure-to-Pay (P2P) Cycle & Continuous Financial Controls Monitoring  
**Review Period:** Full Fiscal Year 2023  
**Audit Standard:** Sarbanes-Oxley (SOX) Section 404 Key Financial Controls & COSO Framework  
**Report Date:** November 2023  

---

## 1. Executive Summary

Internal Audit and the Financial Controls Continuous Monitoring team completed an end-to-end automated analytics review of the enterprise **Procure-to-Pay (P2P)** lifecycle spanning **Purchase Requisitions, Purchase Orders (POs), Goods Receipts (GR), Vendor Invoices, and Disbursements**.

Testing evaluated **179 Purchase Orders**, **180 Invoices**, and **178 Disbursements** across **20 active vendors**, totaling **\$12.55M** in cash outflows.

### High-Level Audit Metrics:
- **Total Procurement Spend (PO):** \$12,698,810.00
- **Total Disbursements Disbursed:** \$12,549,460.00
- **Total Identified Control Violations:** **34 Exceptions**
- **Total Financial Exposure at Risk:** **\$1,803,230.00 (14.37% of Disbursed Spend)**
- **Duplicate Invoices & Double Disbursements:** **\$54,250.00**

```
+-------------------------------------------------------------------------------------------------+
| CONTROL CATEGORY          | SEVERITY | INCIDENTS | AMOUNT AT RISK ($) | % OF TOTAL EXPOSURE     |
+-------------------------------------------------------------------------------------------------+
| Approval Violations       | HIGH     | 14        | $1,137,340.00      | 63.07%                  |
| Vendor Master Anomalies   | HIGH     | 3         | $427,240.00        | 23.69%                  |
| Three-Way Matching        | HIGH/MED | 6         | $95,100.00         | 5.27%                   |
| Split Purchases           | HIGH     | 3         | $56,800.00         | 3.15%                   |
| Duplicate Invoices        | HIGH     | 5         | $54,250.00         | 3.01%                   |
| Payment Anomalies         | HIGH/MED | 3         | $32,500.00         | 1.80%                   |
+-------------------------------------------------------------------------------------------------+
| TOTAL                     |          | 34        | $1,803,230.00      | 100.00%                 |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Detailed Findings by Control Objective

### Finding 1: Duplicate Invoices and Duplicate Disbursements
- **Audit Objective:** Prevent duplicate payments resulting from identical or near-duplicate vendor billings.
- **Exceptions Identified:** 5 incidents totaling **\$54,250.00**.
  - **Exact Duplicate Invoice Paid Twice:** Vendor `VND001` (Apex Tech Solutions) submitted invoice `#INV-APEX-77881` for \$14,500.00 on April 18, 2023, paid on May 15. The exact same invoice was resubmitted on April 30, approved by a different AP clerk, and paid again on May 25.
  - **Suspect Near-Duplicate Invoice:** Vendor `VND004` (Starlight Office Group) billed invoice `#INV-44910` (\$8,750.00) and subsequently billed `#INV-44910-A` (\$8,750.00) 8 days later for identical service lines; both were disbursed.
  - **Duplicate Disbursement on Single Invoice ID:** Invoice `INV-3165` (\$12,000.00) was paid twice (first via ACH on Aug 28, then via Wire on Aug 29) due to lack of payment execution locking.
- **Risk Impact:** Direct, irrecoverable cash loss without supplier recovery recovery audits.

### Finding 2: Three-Way Matching Failures (PO vs GR vs Invoice)
- **Audit Objective:** Ensure invoices are paid only for goods/services contracted and physically received.
- **Exceptions Identified:** 6 incidents totaling **\$95,100.00**.
  - **Quantity Over-billing:** Invoiced 50 laptops (\$62,500) from `VND012` where receiving dock confirmation logged only 30 units (\$37,500). AP was processing payment on 20 phantom units (\$25,000 at risk).
  - **Price Variance > 2% Tolerance:** Invoiced unit price of \$460/unit exceeded contracted PO rate of \$380/unit (+21% variance) on monitor supplies.
  - **Missing Goods Receipt:** Invoice `#INV-PREC-99120` (\$16,000) was presented for physical industrial racking units without any dock receiving record.
  - **Maverick Spend (Non-PO Invoice):** \$24,500 invoice processed for media consulting with no pre-approved purchase order.

### Finding 3: Split Purchases / Structuring Below Authorization Thresholds
- **Audit Objective:** Prevent buyers from deliberately dividing high-value orders to bypass managerial and director signoff limits (\$10,000 threshold).
- **Exceptions Identified:** 3 structured clusters totaling **\$56,800.00**.
  - Senior Buyer Kevin Zhang (`EMP010`) created 3 separate purchase orders on the same day (`PO-1165`, `PO-1166`, `PO-1167`) for \$9,600, \$9,200, and \$9,200 to vendor `VND005`, totaling \$28,000. Each was deliberately kept under his \$10,000 authority threshold to evade VP signoff.
  - Buyer Amanda Foster (`EMP011`) created two consecutive \$9,800 POs to `VND011` within 24 hours.

### Finding 4: Vendor Master Anomalies & Conflict of Interest (SoD)
- **Audit Objective:** Mitigate employee-vendor collusion, shell company pass-throughs, and unauthorized payees.
- **Exceptions Identified:** 3 major high-risk findings totaling **\$427,240.00**.
  - **Employee-Vendor Conflict (Phantom Vendor):** Registered vendor `VND017` (Evergreen Management) has the **exact same bank account number** and **residential address** (742 Evergreen Terrace) as Category Sourcing Lead Robert Mercer (`EMP019`). A total of **\$35,000.00** was disbursed to this vendor.
  - **Duplicate Bank Account:** Vendor `VND016` (Apex Strategic Consulting) shares the exact bank routing and account number with vendor `VND001`. Total disbursements to this shared account exceeded \$42,000.
  - **Transactions on Inactive Vendor:** Vendor `VND018` (Dormant Industrial Corp), marked as INACTIVE since 2020, received a sudden **\$78,000.00** PO and disbursement without master file re-certification.

### Finding 5: Payment Execution Anomalies
- **Audit Objective:** Ensure disbursements strictly mirror valid approved invoices.
- **Exceptions Identified:** 3 incidents totaling **\$32,500.00**.
  - **Ghost Payment:** \$19,500 wire disbursement executed with NULL invoice ID.
  - **Overpayment:** Payment of \$19,500 disbursed against invoice of \$15,000 (\$4,500 overpayment).
  - **Premature Payment:** Disbursed 15 days prior to invoice receipt date.

### Finding 6: Delegation of Authority (DoA) Limit Breaches
- **Audit Objective:** Enforce strict organizational governance limits and Segregation of Duties.
- **Exceptions Identified:** 14 POs totaling **\$1,137,340.00**.
  - Junior Buyer `EMP013` (authorized signing limit: \$2,500) approved a **\$68,000.00** IT infrastructure PO.
  - Self-Approval Violations: Multiple managers created high-value purchase orders and self-approved them, bypassing Segregation of Duties.

---

## 3. Recommended Remediation & Management Action Plan

1. **ERP System Hard Controls:** Configure automated hard stops in SAP / Oracle preventing invoice posting if:
   - Invoice number matches existing vendor record within 180 days.
   - Billed quantity > accepted received dock quantity (zero tolerance for physical inventory).
   - Approver limit < requisition net total.
2. **Automated Vendor Master File Reconciliation:** Schedule bi-weekly fuzzy matching between employee HR master data (addresses, direct deposit bank accounts, SSN/tax IDs) and vendor master payees.
3. **Continuous Controls Monitoring (CCM) Deployment:** Transition from annual sample-based audits to daily automated CCM script runs (using the SQL/Python engine built in this project).
