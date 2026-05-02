from flask import Flask, render_template, redirect, url_for, request, session, flash, jsonify
from dbhelper import (
    init_database,
    get_customer_by_email, get_customer_by_id, get_all_customers, delete_customer,
    get_admin_by_email,
    get_all_motors, get_motor_by_id, add_motor, update_motor, delete_motor,
    get_motors_by_status, get_motors_for_sale,
    get_all_rentals, get_rentals_by_customer, get_rental_by_id,
    add_rental, update_rental_status, delete_rental,
    get_all_sales, add_sale, confirm_sale, delete_sale, get_sale_by_id,
    get_sales_by_customer,
    get_all_parts, get_part_by_id, add_part, update_part, delete_part,
    get_all_orders, add_order, update_order_status, delete_order,
    get_orders_by_customer,
    get_all_installments, get_installment_by_id, create_installment,
    record_installment_payment, get_installment_payments,
    get_installments_by_customer,
    get_all_branches, get_branch_by_id, add_branch, update_branch, delete_branch,
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
def is_admin(): return session.get('role') in ('admin', 'superadmin')
def is_superadmin(): return session.get('role') == 'superadmin'

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

def superadmin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        if not is_superadmin():
            flash('Super Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def calc_days(start_date, end_date):
    try:
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date,   "%Y-%m-%d")
        return max(1, (d2 - d1).days)
    except:
        return 1

def get_branch_id():
    if is_superadmin():
        return None
    return session.get('branch_id')


# ═══════════════════════════════════════════════════════════
#  LANDING PAGE  (new)
# ═══════════════════════════════════════════════════════════

@app.route('/')
def index():
    # If already logged in, skip landing page and go straight to their area
    if is_logged_in():
        return redirect(url_for('dashboard') if is_admin() else url_for('portal'))
    # Get all motorcycles for landing page carousel
    featured_motors = get_all_motors() if get_all_motors() else []
    return render_template('landing.html', featured_motors=featured_motors)


# ═══════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════

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
            session['role']       = admin['role'] if admin['role'] else 'admin'
            session['branch_id']  = admin['branch_id']
            if admin['branch_id']:
                branch = get_branch_by_id(admin['branch_id'])
                session['branch_name'] = branch['name'] if branch else None
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
    result = addrecord('customers', firstname=firstname, lastname=lastname,
                 email=email, phone=phone, birthdate=birthdate,
                 address=address, license_no=license_no,
                 password=generate_password_hash(password))
    if result:
        flash('Account created! You can now sign in.', 'success')
    else:
        flash('Registration failed. Please try again.', 'error')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))   # goes to landing page now


# ═══════════════════════════════════════════════════════════
#  CUSTOMER PORTAL
# ═══════════════════════════════════════════════════════════

@app.route('/portal')
@login_required
def portal():
    if is_admin():
        return redirect(url_for('dashboard'))
    customer         = get_customer_by_id(session['user_id'])
    available_motors = get_motors_by_status('Available')
    sale_motors      = get_motors_for_sale()
    rentals          = get_rentals_by_customer(session['user_id'])
    my_orders        = get_orders_by_customer(session['user_id'])
    my_installments  = get_installments_by_customer(session['user_id'])
    parts            = get_all_parts()
    return render_template('customer_portal.html',
        customer=customer,
        available_motors=available_motors,
        sale_motors=sale_motors,
        rentals=rentals,
        my_orders=my_orders,
        my_installments=my_installments,
        parts=parts,
    )

@app.route('/portal/buy', methods=['POST'])
@login_required
def portal_buy():
    if is_admin():
        return redirect(url_for('dashboard'))
    motor_id      = request.form.get('motor_id', '').strip()
    payment_type  = request.form.get('payment_type', 'Cash').strip()
    down_payment  = float(request.form.get('down_payment', 0) or 0)
    inst_months   = int(request.form.get('installment_months', 0) or 0)
    notes         = request.form.get('notes', '').strip()
    if not motor_id:
        flash('Motor not found.', 'error')
        return redirect(url_for('portal'))
    motor = get_motor_by_id(int(motor_id))
    if not motor or not motor['selling_price']:
        flash('This motor is not available for purchase.', 'error')
        return redirect(url_for('portal'))
    from datetime import date
    sale_id = add_sale(
        customer_id=session['user_id'],
        motor_id=int(motor_id),
        total_price=motor['selling_price'],
        payment_type=payment_type,
        sale_date=str(date.today()),
        down_payment=down_payment,
        installment_months=inst_months,
        notes=notes
    )
    if sale_id:
        flash(f'Purchase request submitted! We will contact you to confirm. ₱{motor["selling_price"]:,.2f}', 'success')
    else:
        flash('Failed to submit purchase request.', 'error')
    return redirect(url_for('portal') + '?tab=myorders')

@app.route('/portal/order-part', methods=['POST'])
@login_required
def portal_order_part():
    if is_admin():
        return redirect(url_for('dashboard'))
    part_id  = request.form.get('part_id', '').strip()
    quantity = int(request.form.get('quantity', 1) or 1)
    notes    = request.form.get('notes', '').strip()
    if not part_id:
        flash('Part not found.', 'error')
        return redirect(url_for('portal'))
    part = get_part_by_id(int(part_id))
    if not part:
        flash('Part not found.', 'error')
        return redirect(url_for('portal'))
    if part['stock'] < quantity:
        flash(f'Only {part["stock"]} unit(s) in stock.', 'error')
        return redirect(url_for('portal'))
    total = part['price'] * quantity
    result = add_order(
        customer_id=session['user_id'],
        part_id=int(part_id),
        quantity=quantity,
        total_price=total,
        notes=notes
    )
    if result:
        update_part(int(part_id), stock=part['stock'] - quantity)
        flash(f'Order placed! {quantity}x {part["name"]} — ₱{total:,.2f}', 'success')
    else:
        flash('Failed to place order.', 'error')
    return redirect(url_for('portal') + '?tab=myorders')


# ═══════════════════════════════════════════════════════════
#  ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════

@app.route('/dashboard')
@admin_required
def dashboard():
    branch_id = get_branch_id()
    stats     = get_dashboard_stats(branch_id)
    rentals   = get_all_rentals(branch_id)
    motors    = get_all_motors(branch_id)
    return render_template('dashboard.html',
        stats=stats, motors=motors, rentals=rentals,
        role=session.get('role'), user_name=session.get('user_name'),
    )


# ═══════════════════════════════════════════════════════════
#  MOTORS
# ═══════════════════════════════════════════════════════════

@app.route('/motors')
@admin_required
def motors():
    branch_id     = get_branch_id()
    status_filter = request.args.get('status', '')
    type_filter   = request.args.get('type', '')
    search        = request.args.get('search', '')
    all_motors    = get_all_motors(branch_id)
    if status_filter: all_motors = [m for m in all_motors if m['status'] == status_filter]
    if type_filter:   all_motors = [m for m in all_motors if m['type'] == type_filter]
    if search:
        s = search.lower()
        all_motors = [m for m in all_motors if s in m['brand'].lower() or s in m['model'].lower() or s in m['plate'].lower()]
    return render_template('motors.html',
        motors=all_motors, available_motors=get_motors_by_status('Available', branch_id),
        customers=get_all_customers(), role=session.get('role'),
        status_filter=status_filter, type_filter=type_filter, search=search,
    )

@app.route('/motors/add', methods=['POST'])
@admin_required
def motor_add():
    brand         = request.form.get('brand','').strip()
    model         = request.form.get('model','').strip()
    year          = request.form.get('year','').strip()
    type_         = request.form.get('type','').strip()
    plate         = request.form.get('plate','').strip()
    rate_per_day  = request.form.get('rate_per_day','').strip()
    status        = request.form.get('status','Available').strip()
    notes         = request.form.get('notes','').strip()
    selling_price = request.form.get('selling_price','').strip()
    for_sale      = 1 if request.form.get('for_sale') else 0
    if not all([brand, model, year, type_, plate, rate_per_day]):
        flash('Please fill in all required motor fields.', 'error')
        return redirect(url_for('motors'))
    if recordexists('motors', plate=plate):
        flash(f'A motor with plate "{plate}" already exists.', 'error')
        return redirect(url_for('motors'))
    if add_motor(brand, model, int(year), type_, plate, float(rate_per_day), status, notes,
                 selling_price=float(selling_price) if selling_price else None,
                 for_sale=for_sale, branch_id=get_branch_id()):
        flash(f'{brand} {model} added successfully!', 'success')
    else:
        flash('Failed to add motor.', 'error')
    return redirect(url_for('motors'))

@app.route('/motors/edit/<int:motor_id>', methods=['POST'])
@admin_required
def motor_edit(motor_id):
    brand         = request.form.get('brand','').strip()
    model         = request.form.get('model','').strip()
    year          = request.form.get('year','').strip()
    type_         = request.form.get('type','').strip()
    plate         = request.form.get('plate','').strip()
    rate_per_day  = request.form.get('rate_per_day','').strip()
    status        = request.form.get('status','Available').strip()
    notes         = request.form.get('notes','').strip()
    selling_price = request.form.get('selling_price','').strip()
    for_sale      = 1 if request.form.get('for_sale') else 0
    if not all([brand, model, year, type_, plate, rate_per_day]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('motors'))
    if recordexists_exclude('motors', 'plate', plate, 'id', motor_id):
        flash(f'Plate "{plate}" is already used by another motor.', 'error')
        return redirect(url_for('motors'))
    if update_motor(motor_id, brand=brand, model=model, year=int(year), type=type_,
                    plate=plate, rate_per_day=float(rate_per_day), status=status, notes=notes,
                    selling_price=float(selling_price) if selling_price else None,
                    for_sale=for_sale):
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


# ═══════════════════════════════════════════════════════════
#  RENTALS
# ═══════════════════════════════════════════════════════════

@app.route('/rentals')
@admin_required
def rentals():
    branch_id     = get_branch_id()
    status_filter = request.args.get('status', '')
    all_rentals   = get_all_rentals(branch_id)
    if status_filter: all_rentals = [r for r in all_rentals if r['status'] == status_filter]
    return render_template('rentals.html',
        rentals=all_rentals, available_motors=get_motors_by_status('Available', branch_id),
        customers=get_all_customers(), role=session.get('role'),
        status_filter=status_filter,
    )

@app.route('/rentals/add', methods=['POST'])
@login_required
def rental_add():
    motor_id   = request.form.get('motor_id','').strip()
    start_date = request.form.get('start_date','').strip()
    end_date   = request.form.get('end_date','').strip()
    notes      = request.form.get('notes','').strip()
    redirect_to = url_for('rentals') if is_admin() else url_for('portal')
    customer_id = request.form.get('customer_id', '').strip() if is_admin() else str(session['user_id'])
    if not all([motor_id, start_date, end_date, customer_id]):
        flash('Please fill in all required fields.', 'error')
        return redirect(redirect_to)
    motor = get_motor_by_id(int(motor_id))
    if not motor or motor['status'] != 'Available':
        flash('This motor is not available for rental.', 'error')
        return redirect(redirect_to)
    days = calc_days(start_date, end_date)
    total_cost = days * motor['rate_per_day']
    if add_rental(int(customer_id), int(motor_id), start_date, end_date, total_cost, notes, get_branch_id()):
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


# ═══════════════════════════════════════════════════════════
#  SALES
# ═══════════════════════════════════════════════════════════

@app.route('/sales')
@admin_required
def sales():
    branch_id = get_branch_id()
    all_sales = get_all_sales(branch_id)
    return render_template('sales.html',
        sales=all_sales,
        available_motors=get_motors_for_sale(branch_id),
        customers=get_all_customers(),
    )

@app.route('/sales/add', methods=['POST'])
@admin_required
def sale_add():
    customer_id   = request.form.get('customer_id','').strip()
    motor_id      = request.form.get('motor_id','').strip()
    total_price   = request.form.get('total_price','').strip()
    payment_type  = request.form.get('payment_type','Cash').strip()
    sale_date     = request.form.get('sale_date','').strip()
    down_payment  = float(request.form.get('down_payment', 0) or 0)
    inst_months   = int(request.form.get('installment_months', 0) or 0)
    notes         = request.form.get('notes','').strip()
    if not all([customer_id, motor_id, total_price, sale_date]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('sales'))
    sale_id = add_sale(
        int(customer_id), int(motor_id), float(total_price),
        payment_type, sale_date, down_payment, inst_months, notes, get_branch_id()
    )
    if sale_id:
        flash('Sale recorded successfully! Confirm it to mark motor as Sold.', 'success')
    else:
        flash('Failed to record sale.', 'error')
    return redirect(url_for('sales'))

@app.route('/sales/confirm/<int:sale_id>', methods=['POST'])
@admin_required
def sale_confirm(sale_id):
    sale = get_sale_by_id(sale_id)
    if sale:
        confirm_sale(sale_id)
        update_motor(sale['motor_id'], status='Sold')
        if sale['payment_type'] == 'Installment' and sale['installment_months'] > 0:
            create_installment(
                sale_id=sale_id,
                customer_id=sale['customer_id'],
                motor_id=sale['motor_id'],
                total_price=sale['total_price'],
                down_payment=sale['down_payment'],
                term_months=sale['installment_months'],
                branch_id=get_branch_id()
            )
            flash('Sale confirmed! Installment plan created.', 'success')
        else:
            flash('Sale confirmed! Motor marked as Sold.', 'success')
    return redirect(url_for('sales'))

@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
@admin_required
def sale_delete(sale_id):
    delete_sale(sale_id)
    flash('Sale deleted.', 'success')
    return redirect(url_for('sales'))


# ═══════════════════════════════════════════════════════════
#  PARTS
# ═══════════════════════════════════════════════════════════

@app.route('/parts')
@admin_required
def parts():
    branch_id = get_branch_id()
    all_parts  = get_all_parts(branch_id)
    all_orders = get_all_orders(branch_id)
    return render_template('parts.html', parts=all_parts, orders=all_orders)

@app.route('/parts/add', methods=['POST'])
@admin_required
def part_add():
    name        = request.form.get('name','').strip()
    brand       = request.form.get('brand','').strip()
    category    = request.form.get('category','Other').strip()
    price       = request.form.get('price','').strip()
    stock       = request.form.get('stock','0').strip()
    compatible  = request.form.get('compatible_with','').strip()
    description = request.form.get('description','').strip()
    if not all([name, price]):
        flash('Name and price are required.', 'error')
        return redirect(url_for('parts'))
    if add_part(name, brand, category, float(price), int(stock), compatible, description, get_branch_id()):
        flash(f'{name} added to inventory!', 'success')
    else:
        flash('Failed to add part.', 'error')
    return redirect(url_for('parts'))

@app.route('/parts/edit/<int:part_id>', methods=['POST'])
@admin_required
def part_edit(part_id):
    name        = request.form.get('name','').strip()
    brand       = request.form.get('brand','').strip()
    category    = request.form.get('category','Other').strip()
    price       = request.form.get('price','').strip()
    stock       = request.form.get('stock','0').strip()
    compatible  = request.form.get('compatible_with','').strip()
    description = request.form.get('description','').strip()
    if update_part(part_id, name=name, brand=brand, category=category,
                   price=float(price), stock=int(stock),
                   compatible_with=compatible, description=description):
        flash('Part updated!', 'success')
    else:
        flash('Failed to update part.', 'error')
    return redirect(url_for('parts'))

@app.route('/parts/delete/<int:part_id>', methods=['POST'])
@admin_required
def part_delete(part_id):
    delete_part(part_id)
    flash('Part deleted.', 'success')
    return redirect(url_for('parts'))

@app.route('/orders/update-status/<int:order_id>', methods=['POST'])
@admin_required
def order_update_status(order_id):
    status = request.form.get('status','').strip()
    if status:
        update_order_status(order_id, status)
        flash(f'Order status updated to {status}.', 'success')
    return redirect(url_for('parts'))

@app.route('/orders/delete/<int:order_id>', methods=['POST'])
@admin_required
def order_delete(order_id):
    delete_order(order_id)
    flash('Order deleted.', 'success')
    return redirect(url_for('parts'))


# ═══════════════════════════════════════════════════════════
#  INSTALLMENTS
# ═══════════════════════════════════════════════════════════

@app.route('/installments')
@admin_required
def installments():
    branch_id = get_branch_id()
    all_inst  = get_all_installments(branch_id)
    return render_template('installments.html', installments=all_inst)

@app.route('/installments/pay/<int:inst_id>', methods=['POST'])
@admin_required
def installment_pay(inst_id):
    amount   = float(request.form.get('amount', 0) or 0)
    pay_date = request.form.get('pay_date', '').strip()
    notes    = request.form.get('notes', '').strip()
    if not amount or not pay_date:
        flash('Please fill in amount and date.', 'error')
        return redirect(url_for('installments'))
    if record_installment_payment(inst_id, amount, pay_date, notes):
        flash(f'Payment of ₱{amount:,.2f} recorded!', 'success')
    else:
        flash('Failed to record payment.', 'error')
    return redirect(url_for('installments'))

@app.route('/installments/<int:inst_id>/history')
@admin_required
def installment_history(inst_id):
    inst     = get_installment_by_id(inst_id)
    payments = get_installment_payments(inst_id)
    return render_template('installment_history.html', installment=inst, payments=payments)


# ═══════════════════════════════════════════════════════════
#  BRANCHES
# ═══════════════════════════════════════════════════════════

@app.route('/branches')
@superadmin_required
def branches():
    return render_template('branches.html', branches=get_all_branches())

@app.route('/branches/add', methods=['POST'])
@superadmin_required
def branch_add():
    name    = request.form.get('name','').strip()
    address = request.form.get('address','').strip()
    phone   = request.form.get('phone','').strip()
    email   = request.form.get('email','').strip()
    if not name or not address:
        flash('Branch name and address are required.', 'error')
        return redirect(url_for('branches'))
    if add_branch(name=name, address=address, phone=phone, email=email):
        flash(f'Branch "{name}" created!', 'success')
    else:
        flash('Failed to create branch.', 'error')
    return redirect(url_for('branches'))

@app.route('/branches/edit/<int:branch_id>', methods=['POST'])
@superadmin_required
def branch_edit(branch_id):
    name    = request.form.get('name','').strip()
    address = request.form.get('address','').strip()
    phone   = request.form.get('phone','').strip()
    email   = request.form.get('email','').strip()
    update_branch(branch_id, name=name, address=address, phone=phone, email=email)
    flash('Branch updated!', 'success')
    return redirect(url_for('branches'))

@app.route('/branches/delete/<int:branch_id>', methods=['POST'])
@superadmin_required
def branch_delete(branch_id):
    delete_branch(branch_id)
    flash('Branch deleted.', 'success')
    return redirect(url_for('branches'))

@app.route('/branches/<int:branch_id>')
@superadmin_required
def branch_view(branch_id):
    branch  = get_branch_by_id(branch_id)
    motors  = get_all_motors(branch_id)
    rentals = get_all_rentals(branch_id)
    stats   = get_dashboard_stats(branch_id)
    return render_template('dashboard.html',
        stats=stats, motors=motors, rentals=rentals,
        branch=branch, branch_view=True,
        role=session.get('role'), user_name=session.get('user_name'),
    )


# ═══════════════════════════════════════════════════════════
#  CUSTOMERS
# ═══════════════════════════════════════════════════════════

@app.route('/customers')
@admin_required
def customers():
    search = request.args.get('search', '')
    all_customers = get_all_customers()
    if search:
        s = search.lower()
        all_customers = [c for c in all_customers
                         if s in c['firstname'].lower() or s in c['lastname'].lower()
                         or s in c['email'].lower() or s in c['license_no'].lower()]
    return render_template('customers.html', customers=all_customers,
                           role=session.get('role'), search=search)

@app.route('/customers/delete/<int:customer_id>', methods=['POST'])
@admin_required
def customer_delete(customer_id):
    delete_customer(customer_id)
    flash('Customer removed.', 'success')
    return redirect(url_for('customers'))


# ═══════════════════════════════════════════════════════════
#  PROFILE
# ═══════════════════════════════════════════════════════════

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
    return render_template('profile.html', customer=None, role=session.get('role'),
                           user_name=session.get('user_name'))


if __name__ == '__main__':
    app.run(debug=True)