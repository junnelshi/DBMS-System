import sqlite3
import os
from werkzeug.security import generate_password_hash

def connect():
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_path   = os.path.join(base_path, "motorent.db")
    conn      = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
#  INIT TABLES
# ─────────────────────────────────────────────

def init_database():
    conn = connect()
    cur  = conn.cursor()

    # Branches
    cur.execute('''CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL, address TEXT NOT NULL,
        phone VARCHAR(20), email VARCHAR(100),
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Customers
    cur.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        firstname VARCHAR(50) NOT NULL, lastname VARCHAR(50) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL, phone VARCHAR(20) NOT NULL,
        birthdate DATE NOT NULL, address TEXT NOT NULL,
        license_no VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Admin
    cur.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL, email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL, role VARCHAR(20) DEFAULT 'admin',
        branch_id INTEGER REFERENCES branches(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # ── RENTAL MOTORS (for renting only) ──
    cur.execute('''CREATE TABLE IF NOT EXISTS rental_motors (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        brand        VARCHAR(50) NOT NULL,
        model        VARCHAR(50) NOT NULL,
        year         INTEGER     NOT NULL,
        type         VARCHAR(30) NOT NULL,
        plate        VARCHAR(20) UNIQUE NOT NULL,
        rate_per_day REAL        NOT NULL,
        status       VARCHAR(30) DEFAULT 'Available',
        branch_id    INTEGER REFERENCES branches(id),
        notes        TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # ── SALE MOTORS (for selling only) ──
    cur.execute('''CREATE TABLE IF NOT EXISTS sale_motors (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        brand         VARCHAR(50) NOT NULL,
        model         VARCHAR(50) NOT NULL,
        year          INTEGER     NOT NULL,
        type          VARCHAR(30) NOT NULL,
        plate         VARCHAR(20) UNIQUE NOT NULL,
        selling_price REAL        NOT NULL,
        status        VARCHAR(30) DEFAULT 'Available',
        branch_id     INTEGER REFERENCES branches(id),
        notes         TEXT,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Rentals (linked to rental_motors)
    cur.execute('''CREATE TABLE IF NOT EXISTS rentals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        motor_id    INTEGER NOT NULL REFERENCES rental_motors(id),
        start_date  DATE    NOT NULL, end_date DATE NOT NULL,
        total_cost  REAL    NOT NULL,
        status      VARCHAR(20) DEFAULT 'Pending',
        notes       TEXT,
        branch_id   INTEGER REFERENCES branches(id),
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Motor Sales transactions (linked to sale_motors)
    cur.execute('''CREATE TABLE IF NOT EXISTS motor_sales (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id      INTEGER NOT NULL REFERENCES customers(id),
        sale_motor_id    INTEGER NOT NULL REFERENCES sale_motors(id),
        total_price      REAL    NOT NULL,
        payment_type     VARCHAR(20) DEFAULT 'Cash',
        down_payment     REAL    DEFAULT 0,
        installment_months INTEGER DEFAULT 0,
        sale_date        DATE    NOT NULL,
        status           VARCHAR(20) DEFAULT 'Pending',
        notes            TEXT,
        branch_id        INTEGER REFERENCES branches(id),
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Parts
    cur.execute('''CREATE TABLE IF NOT EXISTS parts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL, brand VARCHAR(100),
        category VARCHAR(50) DEFAULT 'Other',
        price REAL NOT NULL, stock INTEGER DEFAULT 0,
        compatible_with TEXT, description TEXT,
        branch_id INTEGER REFERENCES branches(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Parts Orders
    cur.execute('''CREATE TABLE IF NOT EXISTS parts_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        part_id INTEGER NOT NULL REFERENCES parts(id),
        quantity INTEGER NOT NULL DEFAULT 1,
        total_price REAL NOT NULL,
        status VARCHAR(20) DEFAULT 'Pending',
        notes TEXT,
        branch_id INTEGER REFERENCES branches(id),
        order_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Installments (linked to motor_sales)
    cur.execute('''CREATE TABLE IF NOT EXISTS installments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL REFERENCES motor_sales(id),
        customer_id INTEGER NOT NULL REFERENCES customers(id),
        sale_motor_id INTEGER NOT NULL REFERENCES sale_motors(id),
        total_price REAL NOT NULL, down_payment REAL DEFAULT 0,
        balance_amount REAL NOT NULL, monthly_payment REAL NOT NULL,
        term_months INTEGER NOT NULL, paid_months INTEGER DEFAULT 0,
        next_due_date DATE, status VARCHAR(20) DEFAULT 'Active',
        branch_id INTEGER REFERENCES branches(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Installment Payments
    cur.execute('''CREATE TABLE IF NOT EXISTS installment_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        installment_id INTEGER NOT NULL REFERENCES installments(id),
        amount REAL NOT NULL, pay_date DATE NOT NULL,
        notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Add missing columns if upgrading from old schema
    _add_col(cur, 'admin',        'role',          "VARCHAR(20) DEFAULT 'admin'")
    _add_col(cur, 'admin',        'branch_id',     'INTEGER REFERENCES branches(id)')
    _add_col(cur, 'installments', 'sale_motor_id', 'INTEGER REFERENCES sale_motors(id)')
    _add_col(cur, 'installments', 'sale_id',       'INTEGER REFERENCES motor_sales(id)')
    _add_col(cur, 'rentals',      'branch_id',     'INTEGER REFERENCES branches(id)')
    _add_col(cur, 'motor_sales',  'branch_id',     'INTEGER REFERENCES branches(id)')

    # Default super admin
    cur.execute("SELECT COUNT(*) FROM admin WHERE email=?", ("admin@motorent.com",))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO admin (name,email,password,role) VALUES (?,?,?,?)",
            ("Administrator","admin@motorent.com",generate_password_hash("admin123"),"superadmin"))

    # Default branch
    cur.execute("SELECT COUNT(*) FROM branches")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO branches (name,address,phone,email) VALUES (?,?,?,?)",
            ("MotoRent Main Branch","Main Branch Address","09XX XXX XXXX","admin@motorent.com"))

    # Sample rental motors
    cur.execute("SELECT COUNT(*) FROM rental_motors")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO rental_motors (brand,model,year,type,plate,rate_per_day,status,notes) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("Honda",   "Click 125i",  2023,"Scooter",  "RNT-001",500,"Available","Brand new unit"),
                ("Yamaha",  "NMAX 155",    2022,"Scooter",  "RNT-002",700,"Available",""),
                ("Suzuki",  "Raider R150", 2021,"Sport",    "RNT-003",600,"Available","Slight scratch left fairing"),
                ("Honda",   "ADV 160",     2023,"Scooter",  "RNT-004",900,"Available",""),
                ("Yamaha",  "Mio i125",    2022,"Scooter",  "RNT-005",450,"Available",""),
                ("Kawasaki","Barako II",   2020,"Underbone","RNT-006",400,"Under Maintenance","Engine check"),
            ]
        )

    # Sample sale motors
    cur.execute("SELECT COUNT(*) FROM sale_motors")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO sale_motors (brand,model,year,type,plate,selling_price,status,notes) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("Honda",  "Click 125i",  2023,"Scooter","SLE-001", 65000,"Available","Brand new"),
                ("Yamaha", "NMAX 155",    2022,"Scooter","SLE-002", 98000,"Available",""),
                ("Honda",  "ADV 160",     2023,"Scooter","SLE-003",130000,"Available",""),
                ("Suzuki", "Raider R150", 2021,"Sport",  "SLE-004", 80000,"Available",""),
                ("Yamaha", "Mio i125",    2022,"Scooter","SLE-005", 55000,"Available",""),
            ]
        )

    # Sample parts
    cur.execute("SELECT COUNT(*) FROM parts")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO parts (name,brand,category,price,stock,compatible_with,description) VALUES (?,?,?,?,?,?,?)",
            [
                ("Air Filter",      "Honda OEM", "Engine",  350, 20,"Honda Click 125i","Genuine filter"),
                ("Brake Pads",      "Daytona",   "Brakes",  480, 15,"Universal Disc",  "High performance"),
                ("Engine Oil 1L",   "Motul",     "Engine",  220, 50,"All motors",      "10W-30"),
                ("Drive Belt",      "Yamaha OEM","Engine",  850,  8,"Yamaha NMAX",     "25000km service"),
                ("Spark Plug",      "NGK",       "Engine",  180, 30,"Universal",       "CR8E"),
                ("Headlight Bulb",  "Osram",     "Electrical",250,25,"Universal H4",   "55W halogen"),
            ]
        )

    conn.commit()
    conn.close()


def _add_col(cur, table, column, col_type):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except:
        pass


# ─────────────────────────────────────────────
#  GENERIC CRUD
# ─────────────────────────────────────────────

def _conn_exec(sql, params=()):
    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(sql, params); conn.commit(); return cur.lastrowid or True
    except Exception as e:
        print("DB error:", e); conn.rollback(); return None
    finally:
        conn.close()

def _fetchall(sql, params=()):
    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(sql, params); return cur.fetchall()
    finally:
        conn.close()

def _fetchone(sql, params=()):
    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(sql, params); return cur.fetchone()
    finally:
        conn.close()

def addrecord(table, **kwargs):
    fields = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", tuple(kwargs.values()))
        conn.commit(); return cur.lastrowid
    except Exception as e:
        print("addrecord error:", e); conn.rollback(); return None
    finally:
        conn.close()

def updaterecord(table, idfield, idvalue, **kwargs):
    set_clause = ", ".join([f"{k}=?" for k in kwargs.keys()])
    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(f"UPDATE {table} SET {set_clause} WHERE {idfield}=?",
                    tuple(kwargs.values()) + (idvalue,))
        conn.commit(); return cur.rowcount > 0
    except Exception as e:
        print("updaterecord error:", e); conn.rollback(); return False
    finally:
        conn.close()

def deleterecord(table, **kwargs):
    field = list(kwargs.keys())[0]; value = kwargs[field]
    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM {table} WHERE {field}=?", (value,))
        conn.commit(); return cur.rowcount > 0
    except Exception as e:
        print("deleterecord error:", e); conn.rollback(); return False
    finally:
        conn.close()

def recordexists(table, **kwargs):
    field = list(kwargs.keys())[0]; value = kwargs[field]
    try:
        row = _fetchone(f"SELECT COUNT(*) FROM {table} WHERE {field}=?", (value,))
        return row[0] > 0
    except: return False

def recordexists_exclude(table, field, value, exclude_field, exclude_value):
    try:
        row = _fetchone(f"SELECT COUNT(*) FROM {table} WHERE {field}=? AND {exclude_field}!=?",
                        (value, exclude_value))
        return row[0] > 0
    except: return False

def getone(table, **kwargs):
    field = list(kwargs.keys())[0]; value = kwargs[field]
    return _fetchone(f"SELECT * FROM {table} WHERE {field}=?", (value,))


# ─────────────────────────────────────────────
#  CUSTOMERS
# ─────────────────────────────────────────────
def get_customer_by_email(email): return getone('customers', email=email)
def get_customer_by_id(cid):      return getone('customers', id=cid)
def get_all_customers():          return _fetchall("SELECT * FROM customers ORDER BY lastname")
def delete_customer(cid):         return deleterecord('customers', id=cid)


# ─────────────────────────────────────────────
#  ADMIN
# ─────────────────────────────────────────────
def get_admin_by_email(email): return getone('admin', email=email)


# ─────────────────────────────────────────────
#  RENTAL MOTORS
# ─────────────────────────────────────────────
def get_all_rental_motors(branch_id=None):
    if branch_id:
        return _fetchall("SELECT * FROM rental_motors WHERE branch_id=? ORDER BY brand,model", (branch_id,))
    return _fetchall("SELECT * FROM rental_motors ORDER BY brand,model")

def get_rental_motor_by_id(mid): return getone('rental_motors', id=mid)

def add_rental_motor(brand, model, year, type_, plate, rate_per_day,
                     status='Available', notes='', branch_id=None):
    return addrecord('rental_motors', brand=brand, model=model, year=year, type=type_,
                     plate=plate, rate_per_day=rate_per_day, status=status,
                     notes=notes, branch_id=branch_id)

def update_rental_motor(mid, **kwargs): return updaterecord('rental_motors', 'id', mid, **kwargs)
def delete_rental_motor(mid):           return deleterecord('rental_motors', id=mid)

def get_rental_motors_by_status(status, branch_id=None):
    if branch_id:
        return _fetchall("SELECT * FROM rental_motors WHERE status=? AND branch_id=?", (status, branch_id))
    return _fetchall("SELECT * FROM rental_motors WHERE status=?", (status,))


# ─────────────────────────────────────────────
#  SALE MOTORS
# ─────────────────────────────────────────────
def get_all_sale_motors(branch_id=None):
    if branch_id:
        return _fetchall("SELECT * FROM sale_motors WHERE branch_id=? ORDER BY brand,model", (branch_id,))
    return _fetchall("SELECT * FROM sale_motors ORDER BY brand,model")

def get_sale_motor_by_id(mid): return getone('sale_motors', id=mid)

def add_sale_motor(brand, model, year, type_, plate, selling_price,
                   status='Available', notes='', branch_id=None):
    return addrecord('sale_motors', brand=brand, model=model, year=year, type=type_,
                     plate=plate, selling_price=selling_price, status=status,
                     notes=notes, branch_id=branch_id)

def update_sale_motor(mid, **kwargs): return updaterecord('sale_motors', 'id', mid, **kwargs)
def delete_sale_motor(mid):           return deleterecord('sale_motors', id=mid)

def get_available_sale_motors(branch_id=None):
    if branch_id:
        return _fetchall("SELECT * FROM sale_motors WHERE status='Available' AND branch_id=?", (branch_id,))
    return _fetchall("SELECT * FROM sale_motors WHERE status='Available'")


# ─────────────────────────────────────────────
#  RENTALS
# ─────────────────────────────────────────────
def get_all_rentals(branch_id=None):
    q = '''SELECT r.id,
               c.firstname||' '||c.lastname AS customer, c.phone,
               rm.brand||' '||rm.model AS motor, rm.plate,
               r.start_date, r.end_date, r.total_cost,
               r.status, r.notes, r.created_at, r.customer_id, r.motor_id
           FROM rentals r
           JOIN customers c ON c.id=r.customer_id
           JOIN rental_motors rm ON rm.id=r.motor_id'''
    if branch_id:
        return _fetchall(q + " WHERE r.branch_id=? ORDER BY r.created_at DESC", (branch_id,))
    return _fetchall(q + " ORDER BY r.created_at DESC")

def get_rentals_by_customer(cid):
    return _fetchall('''SELECT r.id, rm.brand||' '||rm.model AS motor, rm.plate,
               r.start_date, r.end_date, r.total_cost, r.status, r.notes, r.created_at
           FROM rentals r JOIN rental_motors rm ON rm.id=r.motor_id
           WHERE r.customer_id=? ORDER BY r.created_at DESC''', (cid,))

def get_rental_by_id(rid):              return getone('rentals', id=rid)
def update_rental_status(rid, status):  return updaterecord('rentals', 'id', rid, status=status)
def delete_rental(rid):                 return deleterecord('rentals', id=rid)

def add_rental(customer_id, motor_id, start_date, end_date, total_cost, notes='', branch_id=None):
    return addrecord('rentals', customer_id=customer_id, motor_id=motor_id,
                     start_date=start_date, end_date=end_date, total_cost=total_cost,
                     status='Pending', notes=notes, branch_id=branch_id)


# ─────────────────────────────────────────────
#  MOTOR SALES (transactions)
# ─────────────────────────────────────────────
def get_all_motor_sales(branch_id=None):
    q = '''SELECT ms.id,
               c.firstname||' '||c.lastname AS customer,
               sm.brand||' '||sm.model AS motor, sm.plate,
               ms.total_price, ms.payment_type, ms.down_payment,
               ms.installment_months, ms.sale_date, ms.status,
               ms.notes, ms.created_at, ms.customer_id, ms.sale_motor_id AS motor_id
           FROM motor_sales ms
           JOIN customers c ON c.id=ms.customer_id
           JOIN sale_motors sm ON sm.id=ms.sale_motor_id'''
    if branch_id:
        return _fetchall(q + " WHERE ms.branch_id=? ORDER BY ms.created_at DESC", (branch_id,))
    return _fetchall(q + " ORDER BY ms.created_at DESC")

def get_motor_sale_by_id(sid):
    row = _fetchone('''SELECT ms.*, ms.sale_motor_id AS motor_id,
               ms.installment_months
           FROM motor_sales ms WHERE ms.id=?''', (sid,))
    return row

def add_motor_sale(customer_id, sale_motor_id, total_price, payment_type,
                   sale_date, down_payment=0, installment_months=0, notes='', branch_id=None):
    return addrecord('motor_sales', customer_id=customer_id, sale_motor_id=sale_motor_id,
                     total_price=total_price, payment_type=payment_type, sale_date=sale_date,
                     down_payment=down_payment, installment_months=installment_months,
                     notes=notes, status='Pending', branch_id=branch_id)

def confirm_motor_sale(sid):  return updaterecord('motor_sales', 'id', sid, status='Confirmed')
def delete_motor_sale(sid):   return deleterecord('motor_sales', id=sid)

def get_sale_motors_by_customer(cid):
    return _fetchall('''SELECT ms.id, sm.brand||' '||sm.model AS motor, sm.plate,
               ms.total_price, ms.payment_type, ms.sale_date, ms.status
           FROM motor_sales ms JOIN sale_motors sm ON sm.id=ms.sale_motor_id
           WHERE ms.customer_id=? ORDER BY ms.created_at DESC''', (cid,))


# ─────────────────────────────────────────────
#  PARTS
# ─────────────────────────────────────────────
def get_all_parts(branch_id=None):
    if branch_id:
        return _fetchall("SELECT * FROM parts WHERE branch_id=? OR branch_id IS NULL ORDER BY category,name", (branch_id,))
    return _fetchall("SELECT * FROM parts ORDER BY category,name")

def get_part_by_id(pid): return getone('parts', id=pid)

def add_part(name, brand, category, price, stock, compatible_with='', description='', branch_id=None):
    return addrecord('parts', name=name, brand=brand, category=category, price=price,
                     stock=stock, compatible_with=compatible_with, description=description, branch_id=branch_id)

def update_part(pid, **kwargs): return updaterecord('parts', 'id', pid, **kwargs)
def delete_part(pid):           return deleterecord('parts', id=pid)


# ─────────────────────────────────────────────
#  PARTS ORDERS
# ─────────────────────────────────────────────
def get_all_orders(branch_id=None):
    q = '''SELECT po.id, c.firstname||' '||c.lastname AS customer,
               p.name AS part_name, po.quantity, po.total_price,
               po.status, po.order_date, po.notes, po.created_at,
               po.customer_id, po.part_id
           FROM parts_orders po
           JOIN customers c ON c.id=po.customer_id
           JOIN parts p ON p.id=po.part_id'''
    if branch_id:
        return _fetchall(q + " WHERE po.branch_id=? ORDER BY po.created_at DESC", (branch_id,))
    return _fetchall(q + " ORDER BY po.created_at DESC")

def get_orders_by_customer(cid):
    return _fetchall('''SELECT po.id, p.name AS part_name, po.quantity,
               po.total_price, po.order_date, po.status
           FROM parts_orders po JOIN parts p ON p.id=po.part_id
           WHERE po.customer_id=? ORDER BY po.created_at DESC''', (cid,))

def add_order(customer_id, part_id, quantity, total_price, notes='', branch_id=None):
    from datetime import date
    return addrecord('parts_orders', customer_id=customer_id, part_id=part_id,
                     quantity=quantity, total_price=total_price, notes=notes,
                     status='Pending', branch_id=branch_id, order_date=str(date.today()))

def update_order_status(oid, status): return updaterecord('parts_orders', 'id', oid, status=status)
def delete_order(oid):                return deleterecord('parts_orders', id=oid)


# ─────────────────────────────────────────────
#  INSTALLMENTS
# ─────────────────────────────────────────────
def get_all_installments(branch_id=None):
    q = '''SELECT i.id, c.firstname||' '||c.lastname AS customer,
               c.email AS customer_email,
               COALESCE(sm.brand||' '||sm.model, 'Unknown Motor') AS motor,
               COALESCE(sm.plate, '—') AS plate,
               i.total_price, i.down_payment, i.balance_amount,
               i.monthly_payment, i.term_months, i.paid_months,
               i.next_due_date, i.status, i.created_at, i.sale_id
           FROM installments i
           JOIN customers c ON c.id=i.customer_id
           LEFT JOIN sale_motors sm ON sm.id=i.sale_motor_id
               OR sm.id=(SELECT ms2.sale_motor_id FROM motor_sales ms2 WHERE ms2.id=i.sale_id)'''
    if branch_id:
        return _fetchall(q + " WHERE i.branch_id=? ORDER BY i.created_at DESC", (branch_id,))
    return _fetchall(q + " ORDER BY i.created_at DESC")

def get_installment_by_id(iid): return getone('installments', id=iid)

def record_installment_payment(inst_id, amount, pay_date, notes=''):
    from datetime import date
    inst = get_installment_by_id(inst_id)
    if not inst: return False
    addrecord('installment_payments', installment_id=inst_id,
              amount=amount, pay_date=pay_date, notes=notes)
    new_paid    = (inst['paid_months'] or 0) + 1
    new_balance = max(0, (inst['balance_amount'] or 0) - amount)
    today = date.today()
    next_due = date(today.year+1, 1, today.day).isoformat() if today.month == 12 \
               else date(today.year, today.month+1, today.day).isoformat()
    new_status = 'Paid Off' if new_paid >= inst['term_months'] or new_balance <= 0 else 'Active'
    return updaterecord('installments', 'id', inst_id,
                        paid_months=new_paid, balance_amount=new_balance,
                        next_due_date=next_due if new_status != 'Paid Off' else None,
                        status=new_status)

def get_installment_payments(iid):
    return _fetchall("SELECT * FROM installment_payments WHERE installment_id=? ORDER BY pay_date DESC", (iid,))

def get_installments_by_customer(cid):
    return _fetchall('''SELECT i.id,
               COALESCE(sm.brand||' '||sm.model, 'Unknown Motor') AS motor,
               COALESCE(sm.plate, '—') AS plate,
               i.total_price, i.down_payment, i.balance_amount,
               i.monthly_payment, i.term_months, i.paid_months,
               i.next_due_date, i.status
           FROM installments i
           LEFT JOIN sale_motors sm ON sm.id=i.sale_motor_id
               OR sm.id=(SELECT ms2.sale_motor_id FROM motor_sales ms2 WHERE ms2.id=i.sale_id)
           WHERE i.customer_id=? ORDER BY i.created_at DESC''', (cid,))


# ─────────────────────────────────────────────
#  BRANCHES
# ─────────────────────────────────────────────
def get_all_branches():
    return _fetchall('''SELECT b.*,
               (SELECT COUNT(*) FROM rental_motors rm WHERE rm.branch_id=b.id) AS rental_motor_count,
               (SELECT COUNT(*) FROM sale_motors sm WHERE sm.branch_id=b.id) AS sale_motor_count,
               (SELECT COUNT(*) FROM admin a WHERE a.branch_id=b.id) AS admin_count,
               (SELECT COUNT(*) FROM rentals r WHERE r.branch_id=b.id AND r.status='Rented') AS active_rentals,
               (SELECT COUNT(*) FROM motor_sales ms WHERE ms.branch_id=b.id) AS sale_count,
               (SELECT COALESCE(SUM(ms.total_price),0) FROM motor_sales ms WHERE ms.branch_id=b.id AND ms.status='Confirmed') AS revenue
           FROM branches b ORDER BY b.created_at''')

def get_branch_by_id(bid):    return getone('branches', id=bid)
def add_branch(**kwargs):     return addrecord('branches', **kwargs)
def update_branch(bid, **kw): return updaterecord('branches', 'id', bid, **kw)
def delete_branch(bid):       return deleterecord('branches', id=bid)


# ─────────────────────────────────────────────
#  DASHBOARD STATS
# ─────────────────────────────────────────────
def get_dashboard_stats(branch_id=None):
    bf = "AND branch_id=?" if branch_id else ""
    p  = (branch_id,) if branch_id else ()

    def q(sql, extra=()):
        row = _fetchone(sql, p + extra)
        return row[0] if row else 0

    return {
        # Rental stats
        'available':       q(f"SELECT COUNT(*) FROM rental_motors WHERE status='Available' {bf}"),
        'rented':          q(f"SELECT COUNT(*) FROM rental_motors WHERE status='Rented' {bf}"),
        'overdue':         q(f"SELECT COUNT(*) FROM rentals WHERE status='Overdue' {bf}"),
        'pending':         q(f"SELECT COUNT(*) FROM rentals WHERE status='Pending' {bf}"),
        'rental_revenue':  q(f"SELECT COALESCE(SUM(total_cost),0) FROM rentals WHERE status='Returned' {bf}"),
        # Sale motor stats
        'sale_motors_available': q(f"SELECT COUNT(*) FROM sale_motors WHERE status='Available' {bf}"),
        'sale_motors_sold':      q(f"SELECT COUNT(*) FROM sale_motors WHERE status='Sold' {bf}"),
        'motor_sales_count':     q(f"SELECT COUNT(*) FROM motor_sales WHERE status='Confirmed' {bf}"),
        'motor_sales_revenue':   q(f"SELECT COALESCE(SUM(total_price),0) FROM motor_sales WHERE status='Confirmed' {bf}"),
        # Parts stats
        'parts_orders_pending':  q(f"SELECT COUNT(*) FROM parts_orders WHERE status='Pending' {bf}"),
        'parts_orders_revenue':  q(f"SELECT COALESCE(SUM(total_price),0) FROM parts_orders WHERE status='Completed' {bf}"),
        # Shared
        'total_customers':  q("SELECT COUNT(*) FROM customers"),
        'active_installments': q(f"SELECT COUNT(*) FROM installments WHERE status='Active' {bf}"),
    }


# ─────────────────────────────────────────────
#  COMPATIBILITY ALIASES  (used by app.py)
# ─────────────────────────────────────────────

# app.py calls get_all_motors() → returns rental motors for admin view
def get_all_motors(branch_id=None):
    return get_all_rental_motors(branch_id)

def get_motor_by_id(mid):
    return get_rental_motor_by_id(mid)

def add_motor(brand, model, year, type_, plate, rate_per_day,
              status='Available', notes='', selling_price=None,
              for_sale=0, branch_id=None):
    """Routes to rental or sale motor table based on for_sale flag."""
    if for_sale:
        return add_sale_motor(brand, model, year, type_, plate,
                              selling_price or 0, status, notes, branch_id)
    return add_rental_motor(brand, model, year, type_, plate,
                            rate_per_day, status, notes, branch_id)

def update_motor(mid, **kwargs):
    """Try rental_motors first; on failure try sale_motors."""
    # Remove sale-only keys before hitting rental table
    sale_kwargs = {k: v for k, v in kwargs.items() if k != 'rate_per_day'}
    rental_kwargs = kwargs
    result = update_rental_motor(mid, **rental_kwargs)
    if not result:
        result = update_sale_motor(mid, **sale_kwargs)
    return result

def delete_motor(mid):
    r = delete_rental_motor(mid)
    if not r:
        r = delete_sale_motor(mid)
    return r

def get_motors_by_status(status, branch_id=None):
    return get_rental_motors_by_status(status, branch_id)

def get_motors_for_sale(branch_id=None):
    return get_available_sale_motors(branch_id)

# app.py: add_sale(customer_id, motor_id, total_price, ...)
#         motor_id here refers to sale_motor_id
def add_sale(customer_id, motor_id, total_price, payment_type='Cash',
             sale_date=None, down_payment=0, installment_months=0,
             notes='', branch_id=None):
    from datetime import date as _date
    return add_motor_sale(customer_id, motor_id, total_price, payment_type,
                          sale_date or str(_date.today()),
                          down_payment, installment_months, notes, branch_id)

def get_all_sales(branch_id=None):   return get_all_motor_sales(branch_id)
def get_sale_by_id(sid):             return get_motor_sale_by_id(sid)
def confirm_sale(sid):               return confirm_motor_sale(sid)
def delete_sale(sid):                return delete_motor_sale(sid)
def get_sales_by_customer(cid):      return get_sale_motors_by_customer(cid)

# app.py: create_installment(sale_id, customer_id, motor_id, ...)
#         motor_id here is sale_motor_id
def create_installment(sale_id, customer_id, motor_id, total_price,
                        down_payment, term_months, branch_id=None):
    from datetime import date as _date
    balance = total_price - down_payment
    monthly = round(balance / term_months, 2) if term_months > 0 else balance
    today   = _date.today()
    next_due = (_date(today.year + 1, 1, today.day)
                if today.month == 12
                else _date(today.year, today.month + 1, today.day)).isoformat()
    return addrecord('installments',
                     sale_id=sale_id, customer_id=customer_id,
                     sale_motor_id=motor_id, total_price=total_price,
                     down_payment=down_payment, balance_amount=balance,
                     monthly_payment=monthly, term_months=term_months,
                     paid_months=0, next_due_date=next_due,
                     status='Active', branch_id=branch_id)