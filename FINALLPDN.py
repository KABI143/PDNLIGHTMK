import RPi.GPIO as GPIO
from datetime import datetime, timedelta
from flask import Flask, flash, request, render_template, jsonify, redirect, url_for
import os
import time
import secrets
from traceback import format_exc

app = Flask(__name__)
secret_key = secrets.token_hex(16)

# Set it as the Flask app's secret key
app.secret_key = secret_key

GPIO.setmode(GPIO.BCM)

# Configuration
LIGHT_PIN = 17  # GPIO pin connected to the relay module
BUFFER_TIME = 10  # Buffer time in seconds

# Simulated user roles (admin and user)
users = {
    'admin': {
        'username': 'admin',
        'role': 'admin',
        'password': 'admin',
    },
    'user': {
        'username': 'user',
        'role': 'user',
        'password': '123',
    },
}

# Global variables
current_user = None
time_on = None
time_off = None

# Text file path
TIME_FILE_PATH = 'last_set_times.txt'

# Helper functions
def save_last_set_times():
    with open(TIME_FILE_PATH, 'w') as file:
        file.write(f'{time_on},{time_off}')

def read_last_set_times():
    try:
        with open(TIME_FILE_PATH, 'r') as file:
            content = file.read()
            if content:
                return content.split(',')
    except FileNotFoundError:
        pass
    return None, None

def setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LIGHT_PIN, GPIO.OUT)
    GPIO.output(LIGHT_PIN, GPIO.LOW)

def turn_on_light():
    print("Turning the light ON")
    GPIO.output(LIGHT_PIN, GPIO.HIGH)

def turn_off_light():
    print("Turning the light OFF")
    GPIO.output(LIGHT_PIN, GPIO.LOW)

def is_authenticated(username, password):
    return username in users and users[username]['password'] == password

def is_admin():
    return current_user and current_user['role'] == 'admin'

def is_user():
    return current_user and current_user['role'] == 'user'

# Flask routes
@app.route('/')
def index():
    global time_on, time_off
    return render_template('login.html', time_on=time_on, time_off=time_off)

@app.route('/set_times', methods=['GET', 'POST'])
def set_times():
    global time_on, time_off
    if current_user and current_user['role'] == 'admin':
        try:
            if request.method == 'POST':
                global time_on, time_off  # Declare as global
                time_on = request.form['time_on']
                time_off = request.form['time_off']
                save_last_set_times()
                flash('Times updated successfully', 'success')

                # Redirect to the set_times route instead of rendering the template directly
                return redirect(url_for('set_times'))

            return render_template('set.html', time_on=time_on, time_off=time_off,alert_message="Time set successfully!")
        except Exception as e:
            print(f"Error in set_times route: {e}")
            print(format_exc())
            flash('An error occurred while updating times', 'error')

            # Redirect to the set_times route in case of an error
            return redirect(url_for('set_times'))
    else:
        return redirect(url_for('show_times'))


@app.route('/get_light_state')
def get_light_state():
    if current_user:
        light_state = GPIO.input(LIGHT_PIN)
        return jsonify({'light_state': light_state})
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global current_user, time_on, time_off
    login_message = ""

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if is_authenticated(username, password):
            current_user = users[username]

            if is_admin():
                return redirect(url_for('set_times'))
            else:
                return redirect(url_for('show_times'))

        login_message = "Incorrect username or password. Please try again."

    if current_user:
        if is_admin():
            return redirect(url_for('set_times'))
        else:
            return redirect(url_for('show_times'))

    return render_template('login.html', login_message=login_message)

@app.route('/show_times')
def show_times():
    if current_user:
        return render_template('show_times.html', time_on=time_on, time_off=time_off)
    else:
        return redirect(url_for('login'))

# Main function
def check_time():
    global time_on, time_off
    while True:
        time_on, time_off = read_last_set_times()

        current_time = datetime.now().strftime("%H:%M")

        if time_on and time_off and time_on is not None and time_off is not None:
            time_on_dt = datetime.strptime(time_on, "%H:%M")
            time_off_dt = datetime.strptime(time_off, "%H:%M")
            buffer_time = timedelta(seconds=BUFFER_TIME)

            current_time_dt = datetime.strptime(current_time, "%H:%M")

            if time_on_dt - buffer_time <= current_time_dt <= time_off_dt + buffer_time:
                turn_on_light()
            else:
                turn_off_light()

        # Check the time every minute
        time.sleep(10)

# Application setup and run
if __name__ == "__main__":
    setup()
    try:
        import threading
        t = threading.Thread(target=check_time)
        t.start()
        app.run(host='0.0.0.0', port=5001)
    except KeyboardInterrupt:
        GPIO.cleanup()
