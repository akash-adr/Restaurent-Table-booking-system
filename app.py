from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "super_secret_key"

DATABASE = "database.db"

# ===============================
# EMAIL CONFIG
# ===============================

SENDER_EMAIL = "culinarycrown.official@gmail.com"
APP_PASSWORD = "hbeuvdvwokowxleo"
BASE_URL = "http://127.0.0.1:5000"

# ===============================
# EMAIL SENDER
# ===============================

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print("Email failed:", e)

# ===============================
# EMAIL TEMPLATES
# ===============================

def send_confirmation_email(to_email, name, date, guests, seating, phone, booking_id):
    manage_link = f"{BASE_URL}/manage-booking/{booking_id}"

    subject = "Reservation Confirmed: Your table at Culinary Crown awaits!"
    body = f"""
Dear {name},

We are delighted to confirm your upcoming dining experience with us.

Reservation Details
-------------------
Date: {date}
Number of Guests: {guests}
Seating Preference: {seating}
Contact Phone: {phone}

Manage your booking:
{manage_link}

Please arrive 10 minutes early.

Warm regards,
The Culinary Crown Team
"""
    send_email(to_email, subject, body)


def send_user_cancellation_email(to_email, name, date, guests, seating):
    subject = "Cancellation Confirmed - Culinary Crown"
    body = f"""
Dear {name},

We are writing to confirm that your reservation for {date} has been cancelled as requested.

Cancelled Details:
Date: {date}
Guests: {guests}
Seating: {seating}

We hope to welcome you very soon!

Best regards,
The Culinary Crown Team
"""
    send_email(to_email, subject, body)


def send_admin_cancellation_email(to_email, name, date, time):
    subject = "Important: Regarding your reservation at Culinary Crown"
    body = f"""
Dear {name},

We sincerely apologize regarding your reservation on {date} at {time}.

Due to unforeseen circumstances, we are unable to fulfill your booking.

We would love to:
• Reschedule your booking
• Offer a complimentary drink/appetizer on your next visit

Warmly,
Admin
Culinary Crown
"""
    send_email(to_email, subject, body)

# ===============================
# DATABASE
# ===============================

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        branch TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        seating_type TEXT NOT NULL,
        guests INTEGER NOT NULL,
        status TEXT DEFAULT 'Confirmed'
    )
    """)
    conn.commit()
    conn.close()

# ===============================
# USER BOOKING FLOW
# ===============================

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/user-details', methods=['GET', 'POST'])
def user_details():
    if request.method == 'POST':
        session['name'] = request.form.get('name')
        session['email'] = request.form.get('email')
        session['phone'] = request.form.get('phone')
        return redirect(url_for('select_slot'))
    return render_template("user_details.html")


@app.route('/select-slot', methods=['GET', 'POST'])
def select_slot():
    if request.method == 'POST':
        session['branch'] = request.form.get('branch')
        session['date'] = request.form.get('date')
        session['guests'] = int(request.form.get('guests'))
        session['seating_type'] = request.form.get('seating_type')
        session['time'] = request.form.get('time')
        return redirect(url_for('confirmation'))
    return render_template("select_slot.html")


@app.route('/confirmation')
def confirmation():

    if 'name' not in session:
        return redirect(url_for('index'))

    booking_id = str(uuid.uuid4())[:8]

    conn = get_connection()
    conn.execute("""
        INSERT INTO bookings
        (booking_id, name, email, phone, branch, date, time, seating_type, guests)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_id,
        session['name'],
        session['email'],
        session['phone'],
        session['branch'],
        session['date'],
        session['time'],
        session['seating_type'],
        session['guests']
    ))
    conn.commit()
    conn.close()

    send_confirmation_email(
        session['email'],
        session['name'],
        session['date'],
        session['guests'],
        session['seating_type'],
        session['phone'],
        booking_id
    )

    data = dict(session)
    session.clear()

    return render_template("confirmation.html", data=data, booking_id=booking_id)

# ===============================
# MANAGE BOOKING
# ===============================

@app.route('/manage-booking/<booking_id>')
def manage_booking(booking_id):
    conn = get_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,)
    ).fetchone()
    conn.close()

    if not booking:
        return "Invalid Booking ID"

    return render_template("manage_booking.html", booking=booking)


@app.route('/modify-booking/<booking_id>', methods=['GET', 'POST'])
def modify_booking(booking_id):

    conn = get_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return "Invalid Booking ID"

    if request.method == 'POST':

        branch = request.form.get('branch')
        date = request.form.get('date')
        time = request.form.get('time')
        seating_type = request.form.get('seating_type')
        guests = request.form.get('guests')

        if not all([branch, date, time, seating_type, guests]):
            conn.close()
            return "All fields are required"

        conn.execute("""
            UPDATE bookings
            SET branch=?, date=?, time=?, seating_type=?, guests=?
            WHERE booking_id=?
        """, (
            branch,
            date,
            time,
            seating_type,
            int(guests),
            booking_id
        ))
        conn.commit()
        conn.close()

        return redirect(url_for('manage_booking', booking_id=booking_id, updated="true"))

    conn.close()
    return render_template("modify_booking.html", booking=booking)

# ===============================
# USER CANCEL FLOW
# ===============================

@app.route('/cancel-confirm/<booking_id>')
def cancel_confirm_page(booking_id):
    conn = get_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,)
    ).fetchone()
    conn.close()

    if not booking:
        return "Invalid Booking ID"

    return render_template("cancel_confirmation.html", booking=booking)


@app.route('/confirm-cancel/<booking_id>')
def confirm_cancel_booking(booking_id):

    conn = get_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return "Invalid Booking ID"

    conn.execute(
        "UPDATE bookings SET status='Cancelled' WHERE booking_id=?",
        (booking_id,)
    )
    conn.commit()
    conn.close()

    send_user_cancellation_email(
        booking["email"],
        booking["name"],
        booking["date"],
        booking["guests"],
        booking["seating_type"]
    )

    return render_template("cancel_success.html")

# ===============================
# ADMIN ROUTES
# ===============================

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == "admin" and request.form.get('password') == "admin123":
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template("admin/admin_login.html", error="Invalid credentials")
    return render_template("admin/admin_login.html")


@app.route('/admin-dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    bookings = conn.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    cancelled = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Cancelled'").fetchone()[0]
    conn.close()

    return render_template(
        "admin/admin_dashboard.html",
        bookings=bookings,
        total_reservations=total,
        active_reservations=active,
        cancelled_reservations=cancelled
    )


@app.route('/admin-cancel/<booking_id>')
def admin_cancel_booking(booking_id):

    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,)
    ).fetchone()

    if not booking:
        conn.close()
        return "Invalid Booking ID"

    conn.execute(
        "UPDATE bookings SET status='Cancelled' WHERE booking_id=?",
        (booking_id,)
    )
    conn.commit()
    conn.close()

    send_admin_cancellation_email(
        booking["email"],
        booking["name"],
        booking["date"],
        booking["time"]
    )

    return render_template("cancel_success.html")

# ===============================
# RUN APP
# ===============================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)