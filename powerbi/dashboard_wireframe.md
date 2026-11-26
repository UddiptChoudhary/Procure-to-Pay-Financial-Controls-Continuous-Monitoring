# Power BI Dashboard Visual Wireframe & Layout Blueprint

This design corresponds directly to enterprise executive audit dashboards (such as the Databricks & Power BI Procurement Controls blueprint).

---

## Layout Grid (16:9 Aspect Ratio / 1920x1080)

```
+-------------------------------------------------------------------------------------------------------+
|  LOGO | PROCURE-TO-PAY (P2P) FINANCIAL CONTROLS & CONTINUOUS MONITORING DASHBOARD     [2023 Full Year]  |
|  Filters: [ Date Slicer: 2023 ]  [ Severity: High/Med ]  [ Department: All ]  [ Vendor Status: All ]  |
+-------------------------------------------------------------------------------------------------------+
|  [ KPI CARD 1 ]       |  [ KPI CARD 2 ]       |  [ KPI CARD 3 ]       |  [ KPI CARD 4 ]       |  [ KPI 5 ]    |
|  Total PO Spend       |  Total Disbursed      |  Total Amount at Risk |  Duplicate Invoices   |  Exceptions   |
|  $12.70M              |  $12.55M              |  $1.80M (14.4%)       |  $54.25K (5 Incidents)|  34 Violations|
+-------------------------------------------------------------------------------------------------------+
|  [ VISUAL 1: DONUT / BAR ]             |  [ VISUAL 2: STACKED COMBO CHART ]                            |
|  Financial Risk by Control Category    |  Monthly Anomaly Trend: Spend vs Amount at Risk                |
|  - Approval Violations: $1.14M (63%)   |  - Line: Total Disbursed Spend ($)                            |
|  - Vendor Anomalies:   $427K (24%)     |  - Bars: High Severity vs Medium Severity ($ at Risk)         |
|  - Three-Way Match:    $95.1K (5%)     |  (Shows sharp risk spikes in Aug-Nov)                         |
|  - Split Purchases:    $56.8K (3%)     |                                                               |
|  - Duplicate Invoices: $54.3K (3%)     |                                                               |
|  - Payment Anomalies:  $32.5K (2%)     |                                                               |
+----------------------------------------+---------------------------------------------------------------+
|  [ VISUAL 3: VENDOR RISK RANKING ]     |  [ VISUAL 4: AUDIT EXCEPTION DRILLDOWN TABLE ]                |
|  Top 5 Exposure Vendors                |  Detailed Forensic Transaction Log                            |
|  1. VND018 (Dormant Co):   $78.0K      |  [Date]  [Entity ID] [Vendor Name]  [Test Name] [Amount] [Sev]|
|  2. VND002 (Cloud Infra):  $76.5K      |  2023-04 INV-77881   Apex Tech     Exact Duplicate  $14.5K  H |
|  3. VND012 (NexGen IT):    $64.1K      |  2023-06 INV-44910-A Starlight Fac Near Duplicate    $8.8K  H |
|  4. VND017 (Phantom Vend): $35.0K      |  2023-09 VND017      Evergreen     Conflict of Int  $35.0K  H |
|  5. VND005 (Precision):    $28.0K      |  2023-08 PO-1165     Precision     Split Purchase   $28.0K  H |
+-------------------------------------------------------------------------------------------------------+
```

---

## Page Architecture

### Page 1: Executive Controls Summary (C-Suite & Audit Committee)
- **Audience:** CFO, Chief Audit Executive, Chief Procurement Officer.
- **Focus:** High-level exposure, financial impact percentage, SOX key controls status.
- **Key Visuals:**
  1. Top Banner KPI Cards with conditional formatting (Red badge when risk exposure > 5%).
  2. Donut chart of Risk by Category.
  3. Monthly exposure trend area chart.
  4. Vendor Risk Matrix (Disbursed Spend vs Risk Exposure %).

### Page 2: Three-Way Match & Invoice Variance Deep-Dive
- **Audience:** Accounts Payable Manager, Sourcing Category Leads.
- **Focus:** Line-item variances across Quantity, Unit Price, and Missing Delivery Receipts.
- **Key Visuals:**
  1. Invoiced Quantity vs Received Quantity variance bar chart.
  2. Price Variance Distribution (> 2% tolerance).
  3. Non-PO (Maverick Spend) vendor treemap.
  4. Invoice resolution status breakdown (On Hold, Pending Review, Under Investigation).

### Page 3: Forensic Audit & Fraud Risk (Internal Audit & Security)
- **Audience:** Internal Audit, Forensic Investigators, Legal/Compliance.
- **Focus:** Red flags, conflict of interest, structuring, phantom payees.
- **Key Visuals:**
  1. Employee-Vendor match network map / table (Shared address & bank routing).
  2. Split Purchase cluster analysis (Orders within 72 hours under $10,000 threshold).
  3. Inactive/Dormant vendor activity alerts.
  4. Full interactive exception grid with drill-through to raw transactional headers and lines.
