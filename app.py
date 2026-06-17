# app.py - Main Flask application for JobSphere

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from utils.pdf_extractor import extract_all
import os
from datetime import date, datetime

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)

# Make today's date available in every template automatically
@app.context_processor
def inject_today():
    return {'today': date.today()}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ─── Public Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT j.*, c.name as category_name
        FROM jobs j LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.last_date >= CURDATE()
        ORDER BY j.posted_at DESC LIMIT 6
    """)
    recent_jobs = cur.fetchall()
    cur.execute("SELECT COUNT(*) as total FROM jobs WHERE last_date >= CURDATE()")
    total = cur.fetchone()['total']
    cur.close()
    return render_template('index.html', recent_jobs=recent_jobs, total=total)

# ─── Authentication ─────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name  = request.form.get('full_name', '').strip()
        email      = request.form.get('email', '').strip()
        password   = request.form.get('password', '').strip()
        qualify    = request.form.get('qualification', '').strip()
        dob        = request.form.get('date_of_birth', '').strip()
        age        = request.form.get('age', '').strip()

        if not all([full_name, email, password, qualify, dob, age]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            flash('Email already registered. Please login.', 'warning')
            cur.close()
            return redirect(url_for('login'))

        hashed_pw = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users (full_name, email, password, qualification, date_of_birth, age)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (full_name, email, hashed_pw, qualify, dob, age))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['full_name']
            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─── User Dashboard ─────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) as c FROM jobs WHERE last_date >= CURDATE()")
    total_jobs = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) as c FROM saved_jobs WHERE user_id = %s", (uid,))
    saved_count = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) as c FROM applied_jobs WHERE user_id = %s", (uid,))
    applied_count = cur.fetchone()['c']

    cur.execute("""
        SELECT j.*, c.name as category_name
        FROM jobs j LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.last_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        ORDER BY j.last_date ASC LIMIT 5
    """)
    expiring_soon = cur.fetchall()
    cur.close()

    return render_template('dashboard.html',
        total_jobs=total_jobs,
        saved_count=saved_count,
        applied_count=applied_count,
        expiring_soon=expiring_soon
    )


@app.route('/jobs')
@login_required
def jobs():
    uid        = session['user_id']
    search     = request.args.get('search', '').strip()
    category   = request.args.get('category', '').strip()
    qualify    = request.args.get('qualification', '').strip()
    expiring   = request.args.get('expiring', '').strip()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    # Get current user's qualification for eligibility hint
    cur.execute("SELECT qualification FROM users WHERE id = %s", (uid,))
    user_qualify = cur.fetchone()['qualification']

    query = """
        SELECT j.*, c.name as category_name,
               (SELECT COUNT(*) FROM saved_jobs WHERE user_id=%s AND job_id=j.id) as is_saved,
               (SELECT COUNT(*) FROM applied_jobs WHERE user_id=%s AND job_id=j.id) as is_applied
        FROM jobs j LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.last_date >= CURDATE()
    """
    params = [uid, uid]

    if search:
        query += " AND (j.title LIKE %s OR j.qualification LIKE %s)"
        params += [f'%{search}%', f'%{search}%']
    if category:
        query += " AND c.name = %s"
        params.append(category)
    if qualify:
        query += " AND j.qualification LIKE %s"
        params.append(f'%{qualify}%')
    if expiring == 'yes':
        query += " AND j.last_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)"

    query += " ORDER BY j.last_date ASC"
    cur.execute(query, params)
    job_list = cur.fetchall()
    cur.close()

    return render_template('jobs.html',
        job_list=job_list,
        categories=categories,
        user_qualify=user_qualify,
        search=search,
        selected_category=category
    )


@app.route('/job/<int:job_id>')
@login_required
def job_detail(job_id):
    uid = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT j.*, c.name as category_name
        FROM jobs j LEFT JOIN categories c ON j.category_id = c.id
        WHERE j.id = %s
    """, (job_id,))
    job = cur.fetchone()

    cur.execute("SELECT COUNT(*) as c FROM saved_jobs WHERE user_id=%s AND job_id=%s", (uid, job_id))
    is_saved = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) as c FROM applied_jobs WHERE user_id=%s AND job_id=%s", (uid, job_id))
    is_applied = cur.fetchone()['c']
    cur.close()

    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('jobs'))

    return render_template('job_detail.html', job=job, is_saved=is_saved, is_applied=is_applied)


@app.route('/save_job/<int:job_id>')
@login_required
def save_job(job_id):
    uid = session['user_id']
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO saved_jobs (user_id, job_id) VALUES (%s, %s)", (uid, job_id))
        mysql.connection.commit()
        flash('Job saved successfully!', 'success')
    except:
        flash('Job already saved.', 'info')
    cur.close()
    return redirect(request.referrer or url_for('jobs'))


@app.route('/unsave_job/<int:job_id>')
@login_required
def unsave_job(job_id):
    uid = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM saved_jobs WHERE user_id=%s AND job_id=%s", (uid, job_id))
    mysql.connection.commit()
    cur.close()
    flash('Job removed from saved list.', 'info')
    return redirect(request.referrer or url_for('saved_jobs'))


@app.route('/mark_applied/<int:job_id>')
@login_required
def mark_applied(job_id):
    uid = session['user_id']
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO applied_jobs (user_id, job_id) VALUES (%s, %s)", (uid, job_id))
        mysql.connection.commit()
        flash('Marked as applied!', 'success')
    except:
        flash('Already marked as applied.', 'info')
    cur.close()
    return redirect(request.referrer or url_for('jobs'))


@app.route('/saved_jobs')
@login_required
def saved_jobs():
    uid = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT j.*, c.name as category_name
        FROM saved_jobs s
        JOIN jobs j ON s.job_id = j.id
        LEFT JOIN categories c ON j.category_id = c.id
        WHERE s.user_id = %s
        ORDER BY s.saved_at DESC
    """, (uid,))
    jobs_list = cur.fetchall()
    cur.close()
    return render_template('saved_jobs.html', jobs_list=jobs_list)


@app.route('/applied_jobs')
@login_required
def applied_jobs():
    uid = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT j.*, c.name as category_name, a.applied_at
        FROM applied_jobs a
        JOIN jobs j ON a.job_id = j.id
        LEFT JOIN categories c ON j.category_id = c.id
        WHERE a.user_id = %s
        ORDER BY a.applied_at DESC
    """, (uid,))
    jobs_list = cur.fetchall()
    cur.close()
    return render_template('applied_jobs.html', jobs_list=jobs_list)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    uid = session['user_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        qualify   = request.form.get('qualification', '').strip()
        dob       = request.form.get('date_of_birth', '').strip()
        age       = request.form.get('age', '').strip()
        cur.execute("""
            UPDATE users SET full_name=%s, qualification=%s, date_of_birth=%s, age=%s
            WHERE id=%s
        """, (full_name, qualify, dob, age, uid))
        mysql.connection.commit()
        session['user_name'] = full_name
        flash('Profile updated successfully!', 'success')

    cur.execute("SELECT * FROM users WHERE id = %s", (uid,))
    user = cur.fetchone()
    cur.close()
    return render_template('profile.html', user=user)


@app.route('/uploads/pdfs/<filename>')
def serve_pdf(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ─── Admin Routes ───────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()
        cur.close()

        if admin and check_password_hash(admin['password'], password):
            session['admin_id']   = admin['id']
            session['admin_name'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')

    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as c FROM jobs")
    total_jobs = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM jobs WHERE last_date >= CURDATE()")
    active_jobs = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM jobs WHERE last_date < CURDATE()")
    expired_jobs = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM users")
    total_users = cur.fetchone()['c']

    # Category-wise job count for chart
    cur.execute("""
        SELECT c.name, COUNT(j.id) as count
        FROM categories c LEFT JOIN jobs j ON c.id = j.category_id
        GROUP BY c.id, c.name
    """)
    category_stats = cur.fetchall()
    cur.close()

    return render_template('admin/dashboard.html',
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        expired_jobs=expired_jobs,
        total_users=total_users,
        category_stats=category_stats
    )


@app.route('/admin/jobs')
@admin_required
def admin_jobs():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT j.*, c.name as category_name
        FROM jobs j LEFT JOIN categories c ON j.category_id = c.id
        ORDER BY j.posted_at DESC
    """)
    all_jobs = cur.fetchall()
    cur.close()
    return render_template('admin/jobs.html', all_jobs=all_jobs)


@app.route('/admin/add_job', methods=['GET', 'POST'])
@admin_required
def add_job():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    extracted = None

    if request.method == 'POST':
        action = request.form.get('action', 'save')

        # Handle PDF upload and extraction
        if action == 'extract':
            pdf_file = request.files.get('pdf_file')
            if pdf_file and allowed_file(pdf_file.filename):
                filename = secure_filename(pdf_file.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf_file.save(save_path)
                extracted = extract_all(save_path)
                extracted['filename'] = filename
                flash('PDF processed. Review and edit the extracted information below.', 'info')
            else:
                flash('Please upload a valid PDF file.', 'danger')
            cur.close()
            return render_template('admin/add_job.html', categories=categories, extracted=extracted)

        # Save job to database
        title      = request.form.get('title', '').strip()
        cat_id     = request.form.get('category_id', '').strip()
        qualify    = request.form.get('qualification', '').strip()
        age_limit  = request.form.get('age_limit', '').strip()
        salary     = request.form.get('salary', '').strip()
        last_date  = request.form.get('last_date', '').strip() or None
        apply_link = request.form.get('apply_link', '').strip()
        pdf_name   = request.form.get('pdf_filename', '').strip() or None

        if not title:
            flash('Job title is required.', 'danger')
            cur.close()
            return render_template('admin/add_job.html', categories=categories)

        cur.execute("""
            INSERT INTO jobs (title, category_id, qualification, age_limit, salary, last_date, apply_link, pdf_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, cat_id or None, qualify, age_limit, salary, last_date, apply_link, pdf_name))
        mysql.connection.commit()
        cur.close()
        flash('Job added successfully!', 'success')
        return redirect(url_for('admin_jobs'))

    cur.close()
    return render_template('admin/add_job.html', categories=categories, extracted=extracted)


@app.route('/admin/edit_job/<int:job_id>', methods=['GET', 'POST'])
@admin_required
def edit_job(job_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()

    if request.method == 'POST':
        title      = request.form.get('title', '').strip()
        cat_id     = request.form.get('category_id', '').strip()
        qualify    = request.form.get('qualification', '').strip()
        age_limit  = request.form.get('age_limit', '').strip()
        salary     = request.form.get('salary', '').strip()
        last_date  = request.form.get('last_date', '').strip() or None
        apply_link = request.form.get('apply_link', '').strip()

        cur.execute("""
            UPDATE jobs SET title=%s, category_id=%s, qualification=%s,
            age_limit=%s, salary=%s, last_date=%s, apply_link=%s WHERE id=%s
        """, (title, cat_id or None, qualify, age_limit, salary, last_date, apply_link, job_id))
        mysql.connection.commit()
        cur.close()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('admin_jobs'))

    cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
    job = cur.fetchone()
    cur.close()
    return render_template('admin/edit_job.html', job=job, categories=categories)


@app.route('/admin/delete_job/<int:job_id>')
@admin_required
def delete_job(job_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
    mysql.connection.commit()
    cur.close()
    flash('Job deleted.', 'info')
    return redirect(url_for('admin_jobs'))


@app.route('/admin/users')
@admin_required
def admin_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close()
    return render_template('admin/users.html', users=users)


# ─── Run ────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
