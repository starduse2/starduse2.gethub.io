# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import os
import sqlite3
from database import get_db_connection, init_db
from werkzeug.utils import secure_filename

app = Flask(__name__)
#app.secret_key = 'your_secret_key_here'  # غيّره في الإنتاج
app.secret_key = '92525'  # غيّره في الإنتاج

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# تهيئة قاعدة البيانات عند بدء التشغيل
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- المساعدات ----------
def get_sort_field(sort_by):
    """تحويل اسم الحقل من الواجهة إلى اسم العمود في قاعدة البيانات"""
    mapping = {
        'department': 'department',
        'administration': 'administration'
    }
    return mapping.get(sort_by, 'id')

# ---------- الصفحة الرئيسية (عرض، بحث، فرز، اختيار) ----------
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    query = "SELECT * FROM employees WHERE 1=1"
    params = []

    # معالجة البحث
    search_term = request.args.get('search', '')
    search_type = request.args.get('search_type', 'name')  # name أو numera
    if search_term:
        if search_type == 'name':
            query += " AND name LIKE ?"
            params.append(f'%{search_term}%')
        else:
            query += " AND numera LIKE ?"
            params.append(f'%{search_term}%')

    # معالجة الفرز
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

# ---------- إضافة موظف ----------
@app.route('/add', methods=['GET', 'POST'])
def add_employee():
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
            request.form['notes']
        )
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO employees (numera, rank, name, department, administration, phone, whatsapp, profession, enlistment_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
            flash('تم إضافة الموظف بنجاح', 'success')
        except sqlite3.IntegrityError:
            flash('رقم النمرة موجود مسبقاً! الرجاء استخدام رقم مختلف.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('index'))
    return render_template('add_employee.html')

# ---------- تعديل موظف ----------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
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

# ---------- حذف موظف واحد ----------
@app.route('/delete/<int:id>')
def delete_employee(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM employees WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('تم حذف الموظف بنجاح', 'success')
    return redirect(url_for('index'))

# ---------- حذف مجموعة عبر checkbox ----------
@app.route('/delete_selected', methods=['POST'])
def delete_selected():
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

# ---------- تصدير البيانات (كلها أو المحددة فقط) ----------
@app.route('/export', methods=['POST'])
def export():
    ids = request.form.getlist('selected_ids')  # قد تكون فارغة
    conn = get_db_connection()
    if ids:
        placeholders = ','.join('?' for _ in ids)
        employees = conn.execute(f'SELECT * FROM employees WHERE id IN ({placeholders})', ids).fetchall()
    else:
        employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()

    # تحويل إلى DataFrame
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

# ---------- استيراد بيانات (مع منع التكرار بناءً على النمرة) ----------
@app.route('/import', methods=['GET', 'POST'])
def import_data():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # قراءة الملف
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath, engine='openpyxl')

            # تأكد من وجود الأعمدة المطلوبة (بأسماء عربية كما في التصدير)
            required_cols = ['النمرة', 'الرتبة', 'الاسم', 'الدائرة', 'الإدارة', 'الهاتف', 'واتساب', 'المهنة', 'تاريخ التجنيد', 'ملاحظات']
            if not all(col in df.columns for col in required_cols):
                flash('ملف الاستيراد لا يحتوي على الأعمدة المطلوبة بالعربية.', 'danger')
                return redirect(url_for('import_data'))

            conn = get_db_connection()
            new_count = 0
            duplicate_count = 0
            for _, row in df.iterrows():
                numera = str(row['النمرة'])
                # التحقق من وجود النمرة مسبقاً
                existing = conn.execute('SELECT id FROM employees WHERE numera = ?', (numera,)).fetchone()
                if existing:
                    duplicate_count += 1
                    continue
                # إدراج جديد
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
    app.run(debug=True, host='localhost', port=81)