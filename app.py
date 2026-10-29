
import os
import sqlite3
import uuid

from datetime import date
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# Create Flask application
app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-change-this-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB upload limit

# Database and upload folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB = os.path.join(BASE_DIR, 'ecocollect.db')
UPLOADS = os.path.join(BASE_DIR, 'static', 'uploads')

os.makedirs(UPLOADS, exist_ok=True)

ALLOWED = {'jpg', 'jpeg', 'png', 'webp'}


# Connect to database
def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


# Create database tables
def init_db():
    with connect() as db:

        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            points INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pickups(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            pickup_date TEXT NOT NULL,
            pickup_time TEXT NOT NULL,
            address TEXT NOT NULL,
            notes TEXT,
            image TEXT,
            status TEXT DEFAULT 'Pending',
            collector_id INTEGER,
            recycler_id INTEGER,
            points_awarded INTEGER DEFAULT 0
        );
        ''')

        # Create demo accounts
        if db.execute(
            'SELECT COUNT(*) FROM users'
        ).fetchone()[0] == 0:

            demos = [
                (
                    'Demo User',
                    'user@ecocollect.demo',
                    'demo1234',
                    'user'
                ),
                (
                    'Demo Collector',
                    'collector@ecocollect.demo',
                    'demo1234',
                    'collector'
                ),
                (
                    'Demo Recycler',
                    'recycler@ecocollect.demo',
                    'demo1234',
                    'recycler'
                )
            ]

            for name, email, pw, role in demos:

                db.execute(
                    '''
                    INSERT INTO users
                    (name, email, password, role)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        name,
                        email,
                        generate_password_hash(pw),
                        role
                    )
                )


# Check whether user is logged in
def login_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if not session.get('user_id'):
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))

        return fn(*args, **kwargs)

    return wrapper


# Check user role
def roles_required(*roles):

    def decorate(fn):

        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):

            if session.get('role') not in roles:
                flash(
                    'You do not have access to this page.',
                    'error'
                )
                return redirect(url_for('dashboard'))

            return fn(*args, **kwargs)

        return wrapper

    return decorate


# Demo image identification
def identify_demo(filename):

    name = filename.lower()

    items = [
        (('phone', 'mobile'), 'Mobile phone'),
        (('laptop', 'computer', 'pc'), 'Laptop / computer'),
        (('battery', 'cell'), 'Battery'),
        (('charger', 'cable'), 'Charger / cable')
    ]

    for words, label in items:

        if any(word in name for word in words):
            return label

    return 'Other electronics — please verify manually'


# Home page
@app.route('/')
def home():

    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    return render_template('index.html')


# Registration
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user')

        if (
            not name
            or not email
            or len(password) < 8
            or role not in ('user', 'collector', 'recycler')
        ):

            flash(
                'Enter valid details. Password must be at least 8 characters.',
                'error'
            )

        else:

            try:

                with connect() as db:

                    cur = db.execute(
                        '''
                        INSERT INTO users
                        (name, email, password, role)
                        VALUES (?, ?, ?, ?)
                        ''',
                        (
                            name,
                            email,
                            generate_password_hash(password),
                            role
                        )
                    )

                session.update(
                    user_id=cur.lastrowid,
                    name=name,
                    role=role
                )

                return redirect(url_for('dashboard'))

            except sqlite3.IntegrityError:

                flash(
                    'This email is already registered.',
                    'error'
                )

    return render_template('auth.html', mode='Register')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        with connect() as db:

            user = db.execute(
                'SELECT * FROM users WHERE email=?',
                (
                    request.form.get(
                        'email', ''
                    ).strip().lower(),
                )
            ).fetchone()

        if user and check_password_hash(
            user['password'],
            request.form.get('password', '')
        ):

            session.clear()

            session.update(
                user_id=user['id'],
                name=user['name'],
                role=user['role']
            )

            return redirect(url_for('dashboard'))

        flash('Email or password is incorrect.', 'error')

    return render_template('auth.html', mode='Login')


# Logout
@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('home'))


# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():

    with connect() as db:

        user = db.execute(
            'SELECT * FROM users WHERE id=?',
            (session['user_id'],)
        ).fetchone()

        if user['role'] == 'user':

            rows = db.execute(
                '''
                SELECT p.*, c.name collector_name,
                       r.name recycler_name
                FROM pickups p
                LEFT JOIN users c
                    ON p.collector_id = c.id
                LEFT JOIN users r
                    ON p.recycler_id = r.id
                WHERE p.user_id=?
                ORDER BY p.id DESC
                ''',
                (user['id'],)
            ).fetchall()

        elif user['role'] == 'collector':

            rows = db.execute(
                '''
                SELECT p.*, u.name customer,
                       u.email customer_email
                FROM pickups p
                JOIN users u ON p.user_id=u.id
                WHERE p.status='Pending'
                   OR p.collector_id=?
                ORDER BY p.id DESC
                ''',
                (user['id'],)
            ).fetchall()

        else:

            rows = db.execute(
                '''
                SELECT p.*, u.name customer,
                       c.name collector
                FROM pickups p
                JOIN users u ON p.user_id=u.id
                LEFT JOIN users c
                    ON p.collector_id=c.id
                WHERE p.recycler_id=?
                ORDER BY p.id DESC
                ''',
                (user['id'],)
            ).fetchall()

        recyclers = db.execute(
            "SELECT id, name FROM users WHERE role='recycler'"
        ).fetchall()

    return render_template(
        'dashboard.html',
        user=user,
        rows=rows,
        recyclers=recyclers,
        today=date.today().isoformat()
    )


# Upload and identify e-waste image
@app.route('/identify', methods=['POST'])
@roles_required('user')
def identify():

    photo = request.files.get('photo')

    if (
        not photo
        or not photo.filename
        or '.' not in photo.filename
        or photo.filename.rsplit('.', 1)[1].lower() not in ALLOWED
    ):

        flash('Choose a JPG, PNG or WEBP image.', 'error')

        return redirect(url_for('dashboard'))

    filename = (
        uuid.uuid4().hex
        + '_'
        + secure_filename(photo.filename)
    )

    photo.save(os.path.join(UPLOADS, filename))

    label = identify_demo(filename)

    session['identified_image'] = filename
    session['identified_label'] = label

    flash(
        'Demo suggestion: ' + label
        + '. Please verify the item yourself.',
        'success'
    )

    return redirect(url_for('dashboard'))


# Book pickup
@app.route('/book', methods=['POST'])
@roles_required('user')
def book():

    category = request.form.get('category', '')

    try:
        quantity = int(request.form.get('quantity', '1'))
    except ValueError:
        quantity = 0

    pickup_date = request.form.get('pickup_date', '')
    pickup_time = request.form.get('pickup_time', '')
    address = request.form.get('address', '').strip()

    allowed_categories = [
        'Mobile phone',
        'Laptop / computer',
        'Battery',
        'Charger / cable',
        'Small appliance',
        'Other electronics'
    ]

    if (
        category not in allowed_categories
        or not 1 <= quantity <= 100
        or pickup_date < date.today().isoformat()
        or not pickup_time
        or not address
    ):

        flash(
            'Please complete all pickup details correctly.',
            'error'
        )

    else:

        with connect() as db:

            db.execute(
                '''
                INSERT INTO pickups
                (
                    user_id, category, quantity,
                    pickup_date, pickup_time,
                    address, notes, image
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    session['user_id'],
                    category,
                    quantity,
                    pickup_date,
                    pickup_time,
                    address,
                    request.form.get('notes', ''),
                    session.get('identified_image')
                )
            )

        session.pop('identified_image', None)
        session.pop('identified_label', None)

        flash('Pickup request submitted!', 'success')

    return redirect(url_for('dashboard'))


# Collector accepts pickup
@app.route('/pickup/<int:pid>/accept', methods=['POST'])
@roles_required('collector')
def accept(pid):

    with connect() as db:

        row = db.execute(
            """
            SELECT * FROM pickups
            WHERE id=? AND status='Pending'
            """,
            (pid,)
        ).fetchone()

        if row:

            db.execute(
                """
                UPDATE pickups
                SET status='Accepted', collector_id=?
                WHERE id=?
                """,
                (session['user_id'], pid)
            )

            flash('Request accepted.', 'success')

        else:

            flash(
                'This request is no longer available.',
                'error'
            )

    return redirect(url_for('dashboard'))


# Collector updates pickup status
@app.route('/pickup/<int:pid>/update', methods=['POST'])
@roles_required('collector')
def update_pickup(pid):

    status = request.form.get('status')

    with connect() as db:

        row = db.execute(
            '''
            SELECT * FROM pickups
            WHERE id=? AND collector_id=?
            ''',
            (pid, session['user_id'])
        ).fetchone()

        if not row:

            flash('Request not assigned to you.', 'error')

        elif status == 'Picked up' and row['status'] == 'Accepted':

            db.execute(
                "UPDATE pickups SET status='Picked up' WHERE id=?",
                (pid,)
            )

            flash('Pickup marked complete.', 'success')

        elif (
            status == 'Delivered to recycler'
            and row['status'] == 'Picked up'
        ):

            rid = request.form.get('recycler_id', type=int)

            valid = db.execute(
                "SELECT id FROM users WHERE id=? AND role='recycler'",
                (rid,)
            ).fetchone()

            if valid:

                db.execute(
                    '''
                    UPDATE pickups
                    SET status='Delivered to recycler',
                        recycler_id=?
                    WHERE id=?
                    ''',
                    (rid, pid)
                )

                flash(
                    'Delivery sent to recycler for verification.',
                    'success'
                )

            else:

                flash('Select a valid recycler account.', 'error')

        else:

            flash('Follow the pickup status sequence.', 'error')

    return redirect(url_for('dashboard'))


# Recycler records processing
@app.route('/pickup/<int:pid>/process', methods=['POST'])
@roles_required('recycler')
def process(pid):

    outcome = request.form.get('outcome')

    if outcome not in (
        'Recycled',
        'Refurbished',
        'Parts recovered',
        'Needs review'
    ):

        flash('Choose a valid outcome.', 'error')

        return redirect(url_for('dashboard'))

    with connect() as db:

        row = db.execute(
            """
            SELECT * FROM pickups
            WHERE id=?
            AND recycler_id=?
            AND status='Delivered to recycler'
            """,
            (pid, session['user_id'])
        ).fetchone()

        if row:

            db.execute(
                """
                UPDATE pickups
                SET status='Processing complete'
                WHERE id=?
                """,
                (pid,)
            )

            if outcome != 'Needs review' and not row['points_awarded']:

                points = min(
                    100,
                    max(10, row['quantity'] * 20)
                )

                db.execute(
                    'UPDATE users SET points=points+? WHERE id=?',
                    (points, row['user_id'])
                )

                db.execute(
                    'UPDATE pickups SET points_awarded=? WHERE id=?',
                    (points, pid)
                )

            flash(
                'Processing recorded. Green Points credited if eligible.',
                'success'
            )

        else:

            flash(
                'This delivery is not assigned to your centre.',
                'error'
            )

    return redirect(url_for('dashboard'))


# Run application
# Initialize the database when the application starts.
init_db()

if __name__ == '__main__':
    # Debug mode is disabled by default; enable locally with FLASK_DEBUG=1 if needed.
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
