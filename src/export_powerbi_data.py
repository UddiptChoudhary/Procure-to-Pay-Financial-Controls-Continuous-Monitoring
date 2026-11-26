"""
Power BI Data Pipeline: Star Schema Transformation & Export
Extracts and structures P2P transaction data into a formal Star Schema for Power BI:
- Dim_Vendor
- Dim_Employee
- Dim_Date
- Fact_Purchase_Orders
- Fact_Invoices
- Fact_Payments
- Fact_Control_Exceptions
"""

import os
import csv
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
POWERBI_DIR = os.path.join(DATA_DIR, "powerbi")
DB_PATH = os.path.join(DATA_DIR, "p2p_controls.db")

os.makedirs(POWERBI_DIR, exist_ok=True)

def export_csv(filename, headers, rows):
    path = os.path.join(POWERBI_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f" [Power BI Star Schema] {filename}: {len(rows)} rows exported.")

def generate_dim_date():
    start = datetime(2023, 1, 1)
    end = datetime(2024, 1, 31)
    curr = start
    rows = []
    while curr <= end:
        date_str = curr.strftime("%Y-%m-%d")
        year = curr.year
        quarter = f"Q{(curr.month - 1) // 3 + 1}"
        month_num = curr.month
        month_name = curr.strftime("%B")
        month_year = curr.strftime("%b %Y")
        day_of_week = curr.strftime("%A")
        is_weekend = 1 if curr.weekday() >= 5 else 0
        rows.append([date_str, year, quarter, month_num, month_name, month_year, day_of_week, is_weekend])
        curr += timedelta(days=1)
    
    headers = ["Date", "Year", "Quarter", "MonthNumber", "MonthName", "MonthYear", "DayOfWeek", "IsWeekend"]
    export_csv("Dim_Date.csv", headers, rows)

def build_star_schema():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Dim_Vendor
    sql_vendor = """
        SELECT 
            v.vendor_id AS VendorKey,
            v.vendor_name AS VendorName,
            v.tax_id AS TaxID,
            v.bank_account_number AS BankAccountNumber,
            v.bank_routing_number AS BankRoutingNumber,
            v.payment_terms AS PaymentTerms,
            v.city AS City,
            v.state AS State,
            v.country AS Country,
            v.vendor_status AS VendorStatus,
            v.created_date AS VendorCreatedDate,
            CASE WHEN ce.vendor_id IS NOT NULL THEN 'High Risk' ELSE 'Standard' END AS RiskClassification
        FROM vendors v
        LEFT JOIN (SELECT DISTINCT vendor_id FROM control_exceptions) ce ON v.vendor_id = ce.vendor_id;
    """
    rows_v = [list(r) for r in cursor.execute(sql_vendor).fetchall()]
    headers_v = ["VendorKey", "VendorName", "TaxID", "BankAccountNumber", "BankRoutingNumber", "PaymentTerms", "City", "State", "Country", "VendorStatus", "VendorCreatedDate", "RiskClassification"]
    export_csv("Dim_Vendor.csv", headers_v, rows_v)

    # 2. Dim_Employee
    sql_emp = """
        SELECT 
            employee_id AS EmployeeKey,
            first_name || ' ' || last_name AS EmployeeName,
            department AS Department,
            job_title AS JobTitle,
            email AS Email,
            approval_limit AS AuthorizationLimit,
            city AS City,
            state AS State
        FROM employees;
    """
    rows_e = [list(r) for r in cursor.execute(sql_emp).fetchall()]
    headers_e = ["EmployeeKey", "EmployeeName", "Department", "JobTitle", "Email", "AuthorizationLimit", "City", "State"]
    export_csv("Dim_Employee.csv", headers_e, rows_e)

    # 3. Dim_Date
    generate_dim_date()

    # 4. Fact_Purchase_Orders
    sql_po = """
        SELECT 
            po.po_id AS POKeys,
            po.po_number AS PONumber,
            po.vendor_id AS VendorKey,
            po.requester_id AS RequesterEmployeeKey,
            po.approver_id AS ApproverEmployeeKey,
            po.po_date AS PODate,
            po.approval_date AS POApprovalDate,
            po.total_amount AS POTotalAmount,
            po.department AS Department,
            po.po_status AS POStatus
        FROM purchase_orders po;
    """
    rows_po = [list(r) for r in cursor.execute(sql_po).fetchall()]
    headers_po = ["POKeys", "PONumber", "VendorKey", "RequesterEmployeeKey", "ApproverEmployeeKey", "PODate", "POApprovalDate", "POTotalAmount", "Department", "POStatus"]
    export_csv("Fact_Purchase_Orders.csv", headers_po, rows_po)

    # 5. Fact_Invoices
    sql_inv = """
        SELECT 
            i.invoice_id AS InvoiceKey,
            i.invoice_number AS InvoiceNumber,
            i.vendor_id AS VendorKey,
            i.po_id AS POKeys,
            i.invoice_date AS InvoiceDate,
            i.received_date AS InvoiceReceivedDate,
            i.due_date AS InvoiceDueDate,
            i.invoice_amount AS InvoiceAmount,
            i.invoice_status AS InvoiceStatus,
            i.approved_by AS ApprovedByEmployeeKey,
            i.approval_date AS InvoiceApprovalDate
        FROM invoices i;
    """
    rows_inv = [list(r) for r in cursor.execute(sql_inv).fetchall()]
    headers_inv = ["InvoiceKey", "InvoiceNumber", "VendorKey", "POKeys", "InvoiceDate", "InvoiceReceivedDate", "InvoiceDueDate", "InvoiceAmount", "InvoiceStatus", "ApprovedByEmployeeKey", "InvoiceApprovalDate"]
    export_csv("Fact_Invoices.csv", headers_inv, rows_inv)

    # 6. Fact_Payments
    sql_pay = """
        SELECT 
            p.payment_id AS PaymentKey,
            p.payment_reference AS PaymentReference,
            p.invoice_id AS InvoiceKey,
            p.vendor_id AS VendorKey,
            p.payment_date AS PaymentDate,
            p.payment_amount AS PaymentAmount,
            p.payment_method AS PaymentMethod,
            p.bank_account_remitted AS BankAccountRemitted,
            p.payment_status AS PaymentStatus
        FROM payments p;
    """
    rows_pay = [list(r) for r in cursor.execute(sql_pay).fetchall()]
    headers_pay = ["PaymentKey", "PaymentReference", "InvoiceKey", "VendorKey", "PaymentDate", "PaymentAmount", "PaymentMethod", "BankAccountRemitted", "PaymentStatus"]
    export_csv("Fact_Payments.csv", headers_pay, rows_pay)

    # 7. Fact_Control_Exceptions
    sql_exc = """
        SELECT 
            exception_id AS ExceptionKey,
            test_code AS TestCode,
            test_name AS TestName,
            category AS ControlCategory,
            severity AS Severity,
            entity_type AS EntityType,
            entity_id AS EntityID,
            vendor_id AS VendorKey,
            amount_at_risk AS AmountAtRisk,
            violation_details AS ViolationDetails,
            detection_date AS DetectionDate,
            resolution_status AS ResolutionStatus
        FROM control_exceptions;
    """
    rows_exc = [list(r) for r in cursor.execute(sql_exc).fetchall()]
    headers_exc = ["ExceptionKey", "TestCode", "TestName", "ControlCategory", "Severity", "EntityType", "EntityID", "VendorKey", "AmountAtRisk", "ViolationDetails", "DetectionDate", "ResolutionStatus"]
    export_csv("Fact_Control_Exceptions.csv", headers_exc, rows_exc)

    conn.close()
    print("\n>>> All Power BI Star Schema Fact and Dimension tables generated successfully!")

if __name__ == "__main__":
    build_star_schema()
