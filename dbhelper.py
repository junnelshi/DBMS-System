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

    # ── Customers table ──
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

    # ── Admin table (renamed from users) ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(100) UNIQUE NOT NULL,
            password   VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Motors / Vehicles table ──
    cur.execute('''
        CREATE TABLE IF NOT EXISTS motors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            brand        VARCHAR(50)  NOT NULL,
            model        VARCHAR(50)  NOT NULL,
            year         INTEGER      NOT NULL,
            type         VARCHAR(30)  NOT NULL,
            plate        VARCHAR(20)  UNIQUE NOT NULL,
            rate_per_day REAL         NOT NULL,
            status       VARCHAR(30)  DEFAULT 'Available',
            notes        TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── Rentals table ──
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
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (motor_id)    REFERENCES motors(id)
        )
    ''')

    # ── Migrate old 'users' table to 'admin' if it exists ──
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        cur.execute("INSERT OR IGNORE INTO admin (id, name, email, password, created_at) SELECT id, name, email, password, created_at FROM users")
        cur.execute("DROP TABLE users")
        print("[MIGRATE] Migrated 'users' table to 'admin'.")

    # ── Drop leftover students table if it exists ──
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students'")
    if cur.fetchone():
        cur.execute("DROP TABLE students")
        print("[CLEANUP] Dropped 'students' table.")

    # ── Default admin (inserted once) ──
    cur.execute("SELECT COUNT(*) FROM admin WHERE email = ?", ("admin@motorent.com",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO admin (name, email, password) VALUES (?, ?, ?)",
            ("Administrator", "admin@motorent.com", generate_password_hash("admin123"))
        )
        print("[INIT] Admin created → email: admin@motorent.com | password: admin123")

    # ── Sample motors (inserted once) ──
    cur.execute("SELECT COUNT(*) FROM motors")
    if cur.fetchone()[0] == 0:
        sample_motors = [
            ("Honda",    "Click 125i",  2023, "Scooter",   "ABC 1234", 500,  "Available",         "Brand new unit"),
            ("Yamaha",   "NMAX 155",    2022, "Scooter",   "XYZ 5678", 700,  "Available",         ""),
            ("Suzuki",   "Raider R150", 2021, "Sport",     "DEF 9012", 600,  "Available",         "Slight scratch on left fairing"),
            ("Honda",    "ADV 160",     2023, "Scooter",   "GHI 3456", 900,  "Available",         ""),
            ("Kawasaki", "Barako II",   2020, "Underbone", "JKL 7890", 400,  "Under Maintenance", "Engine check"),
            ("Yamaha",   "Mio i125",    2022, "Scooter",   "MNO 1234", 450,  "Available",         ""),
        ]
        cur.executemany(
            "INSERT INTO motors (brand, model, year, type, plate, rate_per_day, status, notes) VALUES (?,?,?,?,?,?,?,?)",
            sample_motors
        )
        print("[INIT] Sample motors inserted.")

    conn.commit()
    conn.close()


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
        return True
    except Exception as e:
        print("addrecord error:", e)
        conn.rollback()
        return False
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

def get_customer_by_email(email):
    return getone('customers', email=email)

def get_customer_by_id(customer_id):
    return getone('customers', id=customer_id)

def get_all_customers():
    return getall('customers')

def delete_customer(customer_id):
    return deleterecord('customers', id=customer_id)


# ─────────────────────────────────────────────
#  ADMIN FUNCTIONS (renamed from users)
# ─────────────────────────────────────────────

def get_admin_by_email(email):
    return getone('admin', email=email)

def get_all_admins():
    return getall('admin')

def delete_admin(admin_id):
    return deleterecord('admin', id=admin_id)


# ─────────────────────────────────────────────
#  MOTOR FUNCTIONS
# ─────────────────────────────────────────────

def get_all_motors():
    return getall('motors')

def get_motor_by_id(motor_id):
    return getone('motors', id=motor_id)

def add_motor(brand, model, year, type_, plate, rate_per_day, status='Available', notes=''):
    return addrecord('motors',
        brand=brand, model=model, year=year, type=type_,
        plate=plate, rate_per_day=rate_per_day, status=status, notes=notes
    )

def update_motor(motor_id, **kwargs):
    return updaterecord('motors', 'id', motor_id, **kwargs)

def delete_motor(motor_id):
    return deleterecord('motors', id=motor_id)

def get_motors_by_status(status):
    conn = connect()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM motors WHERE status = ?", (status,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  RENTAL FUNCTIONS
# ─────────────────────────────────────────────

def get_all_rentals():
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT
            r.id,
            c.firstname || ' ' || c.lastname AS customer,
            c.phone,
            m.brand || ' ' || m.model        AS motor,
            m.plate,
            r.start_date,
            r.end_date,
            r.total_cost,
            r.status,
            r.notes,
            r.created_at,
            r.customer_id,
            r.motor_id
        FROM rentals r
        JOIN customers c ON c.id = r.customer_id
        JOIN motors    m ON m.id = r.motor_id
        ORDER BY r.created_at DESC
    ''')
    rows = cur.fetchall()
    conn.close()
    return rows

def get_rentals_by_customer(customer_id):
    conn = connect()
    cur  = conn.cursor()
    cur.execute('''
        SELECT
            r.id,
            m.brand || ' ' || m.model AS motor,
            m.plate,
            r.start_date,
            r.end_date,
            r.total_cost,
            r.status,
            r.notes,
            r.created_at
        FROM rentals r
        JOIN motors m ON m.id = r.motor_id
        WHERE r.customer_id = ?
        ORDER BY r.created_at DESC
    ''', (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_rental_by_id(rental_id):
    return getone('rentals', id=rental_id)

def add_rental(customer_id, motor_id, start_date, end_date, total_cost, notes=''):
    return addrecord('rentals',
        customer_id=customer_id, motor_id=motor_id,
        start_date=start_date, end_date=end_date,
        total_cost=total_cost, status='Pending', notes=notes
    )

def update_rental_status(rental_id, status):
    return updaterecord('rentals', 'id', rental_id, status=status)

def delete_rental(rental_id):
    return deleterecord('rentals', id=rental_id)


# ─────────────────────────────────────────────
#  DASHBOARD STATS
# ─────────────────────────────────────────────

def get_dashboard_stats():
    conn = connect()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM motors WHERE status = 'Available'")
    available = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM motors WHERE status = 'Rented'")
    rented = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM rentals WHERE status = 'Overdue'")
    overdue = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM rentals WHERE status = 'Pending'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(total_cost), 0) FROM rentals WHERE status = 'Returned'")
    revenue = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM customers")
    total_customers = cur.fetchone()[0]

    conn.close()
    return {
        'available':       available,
        'rented':          rented,
        'overdue':         overdue,
        'pending':         pending,
        'revenue':         revenue,
        'total_customers': total_customers,
    }