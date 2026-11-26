"""
Procure-to-Pay (P2P) Continuous Controls Monitoring (CCM) Audit Engine
Executes automated exception testing against the enterprise procurement data,
classifies control exceptions, calculates financial risk exposure,
and logs all violations to the centralized control_exceptions registry.
"""

import os
import csv
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "p2p_controls.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

class P2PContinuousControlsMonitor:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.exceptions = []

    def close(self):
        self.conn.close()

    def run_all_tests(self):
        print("="*75)
        print("  PROCURE-TO-PAY (P2P) CONTINUOUS CONTROLS MONITORING ENGINE")
        print("  Executing Automated Financial Exception Audits...")
        print("="*75)
        
        # Clear previous exception runs
        self.cursor.execute("DELETE FROM control_exceptions;")
        self.conn.commit()
        
        self.test_01_duplicate_invoices()
        self.test_02_three_way_matching()
        self.test_03_split_purchases()
        self.test_04_vendor_anomalies_and_conflicts()
        self.test_05_payment_anomalies()
        self.test_06_approval_violations()
        
        self.save_exceptions_to_db()
        self.generate_risk_scorecards()
        self.print_executive_summary()

    # -------------------------------------------------------------
    # 1. Duplicate Invoices & Disbursements
    # -------------------------------------------------------------
    def test_01_duplicate_invoices(self):
        # 1A. Exact Duplicates
        sql_exact = """
            SELECT vendor_id, invoice_number, COUNT(*) as cnt, MIN(invoice_id) as orig_id,
                   MAX(invoice_id) as dup_id, MIN(invoice_date) as orig_dt, MAX(invoice_date) as dup_dt,
                   invoice_amount
            FROM invoices
            GROUP BY vendor_id, invoice_number
            HAVING COUNT(*) > 1;
        """
        for row in self.cursor.execute(sql_exact):
            exposure = round((row["cnt"] - 1) * row["invoice_amount"], 2)
            self.exceptions.append({
                "test_code": "DUP_INV_EXACT",
                "test_name": "Exact Duplicate Invoice",
                "category": "Duplicate Invoices",
                "severity": "HIGH",
                "entity_type": "INVOICE",
                "entity_id": row["dup_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": exposure,
                "violation_details": f"Invoice #{row['invoice_number']} submitted {row['cnt']} times. Matched with original {row['orig_id']} on {row['orig_dt']}.",
                "detection_date": row["dup_dt"]
            })

        # 1B. Suspect Near-Duplicate Invoices (Same vendor, same amount within 30 days)
        sql_suspect = """
            SELECT i1.invoice_id AS id1, i2.invoice_id AS id2, i1.vendor_id,
                   i1.invoice_number AS num1, i2.invoice_number AS num2,
                   i1.invoice_amount, i1.invoice_date AS dt1, i2.invoice_date AS dt2,
                   ROUND(ABS(JULIANDAY(i2.invoice_date) - JULIANDAY(i1.invoice_date)), 1) AS days_diff
            FROM invoices i1
            JOIN invoices i2 ON i1.vendor_id = i2.vendor_id 
                AND i1.invoice_amount = i2.invoice_amount 
                AND i1.invoice_id < i2.invoice_id
                AND i1.invoice_number != i2.invoice_number
            WHERE ABS(JULIANDAY(i2.invoice_date) - JULIANDAY(i1.invoice_date)) <= 30;
        """
        for row in self.cursor.execute(sql_suspect):
            self.exceptions.append({
                "test_code": "DUP_INV_SUSPECT",
                "test_name": "Suspect Near-Duplicate Invoice",
                "category": "Duplicate Invoices",
                "severity": "HIGH",
                "entity_type": "INVOICE",
                "entity_id": row["id2"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["invoice_amount"],
                "violation_details": f"Identical amount (${row['invoice_amount']:,.2f}) to vendor within {row['days_diff']} days. Invoice #{row['num2']} vs #{row['num1']}.",
                "detection_date": row["dt2"]
            })

        # 1C. Duplicate Payment on Single Invoice
        sql_dup_pay = """
            SELECT invoice_id, vendor_id, COUNT(*) as cnt, SUM(payment_amount) as total_paid,
                   MIN(payment_date) as first_dt, MAX(payment_date) as last_dt
            FROM payments
            WHERE invoice_id IS NOT NULL AND payment_status = 'COMPLETED'
            GROUP BY invoice_id, vendor_id
            HAVING COUNT(*) > 1;
        """
        for row in self.cursor.execute(sql_dup_pay):
            # Fetch invoice amount
            inv_row = self.cursor.execute("SELECT invoice_amount FROM invoices WHERE invoice_id = ?", (row["invoice_id"],)).fetchone()
            inv_amt = inv_row["invoice_amount"] if inv_row else 0.0
            excess_loss = round(row["total_paid"] - inv_amt, 2)
            self.exceptions.append({
                "test_code": "DUP_PAYMENT_INV",
                "test_name": "Duplicate Payment on Single Invoice",
                "category": "Duplicate Invoices",
                "severity": "HIGH",
                "entity_type": "PAYMENT",
                "entity_id": row["invoice_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": excess_loss if excess_loss > 0 else row["total_paid"] / 2.0,
                "violation_details": f"Invoice {row['invoice_id']} paid {row['cnt']} times. Total disbursed: ${row['total_paid']:,.2f} vs invoice amount ${inv_amt:,.2f}.",
                "detection_date": row["last_dt"]
            })

    # -------------------------------------------------------------
    # 2. Three-Way Matching Violations
    # -------------------------------------------------------------
    def test_02_three_way_matching(self):
        # 2A. Invoiced Qty > Received Qty
        sql_qty = """
            WITH Receipts AS (
                SELECT po_line_id, SUM(quantity_received) as tot_rec
                FROM goods_receipts WHERE condition_status = 'ACCEPTED'
                GROUP BY po_line_id
            )
            SELECT i.invoice_id, i.invoice_number, i.vendor_id, i.po_id, il.item_description,
                   il.quantity_invoiced, COALESCE(r.tot_rec, 0) as tot_rec, il.unit_price,
                   i.invoice_date
            FROM invoice_lines il
            JOIN invoices i ON il.invoice_id = i.invoice_id
            LEFT JOIN Receipts r ON il.po_line_id = r.po_line_id
            WHERE i.po_id IS NOT NULL AND il.quantity_invoiced > COALESCE(r.tot_rec, 0);
        """
        for row in self.cursor.execute(sql_qty):
            qty_var = row["quantity_invoiced"] - row["tot_rec"]
            exposure = round(qty_var * row["unit_price"], 2)
            self.exceptions.append({
                "test_code": "3WAY_QTY_OVERBILL",
                "test_name": "Quantity Over-billing Variance",
                "category": "Three-Way Matching",
                "severity": "HIGH",
                "entity_type": "INVOICE",
                "entity_id": row["invoice_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": exposure,
                "violation_details": f"Invoiced {row['quantity_invoiced']} units of '{row['item_description']}' but only {row['tot_rec']} units received at dock.",
                "detection_date": row["invoice_date"]
            })

        # 2B. Invoiced Unit Price > PO Contracted Unit Price (>2%)
        sql_price = """
            SELECT i.invoice_id, i.invoice_number, i.vendor_id, i.po_id, il.item_description,
                   il.quantity_invoiced, pol.unit_price as po_price, il.unit_price as inv_price,
                   ROUND(((il.unit_price - pol.unit_price) / pol.unit_price) * 100.0, 2) as var_pct,
                   ROUND((il.unit_price - pol.unit_price) * il.quantity_invoiced, 2) as var_exposure,
                   i.invoice_date
            FROM invoice_lines il
            JOIN invoices i ON il.invoice_id = i.invoice_id
            JOIN purchase_order_lines pol ON il.po_line_id = pol.po_line_id
            WHERE il.unit_price > pol.unit_price * 1.02;
        """
        for row in self.cursor.execute(sql_price):
            self.exceptions.append({
                "test_code": "3WAY_PRICE_VARIANCE",
                "test_name": "Price Exceeds Purchase Order",
                "category": "Three-Way Matching",
                "severity": "HIGH" if row["var_pct"] >= 10.0 else "MEDIUM",
                "entity_type": "INVOICE",
                "entity_id": row["invoice_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["var_exposure"],
                "violation_details": f"Unit price variance on '{row['item_description']}': billed @ ${row['inv_price']:,.2f} vs PO @ ${row['po_price']:,.2f} (+{row['var_pct']}%).",
                "detection_date": row["invoice_date"]
            })

        # 2C. Invoice Without Goods Receipt
        sql_no_gr = """
            SELECT i.invoice_id, i.invoice_number, i.vendor_id, i.po_id, i.invoice_date, i.invoice_amount
            FROM invoices i
            LEFT JOIN goods_receipts gr ON i.po_id = gr.po_id
            WHERE i.po_id IS NOT NULL
            GROUP BY i.invoice_id, i.invoice_number, i.vendor_id, i.po_id, i.invoice_date, i.invoice_amount
            HAVING COUNT(gr.gr_id) = 0;
        """
        for row in self.cursor.execute(sql_no_gr):
            self.exceptions.append({
                "test_code": "3WAY_MISSING_GR",
                "test_name": "Invoice Without Goods Receipt",
                "category": "Three-Way Matching",
                "severity": "HIGH",
                "entity_type": "INVOICE",
                "entity_id": row["invoice_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["invoice_amount"],
                "violation_details": f"Invoice #{row['invoice_number']} for ${row['invoice_amount']:,.2f} has zero goods receipt delivery confirmations.",
                "detection_date": row["invoice_date"]
            })

        # 2D. Non-PO Invoices (Maverick Spend)
        sql_no_po = """
            SELECT invoice_id, invoice_number, vendor_id, invoice_date, invoice_amount
            FROM invoices
            WHERE po_id IS NULL;
        """
        for row in self.cursor.execute(sql_no_po):
            self.exceptions.append({
                "test_code": "3WAY_NO_PO",
                "test_name": "Maverick Spend - Non-PO Invoice",
                "category": "Three-Way Matching",
                "severity": "MEDIUM",
                "entity_type": "INVOICE",
                "entity_id": row["invoice_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["invoice_amount"],
                "violation_details": f"Invoice #{row['invoice_number']} for ${row['invoice_amount']:,.2f} processed with no associated purchase order requisition.",
                "detection_date": row["invoice_date"]
            })

    # -------------------------------------------------------------
    # 3. Split Purchases (Evading Authorization Thresholds)
    # -------------------------------------------------------------
    def test_03_split_purchases(self):
        sql_split = """
            WITH ConsecutiveOrders AS (
                SELECT po.po_id, po.requester_id, e.first_name || ' ' || e.last_name as req_name,
                       e.approval_limit, po.vendor_id, po.po_date, po.total_amount,
                       LAG(po.po_id, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) as prev_id,
                       LAG(po.po_date, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) as prev_dt,
                       LAG(po.total_amount, 1) OVER (PARTITION BY po.requester_id, po.vendor_id ORDER BY po.po_date, po.po_id) as prev_amt
                FROM purchase_orders po
                JOIN employees e ON po.requester_id = e.employee_id
                WHERE po.po_status = 'APPROVED'
            )
            SELECT requester_id, req_name, approval_limit, vendor_id, prev_id, po_id, prev_dt, po_date,
                   ROUND(JULIANDAY(po_date) - JULIANDAY(prev_dt), 1) as days_diff,
                   prev_amt, total_amount, (prev_amt + total_amount) as combined_amt
            FROM ConsecutiveOrders
            WHERE prev_id IS NOT NULL
              AND (JULIANDAY(po_date) - JULIANDAY(prev_dt)) <= 3
              AND total_amount < 10000.00 AND prev_amt < 10000.00
              AND (prev_amt + total_amount) >= 10000.00;
        """
        for row in self.cursor.execute(sql_split):
            excess = round(row["combined_amt"] - row["approval_limit"], 2)
            self.exceptions.append({
                "test_code": "SPLIT_PURCHASE_VIOLATION",
                "test_name": "Split Purchase Below Authorization Limit",
                "category": "Split Purchases",
                "severity": "HIGH",
                "entity_type": "PO",
                "entity_id": row["po_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["combined_amt"],
                "violation_details": f"Buyer {row['req_name']} structured multiple POs ({row['prev_id']} & {row['po_id']}) totaling ${row['combined_amt']:,.2f} within {row['days_diff']} days below $10k limit.",
                "detection_date": row["po_date"]
            })

    # -------------------------------------------------------------
    # 4. Vendor Anomalies & Conflict of Interest
    # -------------------------------------------------------------
    def test_04_vendor_anomalies_and_conflicts(self):
        # 4A. Duplicate Vendor Bank Accounts
        sql_dup_bank = """
            SELECT bank_routing_number, bank_account_number, COUNT(*) as cnt,
                   GROUP_CONCAT(vendor_id || ' (' || vendor_name || ')', ' | ') as vendors
            FROM vendors
            GROUP BY bank_routing_number, bank_account_number
            HAVING COUNT(*) > 1;
        """
        for row in self.cursor.execute(sql_dup_bank):
            # Sum payments disbursed to this bank account
            pay_row = self.cursor.execute("""
                SELECT COALESCE(SUM(p.payment_amount), 0) as tot_disbursed
                FROM payments p
                JOIN vendors v ON p.vendor_id = v.vendor_id
                WHERE v.bank_account_number = ?;
            """, (row["bank_account_number"],)).fetchone()
            tot_disbursed = pay_row["tot_disbursed"] if pay_row else 0.0
            self.exceptions.append({
                "test_code": "VND_DUP_BANK",
                "test_name": "Duplicate Vendor Bank Account",
                "category": "Vendor Anomalies",
                "severity": "HIGH",
                "entity_type": "VENDOR",
                "entity_id": row["bank_account_number"],
                "vendor_id": "MULTIPLE",
                "amount_at_risk": tot_disbursed,
                "violation_details": f"Identical routing/account {row['bank_account_number']} shared by {row['cnt']} entities: {row['vendors']}.",
                "detection_date": "2023-12-01"
            })

        # 4B. Employee-Vendor Match (Conflict of Interest / Phantom Vendor)
        sql_conflict = """
            SELECT e.employee_id, e.first_name || ' ' || e.last_name as emp_name, e.department,
                   v.vendor_id, v.vendor_name, e.street_address, e.bank_account_number
            FROM employees e
            JOIN vendors v ON e.bank_account_number = v.bank_account_number
                OR (LOWER(TRIM(e.street_address)) = LOWER(TRIM(v.street_address)) AND LOWER(TRIM(e.postal_code)) = LOWER(TRIM(v.postal_code)));
        """
        for row in self.cursor.execute(sql_conflict):
            pay_row = self.cursor.execute("SELECT COALESCE(SUM(payment_amount), 0) as tot FROM payments WHERE vendor_id = ?", (row["vendor_id"],)).fetchone()
            tot = pay_row["tot"] if pay_row else 0.0
            self.exceptions.append({
                "test_code": "CONFLICT_EMP_VENDOR",
                "test_name": "Employee-Vendor Match (Conflict of Interest)",
                "category": "Vendor Anomalies",
                "severity": "HIGH",
                "entity_type": "VENDOR",
                "entity_id": row["vendor_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": tot,
                "violation_details": f"Employee {row['emp_name']} ({row['employee_id']}, {row['department']}) personal profile matches vendor {row['vendor_name']} ({row['vendor_id']}). Address/Bank Match.",
                "detection_date": "2023-09-15"
            })

        # 4C. Inactive/Dormant Vendor Spend
        sql_inactive = """
            SELECT po.po_id, po.po_date, po.vendor_id, v.vendor_name, po.total_amount
            FROM purchase_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            WHERE v.vendor_status = 'INACTIVE';
        """
        for row in self.cursor.execute(sql_inactive):
            self.exceptions.append({
                "test_code": "VND_INACTIVE_ACTIVITY",
                "test_name": "Transaction on Inactive/Dormant Vendor",
                "category": "Vendor Anomalies",
                "severity": "HIGH",
                "entity_type": "PO",
                "entity_id": row["po_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["total_amount"],
                "violation_details": f"PO {row['po_id']} issued for ${row['total_amount']:,.2f} to vendor {row['vendor_name']} with INACTIVE master status.",
                "detection_date": row["po_date"]
            })

    # -------------------------------------------------------------
    # 5. Payment Anomalies
    # -------------------------------------------------------------
    def test_05_payment_anomalies(self):
        # 5A. Payments Without Invoice
        sql_ghost = """
            SELECT payment_id, payment_reference, vendor_id, payment_date, payment_amount
            FROM payments
            WHERE invoice_id IS NULL;
        """
        for row in self.cursor.execute(sql_ghost):
            self.exceptions.append({
                "test_code": "PAY_UNMATCHED_NO_INV",
                "test_name": "Ghost Payment Without Invoice",
                "category": "Payment Anomalies",
                "severity": "HIGH",
                "entity_type": "PAYMENT",
                "entity_id": row["payment_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["payment_amount"],
                "violation_details": f"Disbursement {row['payment_reference']} of ${row['payment_amount']:,.2f} executed without any matching invoice reference.",
                "detection_date": row["payment_date"]
            })

        # 5B. Overpayments
        sql_over = """
            SELECT p.payment_id, p.payment_reference, p.invoice_id, p.vendor_id, i.invoice_amount,
                   p.payment_amount, ROUND(p.payment_amount - i.invoice_amount, 2) as overpay, p.payment_date
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.invoice_id
            WHERE p.payment_amount > i.invoice_amount;
        """
        for row in self.cursor.execute(sql_over):
            self.exceptions.append({
                "test_code": "PAY_OVERPAYMENT",
                "test_name": "Invoice Overpayment Variance",
                "category": "Payment Anomalies",
                "severity": "HIGH",
                "entity_type": "PAYMENT",
                "entity_id": row["payment_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["overpay"],
                "violation_details": f"Disbursed ${row['payment_amount']:,.2f} on invoice {row['invoice_id']} billed at ${row['invoice_amount']:,.2f} (Overpaid by ${row['overpay']:,.2f}).",
                "detection_date": row["payment_date"]
            })

        # 5C. Premature Payments
        sql_premature = """
            SELECT p.payment_id, p.payment_reference, p.invoice_id, p.vendor_id, p.payment_date,
                   i.invoice_date, p.payment_amount, ROUND(JULIANDAY(i.invoice_date) - JULIANDAY(p.payment_date), 1) as days_prior
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.invoice_id
            WHERE p.payment_date < i.invoice_date;
        """
        for row in self.cursor.execute(sql_premature):
            self.exceptions.append({
                "test_code": "PAY_PREMATURE_DATE",
                "test_name": "Premature Disbursement Before Invoice",
                "category": "Payment Anomalies",
                "severity": "MEDIUM",
                "entity_type": "PAYMENT",
                "entity_id": row["payment_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["payment_amount"],
                "violation_details": f"Payment executed on {row['payment_date']}, which is {row['days_prior']} days prior to invoice date {row['invoice_date']}.",
                "detection_date": row["payment_date"]
            })

    # -------------------------------------------------------------
    # 6. Approval & Authority Violations
    # -------------------------------------------------------------
    def test_06_approval_violations(self):
        # 6A. Approval Limit Exceeded
        sql_limit = """
            SELECT po.po_id, po.po_number, po.vendor_id, po.approver_id, e.first_name || ' ' || e.last_name as approver_name,
                   e.approval_limit, po.total_amount, ROUND(po.total_amount - e.approval_limit, 2) as excess,
                   po.po_date
            FROM purchase_orders po
            JOIN employees e ON po.approver_id = e.employee_id
            WHERE po.total_amount > e.approval_limit;
        """
        for row in self.cursor.execute(sql_limit):
            self.exceptions.append({
                "test_code": "APPR_LIMIT_EXCEEDED",
                "test_name": "Approval Limit Exceeded",
                "category": "Approval Violations",
                "severity": "HIGH",
                "entity_type": "PO",
                "entity_id": row["po_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["total_amount"],
                "violation_details": f"Approver {row['approver_name']} authorized ${row['total_amount']:,.2f} exceeding their financial signing limit of ${row['approval_limit']:,.2f}.",
                "detection_date": row["po_date"]
            })

        # 6B. Self-Approval Violation
        sql_self = """
            SELECT po.po_id, po.po_number, po.vendor_id, po.requester_id, e.first_name || ' ' || e.last_name as emp_name,
                   po.total_amount, po.po_date
            FROM purchase_orders po
            JOIN employees e ON po.requester_id = e.employee_id
            WHERE po.requester_id = po.approver_id;
        """
        for row in self.cursor.execute(sql_self):
            self.exceptions.append({
                "test_code": "APPR_SELF_APPROVAL",
                "test_name": "Self-Approval SoD Violation",
                "category": "Approval Violations",
                "severity": "HIGH",
                "entity_type": "PO",
                "entity_id": row["po_id"],
                "vendor_id": row["vendor_id"],
                "amount_at_risk": row["total_amount"],
                "violation_details": f"Employee {row['emp_name']} self-approved PO {row['po_id']} for ${row['total_amount']:,.2f} in violation of Segregation of Duties.",
                "detection_date": row["po_date"]
            })

    # -------------------------------------------------------------
    # Record to DB and Generate Deliverables
    # -------------------------------------------------------------
    def save_exceptions_to_db(self):
        sql_insert = """
            INSERT INTO control_exceptions 
            (test_code, test_name, category, severity, entity_type, entity_id, vendor_id, amount_at_risk, violation_details, detection_date, resolution_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN');
        """
        records = [
            (e["test_code"], e["test_name"], e["category"], e["severity"], e["entity_type"],
             e["entity_id"], e["vendor_id"], e["amount_at_risk"], e["violation_details"], e["detection_date"])
            for e in self.exceptions
        ]
        self.cursor.executemany(sql_insert, records)
        self.conn.commit()

        # Export CSV
        exc_csv_path = os.path.join(DATA_DIR, "control_exceptions_registry.csv")
        headers = ["exception_id", "test_code", "test_name", "category", "severity", "entity_type", "entity_id", "vendor_id", "amount_at_risk", "violation_details", "detection_date", "resolution_status"]
        with open(exc_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for idx, e in enumerate(self.exceptions, 1):
                writer.writerow([idx, e["test_code"], e["test_name"], e["category"], e["severity"], e["entity_type"], e["entity_id"], e["vendor_id"], e["amount_at_risk"], e["violation_details"], e["detection_date"], "OPEN"])

    def generate_risk_scorecards(self):
        # 1. Vendor Risk Scorecard
        sql_vendor_scorecard = """
            SELECT 
                v.vendor_id,
                v.vendor_name,
                v.vendor_status,
                COUNT(ce.exception_id) AS total_exceptions,
                ROUND(SUM(ce.amount_at_risk), 2) AS total_amount_at_risk,
                COALESCE((SELECT SUM(payment_amount) FROM payments WHERE vendor_id = v.vendor_id), 0) AS total_disbursed,
                CASE 
                    WHEN COUNT(ce.exception_id) >= 3 OR SUM(ce.amount_at_risk) > 50000 THEN 'CRITICAL'
                    WHEN COUNT(ce.exception_id) >= 1 THEN 'ELEVATED'
                    ELSE 'LOW_RISK'
                END AS risk_tier
            FROM vendors v
            LEFT JOIN control_exceptions ce ON v.vendor_id = ce.vendor_id
            GROUP BY v.vendor_id, v.vendor_name, v.vendor_status
            ORDER BY total_amount_at_risk DESC;
        """
        rows = [dict(r) for r in self.cursor.execute(sql_vendor_scorecard).fetchall()]
        scorecard_csv = os.path.join(DATA_DIR, "vendor_risk_scorecard.csv")
        with open(scorecard_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        # 2. Executive KPIs JSON
        total_spend = self.cursor.execute("SELECT SUM(payment_amount) as s FROM payments;").fetchone()["s"] or 0.0
        po_spend = self.cursor.execute("SELECT SUM(total_amount) as s FROM purchase_orders;").fetchone()["s"] or 0.0
        dup_inv_value = self.cursor.execute("SELECT SUM(amount_at_risk) as s FROM control_exceptions WHERE category = 'Duplicate Invoices';").fetchone()["s"] or 0.0
        total_at_risk = self.cursor.execute("SELECT SUM(amount_at_risk) as s FROM control_exceptions;").fetchone()["s"] or 0.0
        exc_count = len(self.exceptions)

        kpis = {
            "total_procurement_po_spend": round(po_spend, 2),
            "total_disbursements_paid": round(total_spend, 2),
            "total_control_exceptions": exc_count,
            "total_financial_amount_at_risk": round(total_at_risk, 2),
            "duplicate_invoice_value_at_risk": round(dup_inv_value, 2),
            "risk_exposure_percentage": round((total_at_risk / total_spend) * 100.0, 2) if total_spend > 0 else 0.0,
            "generated_timestamp": datetime.now().isoformat()
        }
        with open(os.path.join(DATA_DIR, "executive_kpis.json"), "w", encoding="utf-8") as f:
            json.dump(kpis, f, indent=4)

    def print_executive_summary(self):
        kpi_path = os.path.join(DATA_DIR, "executive_kpis.json")
        with open(kpi_path, "r", encoding="utf-8") as f:
            kpis = json.load(f)

        print("\n" + "="*75)
        print(" CONTINUOUS CONTROLS MONITORING (CCM) - AUDIT EXECUTIVE SUMMARY")
        print("="*75)
        print(f" Total Procurement Spend (POs):       ${kpis['total_procurement_po_spend']:>14,.2f}")
        print(f" Total Payments Disbursed:            ${kpis['total_disbursements_paid']:>14,.2f}")
        print(f" Total Identified Control Exceptions: {kpis['total_control_exceptions']:>15d}")
        print(f" Total Financial Amount at Risk:      ${kpis['total_financial_amount_at_risk']:>14,.2f}")
        print(f" Duplicate Invoice Value Detected:    ${kpis['duplicate_invoice_value_at_risk']:>14,.2f}")
        print(f" Financial Risk Exposure Ratio:       {kpis['risk_exposure_percentage']:>14.2f}%")
        print("-"*75)

        print("\nControl Exception Distribution by Category:")
        cat_sql = """
            SELECT category, severity, COUNT(*) as cnt, ROUND(SUM(amount_at_risk), 2) as risk_amt
            FROM control_exceptions
            GROUP BY category, severity
            ORDER BY risk_amt DESC;
        """
        print(f" {'Category':<26} {'Severity':<10} {'Exceptions':<12} {'Amount at Risk':>16}")
        print(" " + "-"*68)
        for r in self.cursor.execute(cat_sql):
            print(f" {r['category']:<26} {r['severity']:<10} {r['cnt']:<12} ${r['risk_amt']:>15,.2f}")
        print("="*75 + "\n")

if __name__ == "__main__":
    monitor = P2PContinuousControlsMonitor()
    monitor.run_all_tests()
    monitor.close()
