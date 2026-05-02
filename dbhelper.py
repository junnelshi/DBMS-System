import sqlite3
import os
from werkzeug.security import generate_password_hash

# ─────────────────────────────────────────────
#  CONNECTION
# ─────────────────────────────────────────────

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

    # ── Branches ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100) NOT NULL,
            address    TEXT         NOT NULL,
            phone      VARCHAR(20),
            email      VARCHAR(100),
            active     INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Customers ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            firstname    VARCHAR(50)  NOT NULL,
            lastname     VARCHAR(50)  NOT NULL,
            email        VARCHAR(100) UNIQUE NOT NULL,
            phone        VARCHAR(20)  NOT NULL,
            birthdate    DATE         NOT NULL,
            address      TEXT         NOT NULL,
            license_no   VARCHAR(50)  UNIQUE NOT NULL,
            password     VARCHAR(255) NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Admin ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(100) UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            role       VARCHAR(20)  DEFAULT 'admin',
            branch_id  INTEGER REFERENCES branches(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Motors ── (added selling_price, for_sale columns)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS motors (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            brand         VARCHAR(50)  NOT NULL,
            model         VARCHAR(50)  NOT NULL,
            year          INTEGER      NOT NULL,
            type          VARCHAR(30)  NOT NULL,
            plate         VARCHAR(20)  UNIQUE NOT NULL,
            rate_per_day  REAL         NOT NULL,
            selling_price REAL,
            for_sale      INTEGER DEFAULT 0,
            status        VARCHAR(30)  DEFAULT 'Available',
            branch_id     INTEGER REFERENCES branches(id),
            notes         TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Rentals ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS rentals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            motor_id    INTEGER NOT NULL,
            start_date  DATE    NOT NULL,
            end_date    DATE    NOT NULL,
            total_cost  REAL    NOT NULL,
            status      VARCHAR(20) DEFAULT 'Pending',
            notes       TEXT,
            branch_id   INTEGER REFERENCES branches(id),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (motor_id)    REFERENCES motors(id)
        )
    ''')

    # ── Sales ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id    INTEGER NOT NULL REFERENCES customers(id),
            motor_id       INTEGER NOT NULL REFERENCES motors(id),
            total_price    REAL    NOT NULL,
            payment_type   VARCHAR(20) DEFAULT 'Cash',
            down_payment   REAL    DEFAULT 0,
            installment_months INTEGER DEFAULT 0,
            sale_date      DATE    NOT NULL,
            status         VARCHAR(20) DEFAULT 'Pending',
            notes          TEXT,
            branch_id      INTEGER REFERENCES branches(id),
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Parts ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            VARCHAR(100) NOT NULL,
            brand           VARCHAR(100),
            category        VARCHAR(50)  DEFAULT 'Other',
            price           REAL         NOT NULL,
            stock           INTEGER      DEFAULT 0,
            compatible_with TEXT,
            description     TEXT,
            branch_id       INTEGER REFERENCES branches(id),
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Parts Orders ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parts_orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            part_id     INTEGER NOT NULL REFERENCES parts(id),
            quantity    INTEGER NOT NULL DEFAULT 1,
            total_price REAL    NOT NULL,
            status      VARCHAR(20) DEFAULT 'Pending',
            notes       TEXT,
            branch_id   INTEGER REFERENCES branches(id),
            order_date  DATE    NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Installments ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS installments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id         INTEGER NOT NULL REFERENCES sales(id),
            customer_id     INTEGER NOT NULL REFERENCES customers(id),
            motor_id        INTEGER NOT NULL REFERENCES motors(id),
            total_price     REAL    NOT NULL,
            down_payment    REAL    DEFAULT 0,
            balance_amount  REAL    NOT NULL,
            monthly_payment REAL    NOT NULL,
            term_months     INTEGER NOT NULL,
            paid_months     INTEGER DEFAULT 0,
            next_due_date   DATE,
            status          VARCHAR(20) DEFAULT 'Active',
            branch_id       INTEGER REFERENCES branches(id),
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Installment Payments ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS installment_payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            installment_id  INTEGER NOT NULL REFERENCES installments(id),
            amount          REAL    NOT NULL,
            pay_date        DATE    NOT NULL,
            notes           TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Migrate old tables ──
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        cur.execute("INSERT OR IGNORE INTO admin (id, name, email, password, created_at) SELECT id, name, email, password, created_at FROM users")
        cur.execute("DROP TABLE users")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students'")
    if cur.fetchone():
        cur.execute("DROP TABLE students")

    # ── Add new columns to existing tables if missing ──
    _add_column_if_missing(cur, 'motors',  'selling_price', 'REAL')
    _add_column_if_missing(cur, 'motors',  'for_sale',      'INTEGER DEFAULT 0')
    _add_column_if_missing(cur, 'motors',  'branch_id',     'INTEGER REFERENCES branches(id)')
    _add_column_if_missing(cur, 'rentals', 'branch_id',     'INTEGER REFERENCES branches(id)')
    _add_column_if_missing(cur, 'admin',   'role',          "VARCHAR(20) DEFAULT 'admin'")
    _add_column_if_missing(cur, 'admin',   'branch_id',     'INTEGER REFERENCES branches(id)')

    # ── Default super admin ──
    cur.execute("SELECT COUNT(*) FROM admin WHERE email = ?", ("admin@motorent.com",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO admin (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Administrator", "admin@motorent.com", generate_password_hash("admin123"), "superadmin")
        )

    # ── Default branch ──
    cur.execute("SELECT COUNT(*) FROM branches")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO branches (name, address, phone, email) VALUES (?, ?, ?, ?)",
            ("MotoRent Main Branch", "Main Branch Address", "09XX XXX XXXX", "admin@motorent.com")
        )

    # ── Sample motors ──
    cur.execute("SELECT COUNT(*) FROM motors")
    if cur.fetchone()[0] == 0:
        sample_motors = [
            ("Honda",    "Click 125i",  2023, "Scooter",   "ABC 1234", 500,  65000, 1, "Available", "Brand new unit"),
            ("Yamaha",   "NMAX 155",    2022, "Scooter",   "XYZ 5678", 700,  98000, 1, "Available", ""),
            ("Suzuki",   "Raider R150", 2021, "Sport",     "DEF 9012", 600,  80000, 1, "Available", "Slight scratch on left fairing"),
            ("Honda",    "ADV 160",     2023, "Scooter",   "GHI 3456", 900,  130000, 1, "Available", ""),
            ("Kawasaki", "Barako II",   2020, "Underbone", "JKL 7890", 400,  0, 0,   "Under Maintenance", "Engine check"),
            ("Yamaha",   "Mio i125",    2022, "Scooter",   "MNO 1234", 450,  55000, 1, "Available", ""),
        ]
        cur.executemany(
            "INSERT INTO motors (brand, model, year, type, plate, rate_per_day, selling_price, for_sale, status, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            sample_motors
        )

    # ── Sample parts ──
    cur.execute("SELECT COUNT(*) FROM parts")
    if cur.fetchone()[0] == 0:
        sample_parts = [
            ("Air Filter",       "Honda OEM",    "Engine",     350,  20, "Honda Click 125i, ADV 160",    "Genuine Honda air filter"),
            ("Brake Pads (Set)", "Daytona",      "Brakes",     480,  15, "Universal Disc",               "High performance brake pads"),
            ("Engine Oil 1L",    "Motul 3000",   "Engine",     220,  50, "All motors",                   "10W-30 mineral oil"),
            ("Drive Belt",       "Yamaha OEM",   "Engine",     850,  8,  "Yamaha NMAX 155, Mio i125",    "Original belt, 25000km service"),
            ("Tire (Front)",     "IRC",          "Tires",      1200, 10, "70/90-17",                     "Standard front tire"),
            ("Spark Plug",       "NGK",          "Engine",     180,  30, "Universal",                    "CR8E standard spark plug"),
            ("Headlight Bulb",   "Osram",        "Electrical", 250,  25, "Universal H4",                 "55W halogen bulb"),
        ]
        cur.executemany(
            "INSERT INTO parts (name, brand, category, price, stock, compatible_with, description) VALUES (?,?,?,?,?,?,?)",
            sample_parts
        )

    conn.commit()
    conn.close()


def _add_column_if_missing(cur, table, column, col_type):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except:
        pass  # column already exists


# ─────────────────────────────────────────────
#  GENERIC CRUD
# ─────────────────────────────────────────────

def getall(table):
    conn = connect()
    cur  = conn.cursor()
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    conn.close()
    return rows

def getone(table, **kwargs):
    conn  = connect()
    cur   = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"SELECT * FROM {table} WHERE {field} = ?", (value,))
        return cur.fetchone()
    except Exception as e:
        print("getone error:", e)
        return None
    finally:
        conn.close()

def addrecord(table, **kwargs):
    conn         = connect()
    cur          = conn.cursor()
    fields       = ", ".join(kwargs.keys())
    placeholders = ", ".join(["?"] * len(kwargs))
    values       = tuple(kwargs.values())
    try:
        cur.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", values)
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print("addrecord error:", e)
        conn.rollback()
        return None
    finally:
        conn.close()

def updaterecord(table, idfield, idvalue, **kwargs):
    conn       = connect()
    cur        = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values     = tuple(kwargs.values()) + (idvalue,)
    try:
        cur.execute(f"UPDATE {table} SET {set_clause} WHERE {idfield} = ?", values)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("updaterecord error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()

def deleterecord(table, **kwargs):
    conn  = connect()
    cur   = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"DELETE FROM {table} WHERE {field} = ?", (value,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print("deleterecord error:", e)
        conn.rollback()
        return False
    finally:
        conn.close()

def recordexists(table, **kwargs):
    conn  = connect()
    cur   = conn.cursor()
    field = list(kwargs.keys())[0]
    value = kwargs[field]
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} = ?", (value,))
        return cur.fetchone()[0] > 0
    except:
        return False
    finally:
        conn.close()

def recordexists_exclude(table, field, value, exclude_field, exclude_value):
    conn = connect()
    cur  = conn.cursor()
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {field} = ? AND {exclude_field} != ?",
            (value, exclude_value)
        )
        return cur.fetchone()[0] > 0
    except:
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
#  CUSTOMER FUNCTIONS
# ─────────────────────────────────────────────

def get_customer_by_email(email):   return getone('customers', email=email)
def get_customer_by_id(cid):        return getone('customers', id=cid)
def get_all_customers():            return getall('customers')
def delete_customer(cid):           return deleterecord('customers', id=cid)


# ─────────────────────────────────────────────
#  ADMIN FUNCTIONS
# ─────────────────────────────────────────────

def get_admin_by_email(email):  return getone('admin', email=email)
def get_all_admins():           return getall('admin')
def delete_admin(aid):          return deleterecord('admin', id=aid)


# ─────────────────────────────────────────────
#  MOTOR FUNCTIONS
# ─────────────────────────────────────────────

def get_all_motors(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    if branch_id:
        cur.execute("SELECT * FROM motors WHERE branch_id = ?", (branch_id,))
    else:
        cur.execute("SELECT * FROM motors")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_motor_by_id(motor_id):  return getone('motors', id=motor_id)

def add_motor(brand, model, year, type_, plate, rate_per_day, status='Available',
              notes='', selling_price=None, for_sale=0, branch_id=None):
    return addrecord('motors',
        brand=brand, model=model, year=year, type=type_,
        plate=plate, rate_per_day=rate_per_day, status=status, notes=notes,
        selling_price=selling_price, for_sale=for_sale, branch_id=branch_id
    )

def update_motor(motor_id, **kwargs): return updaterecord('motors', 'id', motor_id, **kwargs)
def delete_motor(motor_id):           return deleterecord('motors', id=motor_id)

def get_motors_by_status(status, branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    if branch_id:
        cur.execute("SELECT * FROM motors WHERE status = ? AND branch_id = ?", (status, branch_id))
    else:
        cur.execute("SELECT * FROM motors WHERE status = ?", (status,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_motors_for_sale(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    if branch_id:
        cur.execute("SELECT * FROM motors WHERE for_sale = 1 AND status = 'Available' AND branch_id = ?", (branch_id,))
    else:
        cur.execute("SELECT * FROM motors WHERE for_sale = 1 AND status = 'Available'")
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  RENTAL FUNCTIONS
# ─────────────────────────────────────────────

def get_all_rentals(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    query = '''
        SELECT r.id,
               c.firstname || ' ' || c.lastname AS customer,
               c.phone,
               m.brand || ' ' || m.model AS motor,
               m.plate, r.start_date, r.end_date,
               r.total_cost, r.status, r.notes, r.created_at,
               r.customer_id, r.motor_id
        FROM rentals r
        JOIN customers c ON c.id = r.customer_id
        JOIN motors    m ON m.id = r.motor_id
    '''
    if branch_id:
        query += ' WHERE r.branch_id = ?'
        cur.execute(query + ' ORDER BY r.created_at DESC', (branch_id,))
    else:
        cur.execute(query + ' ORDER BY r.created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_rentals_by_customer(customer_id):
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT r.id, m.brand || ' ' || m.model AS motor, m.plate,
               r.start_date, r.end_date, r.total_cost, r.status, r.notes, r.created_at
        FROM rentals r JOIN motors m ON m.id = r.motor_id
        WHERE r.customer_id = ? ORDER BY r.created_at DESC
    ''', (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_rental_by_id(rental_id):           return getone('rentals', id=rental_id)
def update_rental_status(rental_id, stat): return updaterecord('rentals', 'id', rental_id, status=stat)
def delete_rental(rental_id):              return deleterecord('rentals', id=rental_id)

def add_rental(customer_id, motor_id, start_date, end_date, total_cost, notes='', branch_id=None):
    return addrecord('rentals',
        customer_id=customer_id, motor_id=motor_id,
        start_date=start_date, end_date=end_date,
        total_cost=total_cost, status='Pending', notes=notes, branch_id=branch_id
    )


# ─────────────────────────────────────────────
#  SALES FUNCTIONS
# ─────────────────────────────────────────────

def get_all_sales(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    query = '''
        SELECT s.id,
               c.firstname || ' ' || c.lastname AS customer,
               m.brand || ' ' || m.model AS motor,
               m.plate, s.total_price, s.payment_type,
               s.down_payment, s.installment_months,
               s.sale_date, s.status, s.notes, s.created_at,
               s.customer_id, s.motor_id
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        JOIN motors    m ON m.id = s.motor_id
    '''
    if branch_id:
        query += ' WHERE s.branch_id = ?'
        cur.execute(query + ' ORDER BY s.created_at DESC', (branch_id,))
    else:
        cur.execute(query + ' ORDER BY s.created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return rows

def add_sale(customer_id, motor_id, total_price, payment_type, sale_date,
             down_payment=0, installment_months=0, notes='', branch_id=None):
    return addrecord('sales',
        customer_id=customer_id, motor_id=motor_id,
        total_price=total_price, payment_type=payment_type,
        sale_date=sale_date, down_payment=down_payment,
        installment_months=installment_months, notes=notes,
        status='Pending', branch_id=branch_id
    )

def confirm_sale(sale_id):  return updaterecord('sales', 'id', sale_id, status='Confirmed')
def delete_sale(sale_id):   return deleterecord('sales', id=sale_id)
def get_sale_by_id(sid):    return getone('sales', id=sid)

def get_sales_by_customer(customer_id):
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT s.id, m.brand || ' ' || m.model AS motor, m.plate,
               s.total_price, s.payment_type, s.sale_date, s.status
        FROM sales s JOIN motors m ON m.id = s.motor_id
        WHERE s.customer_id = ? ORDER BY s.created_at DESC
    ''', (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  PARTS FUNCTIONS
# ─────────────────────────────────────────────

def get_all_parts(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    if branch_id:
        cur.execute("SELECT * FROM parts WHERE branch_id = ? OR branch_id IS NULL ORDER BY category, name", (branch_id,))
    else:
        cur.execute("SELECT * FROM parts ORDER BY category, name")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_part_by_id(part_id):  return getone('parts', id=part_id)

def add_part(name, brand, category, price, stock, compatible_with='', description='', branch_id=None):
    return addrecord('parts',
        name=name, brand=brand, category=category, price=price,
        stock=stock, compatible_with=compatible_with,
        description=description, branch_id=branch_id
    )

def update_part(part_id, **kwargs): return updaterecord('parts', 'id', part_id, **kwargs)
def delete_part(part_id):           return deleterecord('parts', id=part_id)


# ─────────────────────────────────────────────
#  PARTS ORDERS
# ─────────────────────────────────────────────

def get_all_orders(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    query = '''
        SELECT po.id,
               c.firstname || ' ' || c.lastname AS customer,
               p.name AS part_name,
               po.quantity, po.total_price, po.status,
               po.order_date, po.notes, po.created_at,
               po.customer_id, po.part_id
        FROM parts_orders po
        JOIN customers c ON c.id = po.customer_id
        JOIN parts     p ON p.id = po.part_id
    '''
    if branch_id:
        query += ' WHERE po.branch_id = ?'
        cur.execute(query + ' ORDER BY po.created_at DESC', (branch_id,))
    else:
        cur.execute(query + ' ORDER BY po.created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return rows

def add_order(customer_id, part_id, quantity, total_price, notes='', branch_id=None):
    from datetime import date
    return addrecord('parts_orders',
        customer_id=customer_id, part_id=part_id,
        quantity=quantity, total_price=total_price,
        notes=notes, status='Pending', branch_id=branch_id,
        order_date=str(date.today())
    )

def update_order_status(order_id, status): return updaterecord('parts_orders', 'id', order_id, status=status)
def delete_order(order_id):                return deleterecord('parts_orders', id=order_id)

def get_orders_by_customer(customer_id):
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT po.id, p.name AS part_name, po.quantity,
               po.total_price, po.order_date, po.status
        FROM parts_orders po JOIN parts p ON p.id = po.part_id
        WHERE po.customer_id = ? ORDER BY po.created_at DESC
    ''', (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  INSTALLMENTS
# ─────────────────────────────────────────────

def get_all_installments(branch_id=None):
    conn = connect()
    cur  = conn.cursor()
    query = '''
        SELECT i.id, c.firstname || ' ' || c.lastname AS customer,
               c.email AS customer_email,
               m.brand || ' ' || m.model AS motor,
               m.plate, i.total_price, i.down_payment,
               i.balance_amount, i.monthly_payment,
               i.term_months, i.paid_months, i.next_due_date,
               i.status, i.created_at, i.sale_id
        FROM installments i
        JOIN customers c ON c.id = i.customer_id
        JOIN motors    m ON m.id = i.motor_id
    '''
    if branch_id:
        query += ' WHERE i.branch_id = ?'
        cur.execute(query + ' ORDER BY i.created_at DESC', (branch_id,))
    else:
        cur.execute(query + ' ORDER BY i.created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_installment_by_id(inst_id): return getone('installments', id=inst_id)

def create_installment(sale_id, customer_id, motor_id, total_price,
                        down_payment, term_months, branch_id=None):
    from datetime import date, timedelta
    balance  = total_price - down_payment
    monthly  = round(balance / term_months, 2) if term_months > 0 else balance
    next_due = str(date.today().replace(day=1) + timedelta(days=32)).replace(str(date.today().year)+'.',  '')[0:10]
    # simpler: next month same day
    today = date.today()
    if today.month == 12:
        next_due = date(today.year+1, 1, today.day).isoformat()
    else:
        next_due = date(today.year, today.month+1, today.day).isoformat()

    return addrecord('installments',
        sale_id=sale_id, customer_id=customer_id, motor_id=motor_id,
        total_price=total_price, down_payment=down_payment,
        balance_amount=balance, monthly_payment=monthly,
        term_months=term_months, paid_months=0,
        next_due_date=next_due, status='Active', branch_id=branch_id
    )

def record_installment_payment(inst_id, amount, pay_date, notes=''):
    from datetime import date
    inst = get_installment_by_id(inst_id)
    if not inst: return False

    # Add payment record
    addrecord('installment_payments',
        installment_id=inst_id, amount=amount,
        pay_date=pay_date, notes=notes
    )

    new_paid    = (inst['paid_months'] or 0) + 1
    new_balance = max(0, (inst['balance_amount'] or 0) - amount)

    # Calculate next due date
    today = date.today()
    if today.month == 12:
        next_due = date(today.year+1, 1, today.day).isoformat()
    else:
        next_due = date(today.year, today.month+1, today.day).isoformat()

    new_status = 'Paid Off' if new_paid >= inst['term_months'] or new_balance <= 0 else 'Active'

    return updaterecord('installments', 'id', inst_id,
        paid_months=new_paid,
        balance_amount=new_balance,
        next_due_date=next_due if new_status != 'Paid Off' else None,
        status=new_status
    )

def get_installment_payments(inst_id):
    conn = connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM installment_payments WHERE installment_id = ? ORDER BY pay_date DESC", (inst_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_installments_by_customer(customer_id):
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT i.id, m.brand || ' ' || m.model AS motor,
               m.plate, i.total_price, i.down_payment,
               i.balance_amount, i.monthly_payment,
               i.term_months, i.paid_months, i.next_due_date, i.status
        FROM installments i JOIN motors m ON m.id = i.motor_id
        WHERE i.customer_id = ? ORDER BY i.created_at DESC
    ''', (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  BRANCHES
# ─────────────────────────────────────────────

def get_all_branches():
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT b.*,
               (SELECT COUNT(*) FROM motors  m WHERE m.branch_id = b.id) AS motor_count,
               (SELECT COUNT(*) FROM admin   a WHERE a.branch_id = b.id) AS admin_count,
               (SELECT COUNT(*) FROM rentals r WHERE r.branch_id = b.id AND r.status = 'Rented') AS active_rentals,
               (SELECT COUNT(*) FROM sales   s WHERE s.branch_id = b.id) AS sale_count,
               (SELECT COALESCE(SUM(s.total_price),0) FROM sales s WHERE s.branch_id = b.id AND s.status = 'Confirmed') AS revenue
        FROM branches b ORDER BY b.created_at
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_branch_by_id(bid):      return getone('branches', id=bid)
def add_branch(**kwargs):       return addrecord('branches', **kwargs)
def update_branch(bid, **kw):   return updaterecord('branches', 'id', bid, **kw)
def delete_branch(bid):         return deleterecord('branches', id=bid)


# ─────────────────────────────────────────────
#  DASHBOARD STATS
# ─────────────────────────────────────────────

def get_dashboard_stats(branch_id=None):
    conn = connect()
    cur  = conn.cursor()

    branch_filter = "AND branch_id = ?" if branch_id else ""
    params = (branch_id,) if branch_id else ()

    def q(sql, p=()):
        cur.execute(sql, p)
        return cur.fetchone()[0]

    available = q(f"SELECT COUNT(*) FROM motors WHERE status='Available' {branch_filter}", params)
    rented    = q(f"SELECT COUNT(*) FROM motors WHERE status='Rented' {branch_filter}", params)
    overdue   = q(f"SELECT COUNT(*) FROM rentals WHERE status='Overdue' {branch_filter}", params)
    pending   = q(f"SELECT COUNT(*) FROM rentals WHERE status='Pending' {branch_filter}", params)
    revenue   = q(f"SELECT COALESCE(SUM(total_cost),0) FROM rentals WHERE status='Returned' {branch_filter}", params)
    total_cust= q("SELECT COUNT(*) FROM customers")

    # New stats
    sales_count   = q(f"SELECT COUNT(*) FROM sales WHERE status='Confirmed' {branch_filter}", params)
    sales_revenue = q(f"SELECT COALESCE(SUM(total_price),0) FROM sales WHERE status='Confirmed' {branch_filter}", params)
    active_inst   = q(f"SELECT COUNT(*) FROM installments WHERE status='Active' {branch_filter}", params)
    pending_orders= q(f"SELECT COUNT(*) FROM parts_orders WHERE status='Pending' {branch_filter}", params)

    conn.close()
    return {
        'available':       available,
        'rented':          rented,
        'overdue':         overdue,
        'pending':         pending,
        'revenue':         revenue,
        'total_customers': total_cust,
        'sales_count':     sales_count,
        'sales_revenue':   sales_revenue,
        'active_installments': active_inst,
        'pending_orders':  pending_orders,
    }