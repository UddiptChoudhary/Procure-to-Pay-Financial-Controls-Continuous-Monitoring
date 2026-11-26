# Power BI Star Schema Data Model Specification

## Architecture Overview

The P2P Continuous Controls Monitoring model uses a classic Kimball-style dimensional **Star Schema** with explicit fact tables representing transactional milestones and an exception fact table representing analytical findings.

```
                  +-------------------+
                  |     Dim_Date      |
                  +-------------------+
                     |      |      |
        +------------+      |      +------------+
        |                   |                   |
        v                   v                   v
+-------------------+ +-------------------+ +-------------------------+
|Fact_Purchase_Orders| |   Fact_Invoices   | | Fact_Control_Exceptions |
+-------------------+ +-------------------+ +-------------------------+
        |                   |                   ^
        |   +---------------+                   |
        v   v                                   |
+-------------------+                           |
|   Fact_Payments   |                           |
+-------------------+                           |
        |                                       |
        +------------------+--------------------+
                           |
                           v
                  +-------------------+
                  |    Dim_Vendor     |
                  +-------------------+
                           ^
                           |
                  +-------------------+
                  |   Dim_Employee    |
                  +-------------------+
```

---

## Dimension Tables

### 1. `Dim_Date` (Role-Playing Calendar)
- **Primary Key:** `Date` (YYYY-MM-DD)
- **Attributes:** `Year`, `Quarter`, `MonthNumber`, `MonthName`, `MonthYear`, `DayOfWeek`, `IsWeekend`
- **Relationships:**
  - `Dim_Date[Date]` 1 -> $\infty$ `Fact_Purchase_Orders[PODate]` (Active)
  - `Dim_Date[Date]` 1 -> $\infty$ `Fact_Invoices[InvoiceDate]` (Active)
  - `Dim_Date[Date]` 1 -> $\infty$ `Fact_Payments[PaymentDate]` (Active)
  - `Dim_Date[Date]` 1 -> $\infty$ `Fact_Control_Exceptions[DetectionDate]` (Active)

### 2. `Dim_Vendor` (Supplier Master Data)
- **Primary Key:** `VendorKey` (e.g., VND001)
- **Attributes:** `VendorName`, `TaxID`, `BankAccountNumber`, `BankRoutingNumber`, `PaymentTerms`, `City`, `State`, `Country`, `VendorStatus`, `VendorCreatedDate`, `RiskClassification`
- **Relationships:**
  - `Dim_Vendor[VendorKey]` 1 -> $\infty$ `Fact_Purchase_Orders[VendorKey]`
  - `Dim_Vendor[VendorKey]` 1 -> $\infty$ `Fact_Invoices[VendorKey]`
  - `Dim_Vendor[VendorKey]` 1 -> $\infty$ `Fact_Payments[VendorKey]`
  - `Dim_Vendor[VendorKey]` 1 -> $\infty$ `Fact_Control_Exceptions[VendorKey]` (Allow bi-directional or single cross-filter)

### 3. `Dim_Employee` (Organizational Hierarchy & DoA)
- **Primary Key:** `EmployeeKey` (e.g., EMP001)
- **Attributes:** `EmployeeName`, `Department`, `JobTitle`, `Email`, `AuthorizationLimit`, `City`, `State`
- **Relationships:**
  - `Dim_Employee[EmployeeKey]` 1 -> $\infty$ `Fact_Purchase_Orders[RequesterEmployeeKey]`
  - `Dim_Employee[EmployeeKey]` 1 -> $\infty$ `Fact_Purchase_Orders[ApproverEmployeeKey]` (Inactive / Role-playing)
  - `Dim_Employee[EmployeeKey]` 1 -> $\infty$ `Fact_Invoices[ApprovedByEmployeeKey]`

---

## Fact Tables

### 1. `Fact_Purchase_Orders`
- **Grain:** One record per Purchase Order header.
- **Foreign Keys:** `VendorKey`, `RequesterEmployeeKey`, `ApproverEmployeeKey`, `PODate`
- **Measures:** `POTotalAmount`

### 2. `Fact_Invoices`
- **Grain:** One record per Vendor Invoice header.
- **Foreign Keys:** `VendorKey`, `POKeys`, `ApprovedByEmployeeKey`, `InvoiceDate`
- **Measures:** `InvoiceAmount`

### 3. `Fact_Payments`
- **Grain:** One record per disbursement executed.
- **Foreign Keys:** `InvoiceKey`, `VendorKey`, `PaymentDate`
- **Measures:** `PaymentAmount`

### 4. `Fact_Control_Exceptions` (Audit Analytics Registry)
- **Grain:** One record per detected internal financial control violation.
- **Foreign Keys:** `VendorKey`, `DetectionDate`
- **Attributes:** `ExceptionKey`, `TestCode`, `TestName`, `ControlCategory`, `Severity`, `EntityType`, `EntityID`, `ViolationDetails`, `ResolutionStatus`
- **Measures:** `AmountAtRisk`

---

## Cardinality & Cross-Filtering Strategy
- All Dimension-to-Fact relationships are set to **1-to-Many ($1:*$)**.
- Cross filter direction is set to **Single** (Dimension filters Fact), avoiding ambiguous circular filter paths.
- For vendor exception cross-filtering, `Fact_Control_Exceptions` links directly to `Dim_Vendor[VendorKey]`.
