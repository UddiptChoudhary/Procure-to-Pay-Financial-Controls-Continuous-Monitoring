"""
Master Pipeline Runner for Procure-to-Pay (P2P) Financial Controls Project
Executes the full end-to-end workflow:
1. Synthetic Data Generation & Database Seeding
2. Automated Exception Testing Engine (CCM)
3. Power BI Star Schema Transformation
4. Direct Execution of SQL Analytical Query Files with Formatted Results
"""

import os
import sys
import sqlite3
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "p2p_controls.db")
SQL_DIR = os.path.join(BASE_DIR, "sql")

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title.upper()}")
    print("="*80)

def run_command(cmd_args, step_name):
    print(f"\n>>> Running Step: {step_name}...")
    result = subprocess.run(cmd_args, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(" [Warning/Stderr]:", result.stderr.strip())
    if result.returncode != 0:
        print(f" [Error] Step failed with return code {result.returncode}")
        sys.exit(result.returncode)

def execute_sql_query(query_title, query_sql):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "-"*80)
    print(f" SQL AUDIT TEST: {query_title}")
    print("-"*80)
    
    try:
        cursor.execute(query_sql)
        rows = cursor.fetchall()
        if not rows:
            print(" [Result] No violations detected (Clean control condition).")
            return
            
        columns = rows[0].keys()
        # Calculate dynamic column widths
        widths = {col: len(col) for col in columns}
        data_rows = []
        for r in rows:
            row_dict = {}
            for col in columns:
                val = r[col]
                if isinstance(val, float):
                    val_str = f"{val:,.2f}"
                elif val is None:
                    val_str = "NULL"
                else:
                    val_str = str(val)
                row_dict[col] = val_str
                widths[col] = min(max(widths[col], len(val_str)), 45) # cap at 45 chars for neatness
            data_rows.append(row_dict)
            
        # Format Header
        header_line = " | ".join(col.ljust(widths[col])[:widths[col]] for col in columns)
        sep_line = "-+-".join("-" * widths[col] for col in columns)
        print(" " + header_line)
        print(" " + sep_line)
        
        # Format Data Rows (first 10 max)
        for r in data_rows[:10]:
            line = " | ".join(r[col].ljust(widths[col])[:widths[col]] for col in columns)
            print(" " + line)
            
        if len(data_rows) > 10:
            print(f" ... [Showing 10 of {len(data_rows)} exceptions]")
            
        print(f" Total Identified Exceptions: {len(rows)}")
    except Exception as e:
        print(f" [SQL Error]: {e}")
    finally:
        conn.close()

def run_sql_tests():
    print_header("Executing Direct Analytical SQL Control Tests Against Database")
    
    # 1. Exact & Suspect Duplicate Invoices
    sql_dup = """
        SELECT 
            'DUP_INV' AS TestCode,
            i1.vendor_id AS VendorID,
            i1.invoice_number AS InvoiceNum1,
            i2.invoice_number AS InvoiceNum2,
            i1.invoice_amount AS InvoiceAmount,
            i1.invoice_date AS Date1,
            i2.invoice_date AS Date2,
            ROUND(ABS(JULIANDAY(i2.invoice_date) - JULIANDAY(i1.invoice_date)), 0) AS DaysApart
        FROM invoices i1
        JOIN invoices i2 ON i1.vendor_id = i2.vendor_id 
            AND i1.invoice_amount = i2.invoice_amount 
            AND i1.invoice_id < i2.invoice_id
        WHERE ABS(JULIANDAY(i2.invoice_date) - JULIANDAY(i1.invoice_date)) <= 30;
    """
    execute_sql_query("Duplicate & Suspect Invoices (Same Vendor, Same Amount <= 30 Days)", sql_dup)

    # 2. Three-Way Matching Quantity Over-billing
    sql_3way_qty = """
        WITH Receipts AS (
            SELECT po_line_id, SUM(quantity_received) as tot_rec
            FROM goods_receipts WHERE condition_status = 'ACCEPTED'
            GROUP BY po_line_id
        )
        SELECT 
            i.invoice_number AS InvoiceNum,
            i.vendor_id AS VendorID,
            i.po_id AS PO_ID,
            il.item_description AS Item,
            il.quantity_invoiced AS BilledQty,
            COALESCE(r.tot_rec, 0) AS ReceivedQty,
            (il.quantity_invoiced - COALESCE(r.tot_rec, 0)) AS UnreceivedQtyBilled,
            ROUND((il.quantity_invoiced - COALESCE(r.tot_rec, 0)) * il.unit_price, 2) AS ExposureAmount
        FROM invoice_lines il
        JOIN invoices i ON il.invoice_id = i.invoice_id
        LEFT JOIN Receipts r ON il.po_line_id = r.po_line_id
        WHERE i.po_id IS NOT NULL AND il.quantity_invoiced > COALESCE(r.tot_rec, 0);
    """
    execute_sql_query("Three-Way Match: Quantity Over-billing (Invoiced Qty > Dock Received Qty)", sql_3way_qty)

    # 3. Split Purchases
    sql_split = """
        WITH ConsecutiveOrders AS (
            SELECT po.po_id, po.requester_id, e.first_name || ' ' || e.last_name as Requester,
                   e.approval_limit as LimitAmt, po.vendor_id, po.po_date, po.total_amount,
                   LAG(po.po_id, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) as PrevPO,
                   LAG(po.total_amount, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) as PrevAmt,
                   LAG(po.po_date, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) as PrevDate
            FROM purchase_orders po
            JOIN employees e ON po.requester_id = e.employee_id
            WHERE po.po_status = 'APPROVED'
        )
        SELECT Requester, LimitAmt, vendor_id, PrevPO, po_id AS CurrentPO, PrevDate, po_date AS CurrDate,
               PrevAmt, total_amount AS CurrAmt, (PrevAmt + total_amount) AS CombinedSpend
        FROM ConsecutiveOrders
        WHERE PrevPO IS NOT NULL AND (JULIANDAY(po_date) - JULIANDAY(PrevDate)) <= 3
          AND total_amount < 10000.00 AND PrevAmt < 10000.00
          AND (PrevAmt + total_amount) >= 10000.00;
    """
    execute_sql_query("Split Purchases: Structuring Orders Below $10,000 Authority Threshold", sql_split)

    # 4. Employee-Vendor Conflict of Interest
    sql_conflict = """
        SELECT 
            e.employee_id AS EmpID,
            e.first_name || ' ' || e.last_name AS EmployeeName,
            e.department AS Department,
            v.vendor_id AS VendorID,
            v.vendor_name AS VendorName,
            e.street_address AS SharedAddress,
            e.bank_account_number AS SharedBankAccount,
            (SELECT SUM(payment_amount) FROM payments WHERE vendor_id = v.vendor_id) AS DisbursedAmount
        FROM employees e
        JOIN vendors v ON e.bank_account_number = v.bank_account_number
            OR (LOWER(TRIM(e.street_address)) = LOWER(TRIM(v.street_address)));
    """
    execute_sql_query("Vendor Anomalies: Employee-Vendor Match (Conflict of Interest / Phantom Vendor)", sql_conflict)

    # 5. Approval Authorization Limit Exceeded
    sql_approval = """
        SELECT 
            po.po_id AS PO_ID,
            po.po_date AS PODate,
            po.department AS Department,
            e.first_name || ' ' || e.last_name AS ApproverName,
            e.job_title AS ApproverTitle,
            e.approval_limit AS AuthorizedLimit,
            po.total_amount AS ApprovedAmount,
            (po.total_amount - e.approval_limit) AS UnauthorizedExcess
        FROM purchase_orders po
        JOIN employees e ON po.approver_id = e.employee_id
        WHERE po.total_amount > e.approval_limit
        ORDER BY UnauthorizedExcess DESC;
    """
    execute_sql_query("Approval Violations: PO Total Exceeds Approver Delegated Authority Limit", sql_approval)

def main():
    python_exe = sys.executable
    
    print_header("Procure-to-Pay (P2P) Financial Controls Pipeline Execution")
    print(f" Python Executable: {python_exe}")
    print(f" Project Workspace: {BASE_DIR}")
    
    # Step 1: Data Generation
    run_command([python_exe, os.path.join(BASE_DIR, "src", "generate_p2p_data.py")], "1. Synthetic Enterprise Data Generator")
    
    # Step 2: Continuous Controls Monitoring Engine
    run_command([python_exe, os.path.join(BASE_DIR, "src", "audit_engine.py")], "2. Automated Audit Exception Engine")
    
    # Step 3: Power BI Star Schema Export
    run_command([python_exe, os.path.join(BASE_DIR, "src", "export_powerbi_data.py")], "3. Power BI Star Schema Transformation")
    
    # Step 4: SQL Control Tests
    run_sql_tests()
    
    print_header("Pipeline Execution Completed Successfully!")
    print(f" Database:             {DB_PATH}")
    print(f" Control Registry:     {os.path.join(DATA_DIR, 'control_exceptions_registry.csv')}")
    print(f" Power BI Datasets:    {os.path.join(DATA_DIR, 'powerbi')}")
    print(f" Audit Findings Memo:  {os.path.join(BASE_DIR, 'reports', 'audit_findings_report.md')}")
    print(f" Interactive Web UI:   {os.path.join(BASE_DIR, 'reports', 'interactive_dashboard.html')}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
