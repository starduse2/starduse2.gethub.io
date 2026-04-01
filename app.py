from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.utils import secure_filename
import pandas as pd
import sqlite3
import os
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # غيّره في الإنتاج
#app.secret_key = '92525'  # غيّره في الإنتاج

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'الرجاء تسجيل الدخول أولاً'

# إعداد رفع الملفات
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_NAME = 'employees.db'

# ---------- دوال قاعدة البيانات ----------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # جدول الموظفين
    conn.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numera TEXT UNIQUE NOT NULL,
            rank TEXT,
            name TEXT NOT NULL,
            department TEXT,
            administration TEXT,
            phone TEXT,
            whatsapp TEXT,
            profession TEXT,
            enlistment_date TEXT,
            notes TEXT
        )
    ''')
    # جدول المستخدمين
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()

def create_default_admin():
    """إنشاء مستخدم admin افتراضي إذا لم يكن موجوداً"""
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        hashed = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     ('admin', hashed, 'admin'))
        conn.commit()
        print("تم إنشاء المستخدم admin / admin123")
    conn.close()

# تهيئة قاعدة البيانات والمستخدم الافتراضي عند بدء التشغيل
init_db()
create_default_admin()

# ---------- نموذج المستخدم ----------
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['role'])
    return None

# ---------- دوال مساعدة للصلاحيات ----------
def admin_required(func):
    """Decorator: يسمح فقط للمستخدمين من نوع admin"""
    from functools import wraps
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('غير مسموح بالدخول. هذه الصفحة مخصصة للإدمن فقط.', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_view

def user_can_add():
    """التحقق من أن المستخدم الحالي يمكنه الإضافة (admin أو user)"""
    return current_user.is_authenticated and current_user.role in ('admin', 'user')

# ثم context processor
@app.context_processor
def utility_processor():
    return dict(user_can_add=user_can_add)

# في app.py بعد تعريف الدالة user_can_add

# ---------- صفحات المصادقة ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['role'])
            login_user(user_obj)
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('login'))

# ---------- إدارة المستخدمين (للأدمن فقط) ----------
@app.route('/users')
@login_required
@admin_required
def list_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role FROM users').fetchall()
    conn.close()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                         (username, hashed, role))
            conn.commit()
            flash(f'المستخدم {username} تمت إضافته بنجاح', 'success')
        except sqlite3.IntegrityError:
            flash('اسم المستخدم موجود مسبقاً', 'danger')
        finally:
            conn.close()
        return redirect(url_for('list_users'))
    return render_template('add_user.html')

@app.route('/delete_user/<int:id>')
@login_required
@admin_required
def delete_user(id):
    if id == current_user.id:
        flash('لا يمكنك حذف نفسك', 'danger')
        return redirect(url_for('list_users'))
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('تم حذف المستخدم', 'success')
    return redirect(url_for('list_users'))

# ---------- وظائف إدارة الموظفين ----------
def get_sort_field(sort_by):
    mapping = {'department': 'department', 'administration': 'administration'}
    return mapping.get(sort_by, 'id')

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    query = "SELECT * FROM employees WHERE 1=1"
    params = []

    # البحث
    search_term = request.args.get('search', '')
    search_type = request.args.get('search_type', 'name')
    if search_term:
        if search_type == 'name':
            query += " AND name LIKE ?"
            params.append(f'%{search_term}%')
        else:
            query += " AND numera LIKE ?"
            params.append(f'%{search_term}%')

    # الفرز
    sort_by = request.args.get('sort_by', '')
    if sort_by in ['department', 'administration']:
        query += f" ORDER BY {sort_by}"

    employees = conn.execute(query, params).fetchall()
    total_count = len(employees)
    conn.close()

    return render_template('index.html',
                           employees=employees,
                           total_count=total_count,
                           search_term=search_term,
                           search_type=search_type,
                           sort_by=sort_by)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not user_can_add():
        flash('غير مسموح لك بإضافة موظفين', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            data = (
                request.form['numera'],
                request.form['rank'],
                request.form['name'],
                request.form['department'],
                request.form['administration'],
                request.form['phone'],
                request.form['whatsapp'],
                request.form['profession'],
                request.form['enlistment_date'],
                request.form['notes']
            )
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO employees (numera, rank, name, department, administration, phone, whatsapp, profession, enlistment_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
            conn.close()
            flash('تم إضافة الموظف بنجاح', 'success')
        except sqlite3.IntegrityError:
            flash('رقم النمرة موجود مسبقاً! الرجاء استخدام رقم مختلف.', 'danger')
        except Exception as e:
            flash(f'حدث خطأ: {str(e)}', 'danger')
        return redirect(url_for('index'))
    return render_template('add_employee.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    if current_user.role != 'admin':
        flash('غير مسموح لك بتعديل البيانات', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    employee = conn.execute('SELECT * FROM employees WHERE id = ?', (id,)).fetchone()
    if not employee:
        flash('الموظف غير موجود', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        data = (
            request.form['numera'],
            request.form['rank'],
            request.form['name'],
            request.form['department'],
            request.form['administration'],
            request.form['phone'],
            request.form['whatsapp'],
            request.form['profession'],
            request.form['enlistment_date'],
            request.form['notes'],
            id
        )
        try:
            conn.execute('''
                UPDATE employees SET numera=?, rank=?, name=?, department=?, administration=?,
                phone=?, whatsapp=?, profession=?, enlistment_date=?, notes=? WHERE id=?
            ''', data)
            conn.commit()
            flash('تم تحديث البيانات بنجاح', 'success')
        except sqlite3.IntegrityError:
            flash('رقم النمرة موجود مسبقاً لدى موظف آخر.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('index'))
    conn.close()
    return render_template('edit_employee.html', employee=employee)

@app.route('/delete/<int:id>')
@login_required
def delete_employee(id):
    if current_user.role != 'admin':
        flash('غير مسموح لك بحذف البيانات', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()
    conn.execute('DELETE FROM employees WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('تم حذف الموظف بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/delete_selected', methods=['POST'])
@login_required
def delete_selected():
    if current_user.role != 'admin':
        flash('غير مسموح لك بحذف البيانات', 'danger')
        return redirect(url_for('index'))

    ids = request.form.getlist('selected_ids')
    if ids:
        conn = get_db_connection()
        placeholders = ','.join('?' for _ in ids)
        conn.execute(f'DELETE FROM employees WHERE id IN ({placeholders})', ids)
        conn.commit()
        conn.close()
        flash(f'تم حذف {len(ids)} موظف/موظفين بنجاح', 'success')
    else:
        flash('لم يتم اختيار أي موظف للحذف', 'warning')
    return redirect(url_for('index'))

@app.route('/export', methods=['POST'])
@login_required
def export():
    if current_user.role != 'admin':
        flash('غير مسموح لك بتصدير البيانات', 'danger')
        return redirect(url_for('index'))

    ids = request.form.getlist('selected_ids')
    conn = get_db_connection()
    if ids:
        placeholders = ','.join('?' for _ in ids)
        employees = conn.execute(f'SELECT * FROM employees WHERE id IN ({placeholders})', ids).fetchall()
    else:
        employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()

    data = []
    for emp in employees:
        data.append({
            'النمرة': emp['numera'],
            'الرتبة': emp['rank'],
            'الاسم': emp['name'],
            'الدائرة': emp['department'],
            'الإدارة': emp['administration'],
            'الهاتف': emp['phone'],
            'واتساب': emp['whatsapp'],
            'المهنة': emp['profession'],
            'تاريخ التجنيد': emp['enlistment_date'],
            'ملاحظات': emp['notes']
        })
    df = pd.DataFrame(data)
    export_file = os.path.join(app.config['UPLOAD_FOLDER'], 'exported_employees.xlsx')
    df.to_excel(export_file, index=False, engine='openpyxl')
    return send_file(export_file, as_attachment=True, download_name='employees.xlsx')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_data():
    if current_user.role != 'admin':
        flash('غير مسموح لك باستيراد البيانات', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filepath)
                else:
                    df = pd.read_excel(filepath, engine='openpyxl')
            except Exception as e:
                flash(f'خطأ في قراءة الملف: {str(e)}', 'danger')
                return redirect(url_for('import_data'))

            required_cols = ['النمرة', 'الرتبة', 'الاسم', 'الدائرة', 'الإدارة', 'الهاتف', 'واتساب', 'المهنة', 'تاريخ التجنيد', 'ملاحظات']
            if not all(col in df.columns for col in required_cols):
                flash('ملف الاستيراد لا يحتوي على الأعمدة المطلوبة بالعربية.', 'danger')
                return redirect(url_for('import_data'))

            conn = get_db_connection()
            new_count = 0
            duplicate_count = 0
            for _, row in df.iterrows():
                numera = str(row['النمرة'])
                existing = conn.execute('SELECT id FROM employees WHERE numera = ?', (numera,)).fetchone()
                if existing:
                    duplicate_count += 1
                    continue
                conn.execute('''
                    INSERT INTO employees (numera, rank, name, department, administration, phone, whatsapp, profession, enlistment_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    numera, row['الرتبة'], row['الاسم'], row['الدائرة'], row['الإدارة'],
                    row['الهاتف'], row['واتساب'], row['المهنة'], row['تاريخ التجنيد'], row['ملاحظات']
                ))
                new_count += 1
            conn.commit()
            conn.close()
            flash(f'تم استيراد {new_count} سجل جديد. تم تخطي {duplicate_count} سجل مكرر (النمرة موجودة مسبقاً).', 'success')
            return redirect(url_for('index'))
        else:
            flash('نوع الملف غير مدعوم. يرجى رفع ملف CSV أو Excel.', 'danger')
    return render_template('import.html')

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=80)
