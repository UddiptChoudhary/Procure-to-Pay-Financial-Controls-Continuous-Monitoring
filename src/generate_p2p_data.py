"""
Procure-to-Pay (P2P) Enterprise Synthetic Data Generator
Generates a realistic enterprise procurement dataset spanning 12-24 months
with deliberate, calibrated financial control violations:
1. Duplicate Invoices (Exact & Suspect)
2. Three-Way Matching Mismatches (Qty, Price, Missing GR, Missing PO)
3. Split Purchases (Evading approval thresholds)
4. Vendor Anomalies (Duplicate bank accounts, Employee-Vendor address/bank match)
5. Payment Anomalies (Unmatched payments, Overpayments, Premature payments)
6. Approval Violations (Exceeding approval limits, Self-approvals)
"""

import os
import csv
import json
import sqlite3
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Set fixed seed for deterministic audit reproducibility
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
DB_PATH = os.path.join(DATA_DIR, "p2p_controls.db")
SQL_SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema_sqlite.sql")

os.makedirs(RAW_DIR, exist_ok=True)

# -------------------------------------------------------------
# Configuration & Reference Constants
# -------------------------------------------------------------
DEPARTMENTS = ["Procurement", "Information Technology", "Operations", "Facilities", "Corporate Marketing", "Finance & Accounting"]

ITEM_CATALOG = [
    {"desc": "Dell Latitude 5540 Laptop", "category": "IT Hardware", "unit_price": 1250.00},
    {"desc": "Dell UltraSharp 27 Monitor", "category": "IT Hardware", "unit_price": 380.00},
    {"desc": "Cisco Catalyst 9300 Switch", "category": "IT Hardware", "unit_price": 4200.00},
    {"desc": "Enterprise Cloud Hosting (Monthly)", "category": "Software Licenses", "unit_price": 8500.00},
    {"desc": "Cybersecurity SOC Monitoring (Monthly)", "category": "Software Licenses", "unit_price": 12000.00},
    {"desc": "Salesforce CRM Enterprise Seat (Annual)", "category": "Software Licenses", "unit_price": 1800.00},
    {"desc": "Ergonomic Mesh Task Chairs", "category": "Facilities", "unit_price": 450.00},
    {"desc": "Commercial HVAC Air Filter Box", "category": "Facilities", "unit_price": 120.00},
    {"desc": "Corporate Office Janitorial Services", "category": "Facilities", "unit_price": 3500.00},
    {"desc": "Industrial Pallet Racking Units", "category": "Operations", "unit_price": 1600.00},
    {"desc": "Forklift Maintenance & Battery Pack", "category": "Operations", "unit_price": 2800.00},
    {"desc": "Corrugated Packaging Boxes (Batch 1000)", "category": "Operations", "unit_price": 850.00},
    {"desc": "External Legal Advisory Hours", "category": "Professional Services", "unit_price": 650.00},
    {"desc": "SOX Compliance Internal Audit Consulting", "category": "Professional Services", "unit_price": 450.00},
    {"desc": "Digital Ad Campaign Management Fee", "category": "Corporate Marketing", "unit_price": 7500.00},
    {"desc": "Global Freight Logistics & Drayage", "category": "Logistics", "unit_price": 2200.00},
    {"desc": "Raw Sheet Metal - Aluminum 6061 (Ton)", "category": "Raw Materials", "unit_price": 3100.00},
    {"desc": "Industrial Grade Fasteners (Box 5000)", "category": "Raw Materials", "unit_price": 420.00}
]

def round_curr(val):
    return float(Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

# -------------------------------------------------------------
# 1. Generate Employees Master Data
# -------------------------------------------------------------
def generate_employees():
    employees = [
        # Executives & Directors (High Limit)
        ("EMP001", "Eleanor", "Vance", "Procurement", "Chief Procurement Officer", "e.vance@enterprise.com", 1000000.00, "98765432101", "100 Executive Way", "New York", "NY", "10001"),
        ("EMP002", "Marcus", "Sterling", "Information Technology", "VP of Technology", "m.sterling@enterprise.com", 500000.00, "98765432102", "250 Park Ave", "New York", "NY", "10017"),
        ("EMP003", "Sarah", "Jenkins", "Finance & Accounting", "Corporate Controller", "s.jenkins@enterprise.com", 250000.00, "98765432103", "45 Wall St", "New York", "NY", "10005"),
        ("EMP004", "David", "Kim", "Operations", "Director of Supply Chain", "d.kim@enterprise.com", 150000.00, "98765432104", "88 Industrial Pkwy", "Jersey City", "NJ", "07302"),
        
        # Managers (Mid Limit: $25k - $50k)
        ("EMP005", "Rachel", "Adams", "Procurement", "Sourcing Manager", "r.adams@enterprise.com", 50000.00, "98765432105", "12 Maple St", "Summit", "NJ", "07901"),
        ("EMP006", "Brian", "O'Connor", "Information Technology", "IT Infrastructure Manager", "b.oconnor@enterprise.com", 50000.00, "98765432106", "77 Silicon Way", "Hoboken", "NJ", "07030"),
        ("EMP007", "Lisa", "Perez", "Facilities", "Facilities Director", "l.perez@enterprise.com", 30000.00, "98765432107", "304 Elm Blvd", "White Plains", "NY", "10601"),
        ("EMP008", "Thomas", "Wright", "Corporate Marketing", "Marketing Director", "t.wright@enterprise.com", 25000.00, "98765432108", "19 Broadway", "New York", "NY", "10006"),
        ("EMP009", "Karen", "Mitchell", "Operations", "Plant Operations Manager", "k.mitchell@enterprise.com", 25000.00, "98765432109", "51 Warehouse Rd", "Newark", "NJ", "07105"),
        
        # Supervisors / Senior Buyers (Threshold Limit: $10k)
        ("EMP010", "Kevin", "Zhang", "Procurement", "Senior Sourcing Specialist", "k.zhang@enterprise.com", 10000.00, "98765432110", "404 Cedar Ln", "Fort Lee", "NJ", "07024"),
        ("EMP011", "Amanda", "Foster", "Procurement", "Procurement Specialist", "a.foster@enterprise.com", 10000.00, "98765432111", "90 River St", "Hoboken", "NJ", "07030"),
        ("EMP012", "Daniel", "Ross", "Information Technology", "Lead Cloud Architect", "d.ross@enterprise.com", 10000.00, "98765432112", "22 Beacon St", "Stamford", "CT", "06901"),
        
        # Buyers & Requesters (Low Limit: $1k - $5k)
        ("EMP013", "Jessica", "Taylor", "Procurement", "Junior Buyer", "j.taylor@enterprise.com", 2500.00, "98765432113", "14 Oak Ave", "Jersey City", "NJ", "07304"),
        ("EMP014", "Christopher", "Cole", "Information Technology", "Systems Administrator", "c.cole@enterprise.com", 1000.00, "98765432114", "85 Pine Blvd", "Morristown", "NJ", "07960"),
        ("EMP015", "Ashley", "Green", "Operations", "Warehouse Coordinator", "a.green@enterprise.com", 1000.00, "98765432115", "103 Logistics Way", "Elizabeth", "NJ", "07201"),
        ("EMP016", "Matthew", "Scott", "Corporate Marketing", "Digital Campaign Specialist", "m.scott@enterprise.com", 1000.00, "98765432116", "62 Lexington Ave", "New York", "NY", "10010"),
        ("EMP017", "Nicole", "Bell", "Facilities", "Office Services Coordinator", "n.bell@enterprise.com", 1000.00, "98765432117", "33 High St", "Paterson", "NJ", "07505"),
        ("EMP018", "Anthony", "Harris", "Procurement", "Buyer", "a.harris@enterprise.com", 5000.00, "98765432118", "71 Grand Ave", "Englewood", "NJ", "07631"),
        
        # Suspect Employee for Conflict of Interest / Phantom Vendor Test
        ("EMP019", "Robert", "Mercer", "Procurement", "Category Sourcing Lead", "r.mercer@enterprise.com", 20000.00, "11223344550", "742 Evergreen Terrace", "Springfield", "NJ", "07081"),
        ("EMP020", "Samantha", "Drake", "Operations", "Inventory Analyst", "s.drake@enterprise.com", 1000.00, "98765432120", "88 Lakeview Dr", "Wayne", "NJ", "07470"),
        
        # Receiving Dock Employees (Non-approvers)
        ("EMP021", "Carlos", "Mendez", "Operations", "Receiving Dock Supervisor", "c.mendez@enterprise.com", 0.00, "98765432121", "12 Dockside Way", "Bayonne", "NJ", "07002"),
        ("EMP022", "Gregory", "House", "Operations", "Receiving Clerk", "g.house@enterprise.com", 0.00, "98765432122", "44 Port Rd", "Newark", "NJ", "07114"),
        
        # AP Clerks & Approvers
        ("EMP023", "Megan", "Fox", "Finance & Accounting", "AP Specialist", "m.fox@enterprise.com", 5000.00, "98765432123", "19 Flatbush Ave", "Brooklyn", "NY", "11217"),
        ("EMP024", "Patrick", "Stewart", "Finance & Accounting", "AP Manager", "p.stewart@enterprise.com", 50000.00, "98765432124", "55 Court St", "Brooklyn", "NY", "11201"),
        ("EMP025", "Diana", "Prince", "Finance & Accounting", "Senior Internal Auditor", "d.prince@enterprise.com", 0.00, "98765432125", "10 Queens Blvd", "Queens", "NY", "11101")
    ]
    return employees

# -------------------------------------------------------------
# 2. Generate Vendors Master Data
# -------------------------------------------------------------
def generate_vendors():
    vendors = [
        ("VND001", "Apex Tech Solutions Inc", "12-3456781", "11122233301", "021000021", "NET30", "100 Silicon Ave", "San Jose", "CA", "95112", "USA", "ACTIVE", "2021-01-15", "2024-01-10"),
        ("VND002", "Summit Cloud Infrastructure LLC", "12-3456782", "11122233302", "121000358", "NET30", "450 Cloud Way", "Seattle", "WA", "98101", "USA", "ACTIVE", "2021-03-22", "2024-02-15"),
        ("VND003", "Global Freight & Logistics Corp", "12-3456783", "11122233303", "071000013", "NET45", "88 Harbor Blvd", "Long Beach", "CA", "90802", "USA", "ACTIVE", "2020-05-10", "2024-01-18"),
        ("VND004", "Starlight Office & Facilities Group", "12-3456784", "11122233304", "021000021", "NET30", "210 Commerce St", "Dallas", "TX", "75201", "USA", "ACTIVE", "2019-11-04", "2024-03-01"),
        ("VND005", "Precision Industrial Supply Co", "12-3456785", "11122233305", "041200055", "NET30", "75 Foundry St", "Cleveland", "OH", "44113", "USA", "ACTIVE", "2020-08-19", "2024-01-25"),
        ("VND006", "Enterprise Cyber Defense Partners", "12-3456786", "11122233306", "021000021", "NET30", "300 Security Plaza", "Reston", "VA", "20190", "USA", "ACTIVE", "2021-06-14", "2024-02-28"),
        ("VND007", "Metropolitan Janitorial & Facilities", "12-3456787", "11122233307", "026009593", "NET15", "14 Clean St", "Newark", "NJ", "07102", "USA", "ACTIVE", "2018-09-12", "2023-11-15"),
        ("VND008", "Vanguard Raw Materials Ltd", "12-3456788", "11122233308", "071000013", "NET60", "900 Industrial Pkwy", "Gary", "IN", "46402", "USA", "ACTIVE", "2020-02-17", "2024-02-10"),
        ("VND009", "Horizon Marketing & Media LLC", "12-3456789", "11122233309", "021000021", "NET30", "500 Madison Ave", "New York", "NY", "10022", "USA", "ACTIVE", "2021-09-01", "2024-01-30"),
        ("VND010", "Beacon Legal & Advisory Services", "12-3456790", "11122233310", "021000021", "NET30", "120 Broadway", "New York", "NY", "10271", "USA", "ACTIVE", "2019-04-18", "2024-02-20"),
        ("VND011", "Allied Packaging Solutions", "12-3456791", "11122233311", "071000013", "NET30", "64 Carton Rd", "Allentown", "PA", "18109", "USA", "ACTIVE", "2020-10-05", "2024-01-12"),
        ("VND012", "NexGen IT Hardware Distribution", "12-3456792", "11122233312", "121000358", "NET30", "820 Gateway Blvd", "Austin", "TX", "78701", "USA", "ACTIVE", "2022-01-11", "2024-03-15"),
        ("VND013", "Titan Heavy Machinery & Lift", "12-3456793", "11122233313", "041200055", "NET45", "310 Heavy Way", "Peoria", "IL", "61602", "USA", "ACTIVE", "2019-07-29", "2024-01-08"),
        ("VND014", "AuditPro Advisory Partners", "12-3456794", "11122233314", "021000021", "NET30", "10 Rockefeller Plaza", "New York", "NY", "10020", "USA", "ACTIVE", "2021-11-20", "2024-02-14"),
        ("VND015", "ComfortZone Ergonomic Interiors", "12-3456795", "11122233315", "071000013", "NET30", "415 Design Center", "Grand Rapids", "MI", "49503", "USA", "ACTIVE", "2022-04-03", "2024-01-22"),
        
        # --- DELIBERATE ANOMALY VENDORS ---
        # Anomaly 1: Duplicate Bank Account across Vendors (VND016 copies VND001's bank routing & account!)
        ("VND016", "Apex Strategic Consulting LLC", "99-8877661", "11122233301", "021000021", "NET30", "104 Silicon Blvd", "San Jose", "CA", "95112", "USA", "ACTIVE", "2023-05-10", "2024-02-01"),
        
        # Anomaly 2: Conflict of Interest / Phantom Vendor (Shares address & bank account with employee Robert Mercer - EMP019)
        ("VND017", "Evergreen Management & Sourcing", "99-1122334", "11223344550", "021000021", "NET15", "742 Evergreen Terrace", "Springfield", "NJ", "07081", "USA", "ACTIVE", "2023-02-14", "2023-02-14"),
        
        # Anomaly 3: Inactive / Dormant Vendor with sudden burst in spend
        ("VND018", "Dormant Industrial Corp", "88-7766554", "55443322119", "071000013", "NET30", "12 Ghost Rd", "Detroit", "MI", "48201", "USA", "INACTIVE", "2017-03-01", "2020-01-15"),
        
        # Additional clean vendors
        ("VND019", "OmniSource Office Tech", "12-3456799", "11122233319", "021000021", "NET30", "95 Tech Loop", "Boston", "MA", "02110", "USA", "ACTIVE", "2022-08-15", "2024-02-10"),
        ("VND020", "Pinnacle Warehouse Equipment", "12-3456800", "11122233320", "041200055", "NET30", "500 Logistics Way", "Columbus", "OH", "43215", "USA", "ACTIVE", "2021-12-01", "2024-01-19")
    ]
    return vendors

# -------------------------------------------------------------
# 3. Generate Transactions: POs, Lines, GRs, Invoices, Payments
# -------------------------------------------------------------
def generate_p2p_transactions(employees, vendors):
    emp_dict = {e[0]: e for e in employees}
    vendor_dict = {v[0]: v for v in vendors}
    
    pos = []
    po_lines = []
    grs = []
    invoices = []
    inv_lines = []
    payments = []
    
    po_counter = 1000
    po_line_counter = 5000
    gr_counter = 2000
    inv_counter = 3000
    inv_line_counter = 7000
    pay_counter = 4000
    
    start_date = datetime(2023, 1, 15)
    
    # Track POs created by employee + vendor + date for split purchase injection
    # We will generate ~180 baseline clean POs across 12 months, plus targeted control anomalies!
    
    # -------------------------------------------------------------------------
    # PART A: NORMAL / STANDARD COMPLIANT P2P WORKFLOW CYCLES (~160 POs)
    # -------------------------------------------------------------------------
    clean_vendors = [v[0] for v in vendors if v[0] not in ("VND016", "VND017", "VND018")]
    buyers = ["EMP010", "EMP011", "EMP012", "EMP013", "EMP014", "EMP015", "EMP016", "EMP017", "EMP018"]
    
    for i in range(160):
        po_counter += 1
        po_id = f"PO-{po_counter}"
        po_number = f"PO-2023-{po_counter}"
        
        vendor_id = random.choice(clean_vendors)
        requester_id = random.choice(buyers)
        req_dept = emp_dict[requester_id][3]
        
        # PO Date spread over 2023
        day_offset = int((i / 160.0) * 350) + random.randint(0, 5)
        po_date = start_date + timedelta(days=day_offset)
        
        # Pick 1-3 catalog items
        num_lines = random.choice([1, 2, 3])
        selected_items = random.sample(ITEM_CATALOG, num_lines)
        
        po_total = 0.0
        current_po_lines = []
        for line_idx, item in enumerate(selected_items, 1):
            po_line_counter += 1
            po_line_id = f"POL-{po_line_counter}"
            qty = random.choice([2, 5, 10, 15, 20, 30])
            unit_price = item["unit_price"]
            line_tot = round_curr(qty * unit_price)
            po_total += line_tot
            
            po_lines.append((
                po_line_id, po_id, line_idx, item["desc"], item["category"],
                qty, unit_price, line_tot
            ))
            current_po_lines.append((po_line_id, line_idx, item["desc"], qty, unit_price, line_tot))
            
        po_total = round_curr(po_total)
        
        # Proper Approver Assignment based on approval limit
        if po_total <= 10000.00:
            approver_id = random.choice(["EMP005", "EMP006", "EMP007", "EMP008", "EMP009"])
        elif po_total <= 50000.00:
            approver_id = random.choice(["EMP005", "EMP006", "EMP004"])
        elif po_total <= 250000.00:
            approver_id = random.choice(["EMP003", "EMP004", "EMP002"])
        else:
            approver_id = "EMP001"
            
        approval_date = po_date + timedelta(days=random.randint(1, 3))
        pos.append((
            po_id, po_number, vendor_id, requester_id, approver_id,
            po_date.strftime("%Y-%m-%d"), "APPROVED", approval_date.strftime("%Y-%m-%d"),
            po_total, req_dept
        ))
        
        # Standard Goods Receipt (90% received in full, 10% partial or open)
        gr_date = approval_date + timedelta(days=random.randint(4, 12))
        for pline in current_po_lines:
            gr_counter += 1
            gr_id = f"GR-{gr_counter}"
            gr_num = f"GR-REC-{gr_counter}"
            received_qty = pline[3] # Clean 100% receipt
            grs.append((
                gr_id, gr_num, po_id, pline[0], gr_date.strftime("%Y-%m-%d"),
                random.choice(["EMP021", "EMP022"]), received_qty, "ACCEPTED", "Verified count and condition"
            ))
            
        # Standard Vendor Invoice (3-way match clean)
        inv_counter += 1
        inv_id = f"INV-{inv_counter}"
        inv_num = f"INV-{vendor_id[-3:]}-{random.randint(10000, 99999)}"
        inv_date = gr_date + timedelta(days=random.randint(2, 5))
        rec_date = inv_date + timedelta(days=1)
        due_date = inv_date + timedelta(days=30)
        
        invoices.append((
            inv_id, vendor_id, inv_num, po_id, inv_date.strftime("%Y-%m-%d"),
            rec_date.strftime("%Y-%m-%d"), due_date.strftime("%Y-%m-%d"),
            po_total, "PAID", "EMP024", (rec_date + timedelta(days=2)).strftime("%Y-%m-%d")
        ))
        
        for pline in current_po_lines:
            inv_line_counter += 1
            inv_lines.append((
                f"INVL-{inv_line_counter}", inv_id, pline[1], pline[2],
                pline[3], pline[4], pline[5], pline[0]
            ))
            
        # Standard Payment (Paid on time, correct amount, correct bank)
        pay_counter += 1
        pay_id = f"PAY-{pay_counter}"
        pay_ref = f"ACH-REF-{pay_counter:06d}"
        pay_date = due_date - timedelta(days=random.randint(0, 5))
        remitted_bank = vendor_dict[vendor_id][3]
        
        payments.append((
            pay_id, pay_ref, inv_id, vendor_id, pay_date.strftime("%Y-%m-%d"),
            po_total, "ACH", remitted_bank, "COMPLETED"
        ))

    # -------------------------------------------------------------------------
    # PART B: DELIBERATE INJECTION OF REAL-WORLD FINANCIAL CONTROL VIOLATIONS
    # -------------------------------------------------------------------------
    
    # === CONTROL TEST 1: DUPLICATE INVOICES ===
    # Case 1A: Exact Duplicate Invoice paid twice (Same Vendor, Same Invoice #, Same Amount)
    po_counter += 1
    p_id = f"PO-{po_counter}"
    v_id = "VND001"
    pos.append((p_id, f"PO-2023-{po_counter}", v_id, "EMP010", "EMP005", "2023-04-10", "APPROVED", "2023-04-11", 14500.00, "Procurement"))
    po_lines.append((f"POL-{po_line_counter+1}", p_id, 1, "Enterprise Cloud Hosting (Monthly)", "Software Licenses", 1, 14500.00, 14500.00))
    po_line_counter += 1
    grs.append((f"GR-{gr_counter+1}", f"GR-REC-{gr_counter+1}", p_id, f"POL-{po_line_counter}", "2023-04-15", "EMP021", 1, "ACCEPTED", "Monthly signoff"))
    gr_counter += 1
    
    # Original Invoice & Payment
    inv_counter += 1
    orig_inv_id = f"INV-{inv_counter}"
    dup_inv_num = "INV-APEX-77881"
    invoices.append((orig_inv_id, v_id, dup_inv_num, p_id, "2023-04-18", "2023-04-19", "2023-05-18", 14500.00, "PAID", "EMP024", "2023-04-20"))
    inv_lines.append((f"INVL-{inv_line_counter+1}", orig_inv_id, 1, "Enterprise Cloud Hosting (Monthly)", 1, 14500.00, 14500.00, f"POL-{po_line_counter}"))
    inv_line_counter += 1
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", orig_inv_id, v_id, "2023-05-15", 14500.00, "ACH", vendor_dict[v_id][3], "COMPLETED"))
    
    # Exact Duplicate Invoice Resubmitted 12 days later and PAID AGAIN!
    inv_counter += 1
    dup_inv_id = f"INV-{inv_counter}"
    invoices.append((dup_inv_id, v_id, dup_inv_num, p_id, "2023-04-30", "2023-05-01", "2023-05-30", 14500.00, "PAID", "EMP023", "2023-05-02"))
    inv_lines.append((f"INVL-{inv_line_counter+1}", dup_inv_id, 1, "Enterprise Cloud Hosting (Monthly)", 1, 14500.00, 14500.00, f"POL-{po_line_counter}"))
    inv_line_counter += 1
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"WIRE-REF-{pay_counter:06d}", dup_inv_id, v_id, "2023-05-25", 14500.00, "WIRE", vendor_dict[v_id][3], "COMPLETED"))

    # Case 1B: Near / Suspect Duplicate Invoice (Same Vendor, Same Amount $8,750, Invoice # altered: 'INV-44910' vs 'INV-44910-A')
    po_counter += 1
    p_id = f"PO-{po_counter}"
    v_id = "VND004"
    pos.append((p_id, f"PO-2023-{po_counter}", v_id, "EMP017", "EMP007", "2023-06-05", "APPROVED", "2023-06-06", 8750.00, "Facilities"))
    po_lines.append((f"POL-{po_line_counter+1}", p_id, 1, "Corporate Office Janitorial Services", "Facilities", 2.5, 3500.00, 8750.00))
    po_line_counter += 1
    grs.append((f"GR-{gr_counter+1}", f"GR-REC-{gr_counter+1}", p_id, f"POL-{po_line_counter}", "2023-06-10", "EMP021", 2.5, "ACCEPTED", "Services done"))
    gr_counter += 1
    
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", v_id, "INV-44910", p_id, "2023-06-12", "2023-06-13", "2023-07-12", 8750.00, "PAID", "EMP024", "2023-06-14"))
    inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Corporate Office Janitorial Services", 2.5, 3500.00, 8750.00, f"POL-{po_line_counter}"))
    inv_line_counter += 1
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", v_id, "2023-07-10", 8750.00, "ACH", vendor_dict[v_id][3], "COMPLETED"))
    
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", v_id, "INV-44910-A", p_id, "2023-06-20", "2023-06-21", "2023-07-20", 8750.00, "PAID", "EMP023", "2023-06-22"))
    inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Corporate Office Janitorial Services", 2.5, 3500.00, 8750.00, f"POL-{po_line_counter}"))
    inv_line_counter += 1
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", v_id, "2023-07-18", 8750.00, "ACH", vendor_dict[v_id][3], "COMPLETED"))

    # Case 1C: Duplicate Payment of the exact same Invoice ID (System error double disbursing)
    inv_counter += 1
    single_inv_id = f"INV-{inv_counter}"
    v_id = "VND006"
    invoices.append((single_inv_id, v_id, "INV-CYBER-8821", None, "2023-08-01", "2023-08-02", "2023-09-01", 12000.00, "PAID", "EMP024", "2023-08-03"))
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", single_inv_id, v_id, "2023-08-28", 12000.00, "ACH", vendor_dict[v_id][3], "COMPLETED"))
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"WIRE-REF-{pay_counter:06d}", single_inv_id, v_id, "2023-08-29", 12000.00, "WIRE", vendor_dict[v_id][3], "COMPLETED"))

    # === CONTROL TEST 2: THREE-WAY MATCHING VIOLATIONS ===
    # Case 2A: Quantity Mismatch (Invoiced Qty > Received Qty)
    # PO: 50 laptops @ $1,250 = $62,500. GR: Received only 30 laptops. Invoice billed for full 50 laptops!
    po_counter += 1
    p_id = f"PO-{po_counter}"
    v_id = "VND012"
    pos.append((p_id, f"PO-2023-{po_counter}", v_id, "EMP014", "EMP006", "2023-03-01", "APPROVED", "2023-03-02", 62500.00, "Information Technology"))
    po_line_counter += 1
    pol_id = f"POL-{po_line_counter}"
    po_lines.append((pol_id, p_id, 1, "Dell Latitude 5540 Laptop", "IT Hardware", 50, 1250.00, 62500.00))
    
    gr_counter += 1
    grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, pol_id, "2023-03-10", "EMP022", 30, "ACCEPTED", "Partial shipment: only 30 units delivered"))
    
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", v_id, "INV-NEX-30019", p_id, "2023-03-12", "2023-03-13", "2023-04-12", 62500.00, "PENDING_REVIEW", None, None))
    inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Dell Latitude 5540 Laptop", 50, 1250.00, 62500.00, pol_id))
    inv_line_counter += 1

    # Case 2B: Unit Price Variance (Invoiced Price > PO Price)
    # PO: 20 Monitors @ $380 = $7,600. GR: 20 received. Invoice bills @ $460/unit = $9,200 (+21% variance!)
    po_counter += 1
    p_id = f"PO-{po_counter}"
    v_id = "VND012"
    pos.append((p_id, f"PO-2023-{po_counter}", v_id, "EMP014", "EMP006", "2023-05-10", "APPROVED", "2023-05-11", 7600.00, "Information Technology"))
    po_line_counter += 1
    pol_id = f"POL-{po_line_counter}"
    po_lines.append((pol_id, p_id, 1, "Dell UltraSharp 27 Monitor", "IT Hardware", 20, 380.00, 7600.00))
    
    gr_counter += 1
    grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, pol_id, "2023-05-18", "EMP022", 20, "ACCEPTED", "20 units in box"))
    
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", v_id, "INV-NEX-30455", p_id, "2023-05-20", "2023-05-21", "2023-06-20", 9200.00, "PENDING_REVIEW", None, None))
    inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Dell UltraSharp 27 Monitor", 20, 460.00, 9200.00, pol_id))
    inv_line_counter += 1

    # Case 2C: Invoice without any Goods Receipt (Phantom delivery / premature billing)
    po_counter += 1
    p_id = f"PO-{po_counter}"
    v_id = "VND005"
    pos.append((p_id, f"PO-2023-{po_counter}", v_id, "EMP015", "EMP009", "2023-07-01", "APPROVED", "2023-07-02", 16000.00, "Operations"))
    po_line_counter += 1
    pol_id = f"POL-{po_line_counter}"
    po_lines.append((pol_id, p_id, 1, "Industrial Pallet Racking Units", "Operations", 10, 1600.00, 16000.00))
    # NO GOODS RECEIPT CREATED!
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", v_id, "INV-PREC-99120", p_id, "2023-07-15", "2023-07-16", "2023-08-15", 16000.00, "ON_HOLD", None, None))
    inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Industrial Pallet Racking Units", 10, 1600.00, 16000.00, pol_id))
    inv_line_counter += 1

    # Case 2D: Invoice without any Purchase Order (Unapproved spend / Maverick spend)
    inv_counter += 1
    v_id = "VND009"
    invoices.append((f"INV-{inv_counter}", v_id, "INV-MAV-00129", None, "2023-09-10", "2023-09-11", "2023-10-10", 24500.00, "PENDING_REVIEW", None, None))
    inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Uncontracted Media Marketing Consulting", 1, 24500.00, 24500.00, None))
    inv_line_counter += 1

    # === CONTROL TEST 3: SPLIT PURCHASES (STRUCTURING BELOW $10,000 THRESHOLD) ===
    # Buyer Kevin Zhang (EMP010) has a $10,000 approval limit.
    # To buy $28,000 worth of equipment from VND005 without Director approval,
    # he creates 3 POs on the SAME DAY (2023-08-14), each just below $10,000 ($9,600, $9,200, $9,200)!
    split_dates = ["2023-08-14", "2023-08-14", "2023-08-15"]
    split_amounts = [9600.00, 9200.00, 9200.00]
    for idx, (s_date, s_amt) in enumerate(zip(split_dates, split_amounts), 1):
        po_counter += 1
        p_id = f"PO-{po_counter}"
        pos.append((p_id, f"PO-2023-{po_counter}", "VND005", "EMP010", "EMP010", s_date, "APPROVED", s_date, s_amt, "Procurement"))
        po_line_counter += 1
        po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Industrial Grade Fasteners (Box 5000)", "Raw Materials", int(s_amt/420.0), 420.00, s_amt))
        gr_counter += 1
        grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-08-20", "EMP021", int(s_amt/420.0), "ACCEPTED", "Split order delivery"))
        inv_counter += 1
        invoices.append((f"INV-{inv_counter}", "VND005", f"INV-SPLIT-{po_counter}", p_id, "2023-08-22", "2023-08-23", "2023-09-22", s_amt, "PAID", "EMP024", "2023-08-25"))
        inv_lines.append((f"INVL-{inv_line_counter+1}", f"INV-{inv_counter}", 1, "Industrial Fasteners", int(s_amt/420.0), 420.00, s_amt, f"POL-{po_line_counter}"))
        inv_line_counter += 1
        pay_counter += 1
        payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND005", "2023-09-20", s_amt, "ACH", vendor_dict["VND005"][3], "COMPLETED"))

    # Another split instance: Buyer Amanda Foster (EMP011) structuring 2 POs of $9,800 to VND011 within 24 hours
    for idx, s_amt in enumerate([9800.00, 9800.00], 1):
        po_counter += 1
        p_id = f"PO-{po_counter}"
        pos.append((p_id, f"PO-2023-{po_counter}", "VND011", "EMP011", "EMP011", "2023-10-02", "APPROVED", "2023-10-02", s_amt, "Procurement"))
        po_line_counter += 1
        po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Corrugated Packaging Boxes (Batch 1000)", "Operations", int(s_amt/850.0), 850.00, s_amt))
        gr_counter += 1
        grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-10-10", "EMP022", int(s_amt/850.0), "ACCEPTED", "Delivered"))
        inv_counter += 1
        invoices.append((f"INV-{inv_counter}", "VND011", f"INV-SPLIT2-{po_counter}", p_id, "2023-10-12", "2023-10-13", "2023-11-12", s_amt, "PAID", "EMP024", "2023-10-14"))
        pay_counter += 1
        payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND011", "2023-11-10", s_amt, "ACH", vendor_dict["VND011"][3], "COMPLETED"))

    # === CONTROL TEST 4: VENDOR ANOMALIES & CONFLICT OF INTEREST ===
    # Case 4A: Spending with VND017 (Phantom Vendor matched to employee Robert Mercer EMP019)
    # Total spend: $35,000 funneled to employee's own address/bank!
    for v_amt, p_num in [(18000.00, "PO-FRAUD-01"), (17000.00, "PO-FRAUD-02")]:
        po_counter += 1
        p_id = f"PO-{po_counter}"
        pos.append((p_id, p_num, "VND017", "EMP019", "EMP005", "2023-09-01", "APPROVED", "2023-09-02", v_amt, "Procurement"))
        po_line_counter += 1
        po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Strategic Sourcing Consulting", "Professional Services", 1, v_amt, v_amt))
        gr_counter += 1
        grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-09-10", "EMP021", 1, "ACCEPTED", "Services billed"))
        inv_counter += 1
        invoices.append((f"INV-{inv_counter}", "VND017", f"INV-EVM-{po_counter}", p_id, "2023-09-12", "2023-09-13", "2023-10-12", v_amt, "PAID", "EMP024", "2023-09-15"))
        pay_counter += 1
        payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND017", "2023-10-05", v_amt, "ACH", vendor_dict["VND017"][3], "COMPLETED"))

    # Case 4B: Spending with VND016 (Shell entity copying VND001's bank routing/account)
    po_counter += 1
    p_id = f"PO-{po_counter}"
    pos.append((p_id, f"PO-2023-{po_counter}", "VND016", "EMP010", "EMP005", "2023-11-01", "APPROVED", "2023-11-02", 42000.00, "Procurement"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Strategic Software Infrastructure Upgrade", "Software Licenses", 1, 42000.00, 42000.00))
    gr_counter += 1
    grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-11-10", "EMP021", 1, "ACCEPTED", "License keys delivered"))
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", "VND016", "INV-APX-SHELL-01", p_id, "2023-11-12", "2023-11-13", "2023-12-12", 42000.00, "PAID", "EMP024", "2023-11-14"))
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"WIRE-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND016", "2023-12-05", 42000.00, "WIRE", vendor_dict["VND016"][3], "COMPLETED"))

    # Case 4C: Dormant Vendor VND018 (Status INACTIVE, last review 2020) receiving sudden $78,000 spend
    po_counter += 1
    p_id = f"PO-{po_counter}"
    pos.append((p_id, f"PO-2023-{po_counter}", "VND018", "EMP015", "EMP004", "2023-10-15", "APPROVED", "2023-10-16", 78000.00, "Operations"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Reconditioned Industrial Press Units", "Operations", 2, 39000.00, 78000.00))
    gr_counter += 1
    grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-10-25", "EMP022", 2, "ACCEPTED", "Heavy freight delivered"))
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", "VND018", "INV-DORM-5510", p_id, "2023-10-28", "2023-10-29", "2023-11-28", 78000.00, "PAID", "EMP024", "2023-11-02"))
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"WIRE-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND018", "2023-11-20", 78000.00, "WIRE", vendor_dict["VND018"][3], "COMPLETED"))

    # === CONTROL TEST 5: PAYMENT ANOMALIES ===
    # Case 5A: Ghost Payment (Payment disbursed with NO matching invoice in the system)
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"WIRE-GHOST-{pay_counter}", None, "VND003", "2023-06-25", 19500.00, "WIRE", vendor_dict["VND003"][3], "COMPLETED"))
    
    # Case 5B: Overpayment (Invoice amount was $15,000, but payment executed for $19,500 - $4,500 overpaid!)
    po_counter += 1
    p_id = f"PO-{po_counter}"
    pos.append((p_id, f"PO-2023-{po_counter}", "VND008", "EMP015", "EMP009", "2023-04-05", "APPROVED", "2023-04-06", 15000.00, "Operations"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Raw Sheet Metal - Aluminum 6061", "Raw Materials", 4.838, 3100.00, 15000.00))
    gr_counter += 1
    grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-04-12", "EMP022", 4.838, "ACCEPTED", "Material accepted"))
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", "VND008", "INV-VANG-1004", p_id, "2023-04-15", "2023-04-16", "2023-05-15", 15000.00, "PAID", "EMP024", "2023-04-18"))
    pay_counter += 1
    payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND008", "2023-05-12", 19500.00, "ACH", vendor_dict["VND008"][3], "COMPLETED"))

    # Case 5C: Premature Payment (Payment date occurred 15 days BEFORE invoice date or invoice approval)
    po_counter += 1
    p_id = f"PO-{po_counter}"
    pos.append((p_id, f"PO-2023-{po_counter}", "VND002", "EMP014", "EMP006", "2023-09-01", "APPROVED", "2023-09-02", 8500.00, "Information Technology"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", p_id, 1, "Enterprise Cloud Hosting (Monthly)", "Software Licenses", 1, 8500.00, 8500.00))
    gr_counter += 1
    grs.append((f"GR-{gr_counter}", f"GR-REC-{gr_counter}", p_id, f"POL-{po_line_counter}", "2023-09-05", "EMP021", 1, "ACCEPTED", "Signoff"))
    inv_counter += 1
    invoices.append((f"INV-{inv_counter}", "VND002", "INV-SUM-9099", p_id, "2023-09-25", "2023-09-26", "2023-10-25", 8500.00, "PAID", "EMP024", "2023-09-28"))
    pay_counter += 1
    # Paid on 2023-09-10 (15 days before invoice was received or approved!)
    payments.append((f"PAY-{pay_counter}", f"ACH-REF-{pay_counter:06d}", f"INV-{inv_counter}", "VND002", "2023-09-10", 8500.00, "ACH", vendor_dict["VND002"][3], "COMPLETED"))

    # === CONTROL TEST 6: APPROVAL VIOLATIONS & DELEGATION OF AUTHORITY (DoA) ===
    # Case 6A: Approver exceeding authorization limit (EMP013 limit is $2,500, but approved $68,000 PO!)
    po_counter += 1
    pos.append((f"PO-{po_counter}", f"PO-2023-{po_counter}", "VND002", "EMP014", "EMP013", "2023-07-11", "APPROVED", "2023-07-12", 68000.00, "Information Technology"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", f"PO-{po_counter}", 1, "Enterprise Cloud Infrastructure Cluster", "Software Licenses", 8, 8500.00, 68000.00))
    
    # Case 6B: Self-Approval violation (EMP006 IT Infrastructure Manager created PO for $48,000 and self-approved it!)
    po_counter += 1
    pos.append((f"PO-{po_counter}", f"PO-2023-{po_counter}", "VND006", "EMP006", "EMP006", "2023-08-20", "APPROVED", "2023-08-20", 48000.00, "Information Technology"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", f"PO-{po_counter}", 1, "Cybersecurity SOC Monitoring (Monthly)", "Software Licenses", 4, 12000.00, 48000.00))

    # Case 6C: Self-Approval by Procurement Buyer EMP018 ($18,500 PO self-approved)
    po_counter += 1
    pos.append((f"PO-{po_counter}", f"PO-2023-{po_counter}", "VND004", "EMP018", "EMP018", "2023-11-15", "APPROVED", "2023-11-15", 18500.00, "Procurement"))
    po_line_counter += 1
    po_lines.append((f"POL-{po_line_counter}", f"PO-{po_counter}", 1, "Ergonomic Mesh Task Chairs", "Facilities", 41.11, 450.00, 18500.00))

    return pos, po_lines, grs, invoices, inv_lines, payments

# -------------------------------------------------------------
# 4. Save to CSV and SQLite
# -------------------------------------------------------------
def write_csv(filepath, headers, rows):
    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f" [Export] {os.path.basename(filepath)}: {len(rows)} rows written.")

def build_database():
    print("="*70)
    print(">>> Generating Procure-to-Pay (P2P) Continuous Controls Dataset")
    print("="*70)
    
    employees = generate_employees()
    vendors = generate_vendors()
    pos, po_lines, grs, invoices, inv_lines, payments = generate_p2p_transactions(employees, vendors)
    
    emp_headers = ["employee_id", "first_name", "last_name", "department", "job_title", "email", "approval_limit", "bank_account_number", "street_address", "city", "state", "postal_code"]
    vendor_headers = ["vendor_id", "vendor_name", "tax_id", "bank_account_number", "bank_routing_number", "payment_terms", "street_address", "city", "state", "postal_code", "country", "vendor_status", "created_date", "last_review_date"]
    po_headers = ["po_id", "po_number", "vendor_id", "requester_id", "approver_id", "po_date", "po_status", "approval_date", "total_amount", "department"]
    pol_headers = ["po_line_id", "po_id", "line_number", "item_description", "category", "quantity_ordered", "unit_price", "line_total"]
    gr_headers = ["gr_id", "gr_number", "po_id", "po_line_id", "received_date", "received_by_employee_id", "quantity_received", "condition_status", "notes"]
    inv_headers = ["invoice_id", "vendor_id", "invoice_number", "po_id", "invoice_date", "received_date", "due_date", "invoice_amount", "invoice_status", "approved_by", "approval_date"]
    invl_headers = ["invoice_line_id", "invoice_id", "line_number", "item_description", "quantity_invoiced", "unit_price", "line_total", "po_line_id"]
    pay_headers = ["payment_id", "payment_reference", "invoice_id", "vendor_id", "payment_date", "payment_amount", "payment_method", "bank_account_remitted", "payment_status"]
    
    write_csv(os.path.join(RAW_DIR, "employees.csv"), emp_headers, employees)
    write_csv(os.path.join(RAW_DIR, "vendors.csv"), vendor_headers, vendors)
    write_csv(os.path.join(RAW_DIR, "purchase_orders.csv"), po_headers, pos)
    write_csv(os.path.join(RAW_DIR, "purchase_order_lines.csv"), pol_headers, po_lines)
    write_csv(os.path.join(RAW_DIR, "goods_receipts.csv"), gr_headers, grs)
    write_csv(os.path.join(RAW_DIR, "invoices.csv"), inv_headers, invoices)
    write_csv(os.path.join(RAW_DIR, "invoice_lines.csv"), invl_headers, inv_lines)
    write_csv(os.path.join(RAW_DIR, "payments.csv"), pay_headers, payments)
    
    # Initialize SQLite Database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SQL_SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
        cursor.executescript(schema_file.read())
        
    cursor.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP)", employees)
    cursor.executemany("INSERT INTO vendors VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", vendors)
    cursor.executemany("INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", pos)
    cursor.executemany("INSERT INTO purchase_order_lines VALUES (?,?,?,?,?,?,?,?)", po_lines)
    cursor.executemany("INSERT INTO goods_receipts VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", grs)
    cursor.executemany("INSERT INTO invoices VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", invoices)
    cursor.executemany("INSERT INTO invoice_lines VALUES (?,?,?,?,?,?,?,?)", inv_lines)
    cursor.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", payments)
    
    conn.commit()
    conn.close()
    
    print("\n [Database] SQLite database successfully built at:", DB_PATH)
    print("="*70)

if __name__ == "__main__":
    build_database()
