# Procure-to-Pay (P2P) Financial Controls & Continuous Controls Monitoring (CCM)

[![Database: SQLite / PostgreSQL](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-blue.svg)](sql/)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](src/)
[![Power BI: Star Schema](https://img.shields.io/badge/Power%20BI-Star%20Schema%20%2B%20DAX-yellow.svg)](powerbi/)
[![Audit Framework: SOX 404 / COSO](https://img.shields.io/badge/Audit%20Framework-SOX%20404%20%7C%20COSO-orange.svg)](reports/)

An enterprise-grade **Continuous Controls Monitoring (CCM) and Audit Analytics** system covering the complete **Procure-to-Pay (P2P)** financial lifecycle:

$$\text{Purchase Requisition} \longrightarrow \text{Purchase Order} \longrightarrow \text{Goods Receipt} \longrightarrow \text{Vendor Invoice} \longrightarrow \text{Payment Disbursement}$$

This project simulates a multi-million-dollar procurement dataset ($12.7M spend across 179 purchase orders and 20 vendors), evaluates financial risk using **complex SQL queries (CTEs, Window Functions, Self-Joins)**, and automates control testing via **Python** to detect **34 high-risk financial exceptions totaling $1.80M in financial exposure**.

---

## 📊 Interactive Dashboard & Executive Visuals

An interactive executive dashboard is included in [`reports/interactive_dashboard.html`](file:///d:/Procure-to-Pay%20(P2P)%20Financial%20Controls%20&%20Continuous%20Monitoring/reports/interactive_dashboard.html). Simply open it in any browser to inspect live KPI cards, category breakdown donuts, monthly exposure trend charts, vendor risk heatmaps, and a searchable audit exception grid.

```
+---------------------------------------------------------------------------------------------------------+
|  PROCURE-TO-PAY (P2P) FINANCIAL CONTROLS & CONTINUOUS MONITORING DASHBOARD (FY2023)                     |
+---------------------------------------------------------------------------------------------------------+
|  [ PO SPEND ]        |  [ DISBURSED ]       |  [ AT RISK ]          |  [ DUP INVOICES ]   | [EXCEPTIONS]|
|  $12.70M             |  $12.55M             |  $1.80M (14.37%)      |  $54.25K (5 events) | 34 Violat.  |
+---------------------------------------------------------------------------------------------------------+
|  [ FINANCIAL RISK BY CATEGORY ]              |  [ MONTHLY EXCEPTION EXPOSURE TREND ]                    |
|  - Approval Violations:  $1.14M (63.1%)      |  - Sharp risk concentration during Q3/Q4 ($345K peak)    |
|  - Vendor Anomalies:    $427K (23.7%)        |  - Correlation with restructured procurement orders      |
|  - Three-Way Matching:  $95.1K  (5.3%)       |                                                          |
|  - Split Purchases:     $56.8K  (3.1%)       |                                                          |
|  - Duplicate Invoices:  $54.3K  (3.0%)       |                                                          |
|  - Payment Anomalies:   $32.5K  (1.8%)       |                                                          |
+----------------------------------------------+----------------------------------------------------------+
|  [ HIGH-RISK VENDOR RANKING ]                |  [ CONTINUOUS CONTROLS EXCEPTION LOG ]                   |
|  1. VND018 (Dormant Industrial):   $78.0K    |  • INV-3162: Exact duplicate paid twice ($14.5K)         |
|  2. VND002 (Summit Cloud Infra):   $76.5K    |  • INV-3166: Quantity overbilling 20 unreceived units    |
|  3. VND012 (NexGen IT Hardware):   $64.1K    |  • VND017:   Phantom vendor matches employee profile     |
|  4. VND016 (Apex Shell Company):   $42.0K    |  • PO-1165:  Split purchase below $10,000 threshold      |
|  5. VND017 (Evergreen Management): $35.0K    |  • PAY-4171: Wire disbursement with zero invoice backing|
+---------------------------------------------------------------------------------------------------------+
```

---

## 🎯 Control Test Catalog & Forensic Detection Logic

| Control Area | Test Code | Detection Methodology & Technical Logic | Severity | Financial Exposure |
| :--- | :--- | :--- | :---: | :---: |
| **Duplicate Invoices** | `DUP_INV_EXACT` | CTE group-by vendor ID and invoice number with `HAVING COUNT(*) > 1` where multiple payments were processed. | **HIGH** | \$14,500.00 |
| **Duplicate Invoices** | `DUP_INV_SUSPECT` | Self-join on vendor ID, matching invoice amounts, and date difference `ABS(JULIANDAY(dt2) - JULIANDAY(dt1)) <= 30` with altered alphanumeric invoice strings (e.g. `INV-44910` vs `INV-44910-A`). | **HIGH** | \$8,750.00 |
| **Duplicate Invoices** | `DUP_PAYMENT_INV` | Payments ledger aggregation detecting identical invoice IDs with multiple completed disbursements. | **HIGH** | \$31,000.00 |
| **Three-Way Matching** | `3WAY_QTY_OVERBILL` | Multi-table join comparing `invoice_lines.quantity_invoiced` against dock-accepted receipts `SUM(goods_receipts.quantity_received)`. Identifies billing for unreceived inventory. | **HIGH** | \$25,000.00 |
| **Three-Way Matching** | `3WAY_PRICE_VARIANCE` | Join between invoice lines and PO lines calculating `(Invoiced_Price - PO_Price) / PO_Price`. Flags variances exceeding 2% contractual tolerance. | **HIGH / MED** | \$1,600.00 |
| **Three-Way Matching** | `3WAY_MISSING_GR` | Identifies vendor invoices posted against purchase orders for physical goods where zero goods receipt records exist in warehouse receiving. | **HIGH** | \$16,000.00 |
| **Three-Way Matching** | `3WAY_NO_PO` | Filters invoices where `po_id IS NULL`, uncovering unauthorized maverick spend bypassing procurement review. | **MEDIUM** | \$24,500.00 |
| **Split Purchases** | `SPLIT_PURCHASE_VIOLATION` | Analytical window functions `LAG()` partitioned by buyer and vendor, ordered by date. Flags multiple POs created within 72 hours, each below the $10,000 authorization limit, but cumulatively exceeding it. | **HIGH** | \$56,800.00 |
| **Vendor Master** | `VND_DUP_BANK` | Group-by on bank routing and account numbers having count > 1. Discovers shell companies funneling funds into identical bank accounts. | **HIGH** | \$42,000.00 |
| **Vendor Master (SoD)** | `CONFLICT_EMP_VENDOR` | Fuzzy and exact join between employee HR master file and vendor records on bank account number and residential street address, uncovering employee self-dealing / phantom vendors. | **HIGH** | \$35,000.00 |
| **Vendor Master** | `VND_INACTIVE_ACTIVITY` | Join between POs and vendor master filtering on `vendor_status = 'INACTIVE'`, flagging sudden high-value disbursements to dormant suppliers. | **HIGH** | \$78,000.00 |
| **Payment Anomalies** | `PAY_UNMATCHED_NO_INV` | Treasury disbursement records where `invoice_id IS NULL`. Detects untracked wire disbursements. | **HIGH** | \$19,500.00 |
| **Payment Anomalies** | `PAY_OVERPAYMENT` | Compares `payments.payment_amount` against `invoices.invoice_amount`, flagging over-disbursements. | **HIGH** | \$4,500.00 |
| **Payment Anomalies** | `PAY_PREMATURE_DATE` | Date comparison identifying disbursements released prior to invoice date or approval date. | **MEDIUM** | \$8,500.00 |
| **Approval Limits** | `APPR_LIMIT_EXCEEDED` | Join between POs and employee authority master identifying transactions exceeding designated approval limits ($2,500 limit approver approving $68,000 order). | **HIGH** | \$1,041,840.00 |
| **Approval Limits** | `APPR_SELF_APPROVAL` | Segregation of Duties (SoD) violation check where `requester_id = approver_id`. | **HIGH** | \$95,500.00 |

---

## 🗂️ Repository Structure

```
Procure-to-Pay (P2P) Financial Controls & Continuous Monitoring/
├── data/
│   ├── raw/                           # Raw simulated enterprise CSV tables
│   │   ├── employees.csv              # Master employee & DoA signing limits
│   │   ├── vendors.csv                # Supplier master file & banking details
│   │   ├── purchase_orders.csv        # PO headers & approval routing
│   │   ├── purchase_order_lines.csv   # Item-level line amounts & categories
│   │   ├── goods_receipts.csv         # Physical warehouse receiving records
│   │   ├── invoices.csv               # Vendor invoice headers
│   │   ├── invoice_lines.csv          # Invoiced unit prices and quantities
│   │   └── payments.csv               # Disbursement ledger & bank details
│   ├── powerbi/                       # Formatted Star Schema tables for Power BI
│   │   ├── Dim_Date.csv               # Calendar table with fiscal attributes
│   │   ├── Dim_Employee.csv           # Employee dimension with signing limit
│   │   ├── Dim_Vendor.csv             # Vendor dimension with risk classification
│   │   ├── Fact_Purchase_Orders.csv   # PO spend fact
│   │   ├── Fact_Invoices.csv          # Invoice billing fact
│   │   ├── Fact_Payments.csv          # Cash disbursement fact
│   │   └── Fact_Control_Exceptions.csv# All 34 audit exceptions registry
│   ├── control_exceptions_registry.csv# Export of all identified audit exceptions
│   ├── vendor_risk_scorecard.csv      # Risk scoring & exposure per vendor
│   ├── executive_kpis.json            # Machine-readable high-level metrics
│   └── p2p_controls.db                # SQLite database with all tables & indexes
├── sql/
│   ├── schema_sqlite.sql              # Embedded SQLite DDL & indexing script
│   ├── schema_postgresql.sql          # Enterprise PostgreSQL DDL script
│   ├── 01_duplicate_invoices.sql      # Test 1: Exact, suspect & duplicate disbursements
│   ├── 02_three_way_matching.sql      # Test 2: Qty overbilling, price variance, non-PO
│   ├── 03_split_purchases.sql         # Test 3: Structuring below $10,000 threshold
│   ├── 04_vendor_anomalies_and_conflicts.sql # Test 4: Duplicate bank, conflict of interest
│   ├── 05_payment_anomalies.sql       # Test 5: Ghost payments, overpayments, timing
│   ├── 06_approval_violations.sql     # Test 6: Signing limit exceeded, self-approvals
│   └── 07_executive_risk_kpis.sql     # Executive KPI rollups & vendor exposure
├── src/
│   ├── generate_p2p_data.py           # Enterprise synthetic data generator
│   ├── audit_engine.py                # Automated Continuous Controls Monitoring engine
│   └── export_powerbi_data.py         # Star schema dimensional transformation pipeline
├── powerbi/
│   ├── dax_measures.dax               # Production DAX library (Spend, Risk %, MoM)
│   ├── powerbi_data_model.md          # Dimensional schema architecture & cardinality
│   └── dashboard_wireframe.md         # 3-Page layout blueprint & visual guide
├── reports/
│   ├── audit_findings_report.md       # Formal SOX / Internal Audit Findings Memo
│   └── interactive_dashboard.html     # Self-contained live browser dashboard
└── README.md                          # Comprehensive project documentation
```

---

## 🚀 Quickstart Guide

The pipeline runs out-of-the-box on standard Python 3.11+ with zero required external dependencies (uses Python standard library and SQLite3):

### 1. Generate Raw Enterprise P2P Dataset
```bash
python src/generate_p2p_data.py
```
*Generates 8 master CSV files in `data/raw/` and initializes `data/p2p_controls.db`.*

### 2. Run Continuous Controls Monitoring (CCM) Audit Engine
```bash
python src/audit_engine.py
```
*Executes all 6 control test batteries, logs findings to `control_exceptions`, and outputs the executive summary.*

### 3. Build Power BI Star Schema Tables
```bash
python src/export_powerbi_data.py
```
*Transforms raw tables into clean Dimensional and Fact tables in `data/powerbi/` ready for immediate Power BI drag-and-drop import.*

### 4. View the Interactive Dashboard
Double-click [`reports/interactive_dashboard.html`](file:///d:/Procure-to-Pay%20(P2P)%20Financial%20Controls%20&%20Continuous%20Monitoring/reports/interactive_dashboard.html) or open it in Google Chrome, Microsoft Edge, or Safari to explore the visual analytics.

---

## 📈 Power BI Star Schema & DAX Modeling

The dataset is modeled as a Kimball-style Star Schema with 3 Dimensions (`Dim_Date`, `Dim_Vendor`, `Dim_Employee`) and 4 Fact tables (`Fact_Purchase_Orders`, `Fact_Invoices`, `Fact_Payments`, `Fact_Control_Exceptions`).

### Key DAX Measures (from `powerbi/dax_measures.dax`):

```dax
// Total Disbursed Cash Outflow
Total Disbursed Amount = 
SUM('Fact_Payments'[PaymentAmount])

// Total Financial Exposure from Control Violations
Total Amount at Risk = 
SUM('Fact_Control_Exceptions'[AmountAtRisk])

// Percentage of Total Disbursements Vulnerable to Control Deficiencies
Financial Exposure Rate % = 
DIVIDE([Total Amount at Risk], [Total Disbursed Amount], 0)

// Duplicate Invoices Exposure
Duplicate Invoice Value = 
CALCULATE(
    SUM('Fact_Control_Exceptions'[AmountAtRisk]),
    'Fact_Control_Exceptions'[ControlCategory] = "Duplicate Invoices"
)

// Split Purchases Structured Within 72 Hours Below Threshold
Split Purchase Exposure = 
CALCULATE(
    SUM('Fact_Control_Exceptions'[AmountAtRisk]),
    'Fact_Control_Exceptions'[ControlCategory] = "Split Purchases"
)
```

---

## 💼 Resume Bullets & Interview Talking Points

### Resume Bullet Options:
- **Financial Controls & Continuous Monitoring:** *"Architected an automated Procure-to-Pay (P2P) Continuous Controls Monitoring (CCM) engine using SQL and Python, evaluating $12.7M in spend across 179 purchase orders to detect $1.8M in financial risk exposure across duplicate billings, three-way match variances, and split purchases."*
- **Audit Analytics & Fraud Detection:** *"Engineered analytical detection algorithms uncovering high-risk Segregation of Duties (SoD) breaches, including employee-vendor profile collisions (phantom vendors), duplicate vendor bank accounts, and $56K in structured split purchases evading managerial thresholds."*
- **Data Reconciliation & Three-Way Matching:** *"Designed automated three-way matching reconciliation logic across POs, goods receipts, and invoices, identifying quantity over-billing, unauthorized unit price inflation exceeding 2% contractual tolerance, and non-PO maverick spend."*
- **Business Intelligence & Reporting:** *"Developed an enterprise Power BI Star Schema data model and DAX measure library tracking financial exposure rates, vendor risk scores, and month-over-month exception velocity, complemented by a self-contained interactive dashboard."*

### Key Interview Discussion Topics:
1. **Translating Business Rules into Analytical SQL:** Explain how `LAG()` and cumulative window functions detect structuring/split purchases within rolling 72-hour windows, whereas traditional group-by queries fail.
2. **Preventive vs. Detective Financial Controls:** Discuss how Continuous Controls Monitoring (CCM) shifts internal audit from lagging annual sampling to near-real-time automated preventive interventions.
3. **Data Reconciliation at Scale:** Detail the join strategy between Purchase Orders, Warehouse Receiving logs, and Invoices to catch phantom deliveries and unit price inflation.
