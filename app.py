from flask import Flask, render_template, request, redirect, flash, session
import random, smtplib, json, os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

app = Flask(__name__)
app.secret_key = "emergency_rwanda_2024_final"

# EMAIL CONFIG
SENDER_EMAIL = "salomongusenga25@gmail.com"
SENDER_APP_PASSWORD = "jukfkqbalhkhuxzx"

# ===== ROOMS DEFINITION =====
TOP_ROOM = ["Top Admin", "Mayor", "RDF", "Police", "RIB", "DASSO Coordinator"]
MIDDLE_ROOM = ["Sector Executive"]
LAST_ROOM = ["DASSO Member", "Cell Executive", "SEDO"]
GUEST_ROOM = ["Guest", "Trusted Informer"]
ALLOWED_SELF_REGISTER = MIDDLE_ROOM + LAST_ROOM + GUEST_ROOM

USERS_FILE = 'users.json'
REPORTS_FILE = 'reports.json'

def load_data():
    global USERS, REPORTS
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                USERS = json.load(f)
        except: pass
    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, 'r') as f:
                REPORTS = json.load(f)
        except: pass

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(USERS, f, indent=2)

def save_reports():
    with open(REPORTS_FILE, 'w') as f:
        json.dump(REPORTS, f, indent=2)

USERS = {
    "salomongusenga25@gmail.com": {
        "password": "admin123",
        "name": "Salomon Gusenga",
        "phone": "0780000000",
        "role": "Top Admin",
        "room": "TOP_ROOM",
        "status": "approved"
    }
}
REPORTS = []
load_data()

def send_otp_email(to_email, otp_code):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"ERS Rwanda <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"ERS Code: {otp_code}"
        body = f"""Murakaza neza!

Code yawe ni: {otp_code}
Izamara iminota 5 gusa.

ERS Team - Rwanda Secure & Fast"""
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            flash("Banza winjire!", "danger")
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def top_room_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        user = USERS.get(session['user'])
        if not user or user['room']!= 'TOP_ROOM':
            flash("❌ Nta burenganzira! TOP ROOM gusa ibona Dashboard.", "danger")
            return redirect('/report')
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    if 'user' in session:
        user = USERS.get(session['user'])
        if user and user['room'] == 'TOP_ROOM':
            return redirect('/dashboard')
        else:
            return redirect('/report')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        if email in USERS:
            user = USERS[email]
            if user['status']!= 'approved':
                flash("⏳ Account yawe iracyasuzumwa na Top Admin!", "warning")
                return render_template('login.html')
            if user['password'] == password:
                otp_code = str(random.randint(100000, 999999))
                session['otp_code'] = otp_code
                session['otp_expire'] = (datetime.now() + timedelta(minutes=5)).isoformat()
                session['temp_email'] = email
                session['temp_name'] = user['name']
                session['temp_role'] = user['role']
                session['temp_room'] = user['room']
                sent = send_otp_email(email, otp_code)
                if sent:
                    flash(f"✅ Code yoherejwe kuri {email}!", "success")
                else:
                    flash(f"Demo Code: {otp_code} (Email failed)", "warning")
                return redirect('/verify')
        flash("❌ Email cyangwa Password siyo!", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip().lower()
        phone = request.form.get('phone').strip()
        password = request.form.get('password')
        role = request.form.get('role').strip()
        if email in USERS:
            flash("❌ Uyu email usanzwe uhari!", "danger")
            return render_template('signup.html', allowed_roles=ALLOWED_SELF_REGISTER)
        if role in TOP_ROOM:
            flash("❌ NTABWO wemerewe kwiyandikisha nka Police/Mayor/RDF/RIB! Saba Top Admin.", "danger")
            return render_template('signup.html', allowed_roles=ALLOWED_SELF_REGISTER)
        if role in MIDDLE_ROOM:
            room = "MIDDLE_ROOM"
        elif role in LAST_ROOM:
            room = "LAST_ROOM"
        else:
            room = "GUEST_ROOM"
        USERS[email] = {
            "password": password,
            "name": username,
            "phone": phone,
            "role": role,
            "room": room,
            "status": "pending"
        }
        save_users()
        flash(f"✅ Gusaba byoherejwe! Role: {role} - Tegereza Top Admin.", "success")
        return redirect('/login')
    return render_template('signup.html', allowed_roles=ALLOWED_SELF_REGISTER)

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'otp_code' not in session:
        return redirect('/login')
    if request.method == 'POST':
        entered = request.form.get('otp').strip()
        expire_time = datetime.fromisoformat(session.get('otp_expire'))
        if datetime.now() > expire_time:
            flash("⏰ Code yarangiye!", "danger")
            session.pop('otp_code', None)
            return redirect('/login')
        if entered == session.get('otp_code'):
            session['user'] = session.get('temp_email')
            session['user_name'] = session.get('temp_name')
            session['user_role'] = session.get('temp_role')
            session['user_room'] = session.get('temp_room')
            session.pop('otp_code', None)
            session.pop('otp_expire', None)
            session.pop('temp_email', None)
            session.pop('temp_name', None)
            session.pop('temp_role', None)
            session.pop('temp_room', None)
            if session['user_room'] == 'TOP_ROOM':
                flash(f"Murakaza neza {session['user_name']}! Role: {session['user_role']}", "success")
                return redirect('/dashboard')
            else:
                flash(f"Murakaza neza {session['user_name']}! Ushobora gutanga report.", "success")
                return redirect('/report')
        else:
            flash("❌ Code siyo!", "danger")
    return render_template('verify.html')

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        incident_type = request.form.get('incident_type')
        description = request.form.get('description')
        phone = request.form.get('phone')
        location = request.form.get('location', 'Kigali')
        new_report = {
            "id": f"ER-{len(REPORTS)+1125}",
            "type": incident_type,
            "emergency_type": incident_type,
            "desc": description,
            "description": description,
            "phone": phone,
            "location": location,
            "reporter": session['user'],
            "reporter_name": session['user_name'],
            "reporter_role": session['user_role'],
            "role": session['user_role'],
            "name": session['user_name'],
            "status": "pending",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        REPORTS.append(new_report)
        save_reports()
        flash("✅ Report yoherejwe neza!", "success")
        return redirect('/report')
    user = USERS.get(session['user'])
    return render_template('report.html', user=user, user_name=session.get('user_name'), user_role=session.get('user_role'))

@app.route('/dashboard')
@top_room_required
def dashboard():
    pending_users = {k:v for k,v in USERS.items() if v['status'] == 'pending'}
    return render_template('dashboard.html',
                         user_email=session['user'],
                         user_name=session.get('user_name', 'Admin'),
                         user_role=session.get('user_role'),
                         user_room=session.get('user_room'),
                         reports=REPORTS,
                         users=USERS,
                         pending_users=pending_users)

@app.route('/reports')
@top_room_required
def all_reports():
    pending_users = {k:v for k,v in USERS.items() if v['status'] == 'pending'}
    return render_template('dashboard.html',
                         user_email=session['user'],
                         user_name=session.get('user_name'),
                         user_role=session.get('user_role'),
                         user_room=session.get('user_room'),
                         reports=REPORTS,
                         users=USERS,
                         pending_users=pending_users)

@app.route('/approve/<email>')
@top_room_required
def approve_user(email):
    email = email.lower()
    if email in USERS:
        USERS[email]['status'] = 'approved'
        save_users()
        flash(f"✅ {USERS[email]['name']} ({USERS[email]['role']}) yemejwe!", "success")
    return redirect('/dashboard')

@app.route('/reject/<email>')
@top_room_required
def reject_user(email):
    email = email.lower()
    if email in USERS and email!= "salomongusenga25@gmail.com":
        del USERS[email]
        save_users()
        flash(f"❌ User yahakanye.", "danger")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    flash("Usohotse neza!", "success")
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)