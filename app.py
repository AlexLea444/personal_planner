from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, datetime
import sqlite3 as sql
# import json
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize SQLite database
conn = sql.connect('users.db', check_same_thread=False)
c = conn.cursor()

# Create users table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )''')


# Create assignments table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                assignment_name TEXT NOT NULL,
                deadline TEXT NOT NULL,
                time_required INTEGER NOT NULL,

                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')
conn.commit()


# Create events table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                event_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                weekly INTEGER NOT NULL,
                final_date TEXT,

                FOREIGN KEY (user_id) REFERENCES users (id)
          )''')


# Create events table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                class_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                days_of_week TEXT NOT NULL,
                final_date TEXT,

                FOREIGN KEY (user_id) REFERENCES users (id)
          )''')


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method != 'POST':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']

    # Check if username and password match
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    if user:
        session['username'] = username
        flash("Login successful")
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html', error='Invalid username or password')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method != 'POST':
        return render_template('signup.html')

    username = request.form['username']
    password = request.form['password']

    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        session['username'] = username
        return redirect(url_for('dashboard'))
    except sql.IntegrityError:
        return render_template('signup.html', error='Username already exists')


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    # Retrieve user ID
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = c.fetchone()[0]

    # Fetch user assignments from the database
    c.execute("SELECT assignment_name, deadline, time_required FROM assignments WHERE user_id=? ORDER BY deadline", (user_id,))
    assignments = c.fetchall()

    # Fetch user events from the database
    c.execute("SELECT event_name, event_date, start_time, end_time, weekly FROM events WHERE user_id=?", (user_id,))
    events = c.fetchall()

    # Fetch user classes from the database
    c.execute("SELECT class_name, days_of_week, start_time, end_time FROM classes WHERE user_id=?", (user_id,))
    classes = c.fetchall()

    try:
        error = request.args['error']
        return render_template('dashboard.html', username=username, assignments=assignments, events=events, classes=classes, error=error)
    except Exception:
        return render_template('dashboard.html', username=username, assignments=assignments, events=events, classes=classes)


@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    assignment_name = request.form['assignment_name']
    deadline = request.form['deadline']
    time_required = 0
    try:
        time_required = int(request.form['time_required'])
    except ValueError:
        return redirect(url_for('dashboard', error="Estimated time (hrs) must be an integer"))

    # Retrieve user ID
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = c.fetchone()[0]

    # Insert assignment into database
    c.execute("INSERT INTO assignments (user_id, assignment_name, deadline, time_required) VALUES (?, ?, ?, ?)", (user_id, assignment_name, deadline, time_required))
    conn.commit()

    if datetime.strptime(deadline, '%Y-%m-%d').date() < date.today():
        return redirect(url_for('dashboard', error="Deadline is passed, assignment considered overdue"))

    return redirect(url_for('dashboard'))


@app.route('/remove_assignment', methods=['POST'])
def remove_assignment():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    assignment_name = request.form['assignment_name']

    # Retrieve user ID
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = c.fetchone()[0]

    # Delete assignment from database
    c.execute("DELETE FROM assignments WHERE user_id=? AND assignment_name=?", (user_id, assignment_name))
    conn.commit()

    return redirect(url_for('dashboard'))


@app.route('/add_event', methods=['POST'])
def add_event():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    event_name = request.form['event_name']
    event_date = request.form['event_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    weekly = 'weekly' in request.form
    final_date = ''
    if weekly and 'final_date' in request.form:
        final_date = request.form['final_date']

    # Retrieve user ID
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = c.fetchone()[0]

    # Insert event into database
    if final_date == '':
        c.execute("INSERT INTO events (user_id, event_name, event_date, start_time, end_time, weekly, final_date) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, event_name, event_date, start_time, end_time, weekly, None))
    else:
        c.execute("INSERT INTO events (user_id, event_name, event_date, start_time, end_time, weekly, final_date) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, event_name, event_date, start_time, end_time, weekly, final_date))
    conn.commit()

    return redirect(url_for('dashboard'))


@app.route('/remove_event', methods=['POST'])
def remove_event():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    event_name = request.form['event_name']

    # Retrieve user ID
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = c.fetchone()[0]

    # Delete assignment from database
    c.execute("DELETE FROM events WHERE user_id=? AND event_name=?", (user_id, event_name))
    conn.commit()

    return redirect(url_for('dashboard'))


@app.route('/add_class', methods=['POST'])
def add_class():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    class_name = request.form['class_name']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    days_of_week = request.form['days_of_week']
    final_date = ''
    if 'final_date' in request.form:
        final_date = request.form['final_date']

    # Retrieve user ID
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user_id = c.fetchone()[0]

    # Insert event into database
    if final_date == '':
        c.execute("INSERT INTO events (user_id, class_name, start_time, end_time, days_of_week, final_date) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, class_name, start_time, end_time, days_of_week, None))
    else:
        c.execute("INSERT INTO events (user_id, event_name, event_date, start_time, end_time, weekly, final_date) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, class_name, start_time, end_time, days_of_week, final_date))
    conn.commit()

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
