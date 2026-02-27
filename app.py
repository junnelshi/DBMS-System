from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from dbhelper import (
    init_database,
    get_customer_by_email, get_customer_by_id, get_all_customers, delete_customer,
    get_admin_by_email,
    get_all_motors, get_motor_by_id, add_motor, update_motor, delete_motor, get_motors_by_status,
    get_all_rentals, get_rentals_by_customer, get_rental_by_id,
    add_rental, update_rental_status, delete_rental,
    get_dashboard_stats,
    addrecord, updaterecord, deleterecord, recordexists, recordexists_exclude
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "motorent-secret-change-this")
init_database()

def is_logged_in(): return 'user_id' in session
def is_admin(): return session.get('role') == 'admin'

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        if not is_admin():
            return redirect(url_for('portal'))
        return f(*args, **kwargs)
    return decorated

def calc_days(start_date, end_date):
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date,   "%Y-%m-%d")
        return max(1, (d2 - d1).days)
    except:
        return 1

@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('dashboard') if is_admin() else url_for('portal'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('dashboard') if is_admin() else url_for('portal'))
    if request.method == 'POST':
        email    = request.form.get('idno', '').strip()
        password = request.form.get('password', '').strip()
        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('login'))
        admin = get_admin_by_email(email)
        if admin and check_password_hash(admin['password'], password):
            session['user_id']    = admin['id']
            session['user_name']  = admin['name']
            session['user_email'] = admin['email']
            session['role']       = 'admin'
            return redirect(url_for('dashboard'))
        customer = get_customer_by_email(email)
        if customer and check_password_hash(customer['password'], password):
            session['user_id']   = customer['id']
            session['user_name'] = f"{customer['firstname']} {customer['lastname']}"
            session['role']      = 'customer'
            return redirect(url_for('portal'))
        flash('Invalid email or password.', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    if is_logged_in():
        return redirect(url_for('index'))
    firstname  = request.form.get('firstname',  '').strip()
    lastname   = request.form.get('lastname',   '').strip()
    email      = request.form.get('email',      '').strip()
    phone      = request.form.get('phone',      '').strip()
    birthdate  = request.form.get('birthdate',  '').strip()
    address    = request.form.get('address',    '').strip()
    license_no = request.form.get('license_no', '').strip()
    password   = request.form.get('password',   '').strip()
    confirm    = request.form.get('confirm_password', '').strip()
    if not all([firstname, lastname, email, phone, birthdate, address, license_no, password, confirm]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('login'))
    if password != confirm:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('login'))
    if recordexists('customers', email=email):
        flash('An account with this email already exists.', 'error')
        return redirect(url_for('login'))
    if recordexists('customers', license_no=license_no):
        flash("This driver's license number is already registered.", 'error')
        return redirect(url_for('login'))
    if addrecord('customers', firstname=firstname, lastname=lastname,
                 email=email, phone=phone, birthdate=birthdate,
                 address=address, license_no=license_no,
                 password=generate_password_hash(password)):
        flash('Account created! You can now sign in.', 'success')
    else:
        flash('Registration failed. Please try again.', 'error')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ── CUSTOMER PORTAL ──
@app.route('/portal')
@login_required
def portal():
    if is_admin():
        return redirect(url_for('dashboard'))
    customer         = get_customer_by_id(session['user_id'])
    available_motors = get_motors_by_status('Available')
    rentals          = get_rentals_by_customer(session['user_id'])
    return render_template('customer_portal.html',
        customer=customer,
        available_motors=available_motors,
        rentals=rentals,
    )

# ── ADMIN DASHBOARD ──
@app.route('/dashboard')
@admin_required
def dashboard():
    stats   = get_dashboard_stats()
    rentals = get_all_rentals()
    motors  = get_all_motors()
    return render_template('dashboard.html',
        stats=stats, motors=motors, rentals=rentals,
        role='admin', user_name=session.get('user_name'),
    )

# ── MOTORS (admin) ──
@app.route('/motors')
@admin_required
def motors():
    status_filter = request.args.get('status', '')
    type_filter   = request.args.get('type', '')
    search        = request.args.get('search', '')
    all_motors    = get_all_motors()
    if status_filter: all_motors = [m for m in all_motors if m['status'] == status_filter]
    if type_filter:   all_motors = [m for m in all_motors if m['type'] == type_filter]
    if search:
        s = search.lower()
        all_motors = [m for m in all_motors if s in m['brand'].lower() or s in m['model'].lower() or s in m['plate'].lower()]
    return render_template('motors.html',
        motors=all_motors, available_motors=get_motors_by_status('Available'),
        customers=get_all_customers(), role='admin', user_name=session.get('user_name'),
        status_filter=status_filter, type_filter=type_filter, search=search,
    )

@app.route('/motors/add', methods=['POST'])
@admin_required
def motor_add():
    brand=request.form.get('brand','').strip(); model=request.form.get('model','').strip()
    year=request.form.get('year','').strip();   type_=request.form.get('type','').strip()
    plate=request.form.get('plate','').strip(); rate_per_day=request.form.get('rate_per_day','').strip()
    status=request.form.get('status','Available').strip(); notes=request.form.get('notes','').strip()
    if not all([brand, model, year, type_, plate, rate_per_day]):
        flash('Please fill in all required motor fields.', 'error')
        return redirect(url_for('motors'))
    if recordexists('motors', plate=plate):
        flash(f'A motor with plate "{plate}" already exists.', 'error')
        return redirect(url_for('motors'))
    if add_motor(brand, model, int(year), type_, plate, float(rate_per_day), status, notes):
        flash(f'{brand} {model} added successfully!', 'success')
    else:
        flash('Failed to add motor.', 'error')
    return redirect(url_for('motors'))

@app.route('/motors/edit/<int:motor_id>', methods=['POST'])
@admin_required
def motor_edit(motor_id):
    brand=request.form.get('brand','').strip(); model=request.form.get('model','').strip()
    year=request.form.get('year','').strip();   type_=request.form.get('type','').strip()
    plate=request.form.get('plate','').strip(); rate_per_day=request.form.get('rate_per_day','').strip()
    status=request.form.get('status','Available').strip(); notes=request.form.get('notes','').strip()
    if not all([brand, model, year, type_, plate, rate_per_day]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('motors'))
    if recordexists_exclude('motors', 'plate', plate, 'id', motor_id):
        flash(f'Plate "{plate}" is already used by another motor.', 'error')
        return redirect(url_for('motors'))
    if update_motor(motor_id, brand=brand, model=model, year=int(year), type=type_, plate=plate, rate_per_day=float(rate_per_day), status=status, notes=notes):
        flash('Motor updated successfully!', 'success')
    else:
        flash('Failed to update motor.', 'error')
    return redirect(url_for('motors'))

@app.route('/motors/delete/<int:motor_id>', methods=['POST'])
@admin_required
def motor_delete(motor_id):
    delete_motor(motor_id)
    flash('Motor deleted.', 'success')
    return redirect(url_for('motors'))

# ── RENTALS ──
@app.route('/rentals')
@admin_required
def rentals():
    status_filter = request.args.get('status', '')
    all_rentals   = get_all_rentals()
    if status_filter: all_rentals = [r for r in all_rentals if r['status'] == status_filter]
    return render_template('rentals.html',
        rentals=all_rentals, available_motors=get_motors_by_status('Available'),
        customers=get_all_customers(), role='admin', user_name=session.get('user_name'),
        status_filter=status_filter,
    )

@app.route('/rentals/add', methods=['POST'])
@login_required
def rental_add():
    motor_id=request.form.get('motor_id','').strip()
    start_date=request.form.get('start_date','').strip()
    end_date=request.form.get('end_date','').strip()
    notes=request.form.get('notes','').strip()
    redirect_to = url_for('rentals') if is_admin() else url_for('portal')
    if is_admin():
        customer_id = request.form.get('customer_id', '').strip()
        if not customer_id:
            flash('Please select a customer.', 'error')
            return redirect(redirect_to)
    else:
        customer_id = session['user_id']
    if not all([motor_id, start_date, end_date]):
        flash('Please fill in all required fields.', 'error')
        return redirect(redirect_to)
    motor = get_motor_by_id(int(motor_id))
    if not motor or motor['status'] != 'Available':
        flash('This motor is not available for rental.', 'error')
        return redirect(redirect_to)
    days = calc_days(start_date, end_date)
    total_cost = days * motor['rate_per_day']
    if add_rental(int(customer_id), int(motor_id), start_date, end_date, total_cost, notes):
        update_motor(int(motor_id), status='Rented')
        flash(f'Booking submitted! ₱{total_cost:,.2f} for {days} day(s). Awaiting admin approval.', 'success')
    else:
        flash('Failed to create booking.', 'error')
    return redirect(redirect_to)

@app.route('/rentals/approve/<int:rental_id>', methods=['POST'])
@admin_required
def rental_approve(rental_id):
    update_rental_status(rental_id, 'Rented')
    flash('Rental approved!', 'success')
    return redirect(url_for('rentals'))

@app.route('/rentals/return/<int:rental_id>', methods=['POST'])
@admin_required
def rental_return(rental_id):
    rental = get_rental_by_id(rental_id)
    if rental:
        update_rental_status(rental_id, 'Returned')
        update_motor(rental['motor_id'], status='Available')
        flash('Rental marked as returned.', 'success')
    return redirect(url_for('rentals'))

@app.route('/rentals/delete/<int:rental_id>', methods=['POST'])
@admin_required
def rental_delete(rental_id):
    rental = get_rental_by_id(rental_id)
    if rental:
        if rental['status'] in ('Rented', 'Pending'):
            update_motor(rental['motor_id'], status='Available')
        delete_rental(rental_id)
        flash('Rental deleted.', 'success')
    return redirect(url_for('rentals'))

# ── CUSTOMERS ──
@app.route('/customers')
@admin_required
def customers():
    search = request.args.get('search', '')
    all_customers = get_all_customers()
    if search:
        s = search.lower()
        all_customers = [c for c in all_customers if s in c['firstname'].lower() or s in c['lastname'].lower() or s in c['email'].lower() or s in c['license_no'].lower()]
    return render_template('customers.html', customers=all_customers, role='admin', user_name=session.get('user_name'), search=search)

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@admin_required
def customer_delete(customer_id):
    delete_customer(customer_id)
    flash('Customer removed.', 'success')
    return redirect(url_for('customers'))

# ── PROFILE ──
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if not is_admin():
        return redirect(url_for('portal'))
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '').strip()
        new_pw     = request.form.get('new_password', '').strip()
        confirm_pw = request.form.get('confirm_password', '').strip()
        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('profile'))
        record = get_admin_by_email(session.get('user_email', ''))
        if record and check_password_hash(record['password'], current_pw):
            updaterecord('admin', 'id', session['user_id'], password=generate_password_hash(new_pw))
            flash('Password updated!', 'success')
        else:
            flash('Current password is incorrect.', 'error')
        return redirect(url_for('profile'))
    return render_template('profile.html', customer=None, role='admin', user_name=session.get('user_name'))

if __name__ == '__main__':
    app.run(debug=True)