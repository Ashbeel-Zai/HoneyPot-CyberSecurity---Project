#libraries
import logging 
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for
from send_to_api import send_to_api

# Logging Format
logging_format = logging.Formatter('%(asctime)s  %(message)s')

# HTTP logger
funnel_logger = logging.getLogger('HTTP_Logger')
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler('http_audits.log', maxBytes=2000, backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)

# Baseline honeypot

def web_honeypot(input_username="admin", input_password="password123"):
    
    app = Flask(__name__)

    @app.route('/')

    def index():
        return render_template('web_login.html')
    
    @app.route('/admin', methods=['POST'])

    def login():
        username = request.form.get('username')
        password = request.form.get('password')

        ip_address = request.remote_addr
        funnel_logger.info(f"HTTP Login Attempt - IP: {ip_address} | Username: {username} | Password: {password}")
        send_to_api({"event": "login","protocol": "HTTP","ip": ip_address,"username": username,"password": password,"command": None,"session_id": None})

        if username == input_username and password == input_password:
            return '<h1>Welcome to the Honey Dashboard</h1>'
        else:
            return '<h1>Invalid Credentials</h1>'
        
    return app


def run_web_honeypot(port=5000,input_username="admin", input_password="password123"):
    run_web_honeypot_app = web_honeypot(input_username, input_password)
    run_web_honeypot_app.run(debug=True, port=port, host="0.0.0.0")

    return run_web_honeypot_app

    