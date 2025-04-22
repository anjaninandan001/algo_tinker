import smtplib
import os
import random
import string
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import session

# Store verification codes temporarily
VERIFICATION_CODES = {}
USER_DATA_FILE = 'data/users.json'

# Ensure users file exists
os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_users():
    """Load users from JSON file"""
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """Save users to JSON file"""
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code):
    """Send verification email with code"""
    # Get email credentials from environment
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    
    if not smtp_user or not smtp_password:
        # Use a simulated email for development
        print(f"DEVELOPMENT MODE: Verification code for {email} is {code}")
        return True
        
    # Create email message
    message = MIMEMultipart()
    message['From'] = smtp_user
    message['To'] = email
    message['Subject'] = 'AlgoBlocks Verification Code'
    
    # Email body
    body = f"""
    <html>
    <body>
        <h2>AlgoBlocks Verification Code</h2>
        <p>Your verification code is: <strong>{code}</strong></p>
        <p>This code will expire in 10 minutes.</p>
    </body>
    </html>
    """
    message.attach(MIMEText(body, 'html'))
    
    try:
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def register_user(email, password, username):
    """Register a new user"""
    users = load_users()
    if email in users:
        return False, "Email already registered"
        
    # Generate verification code
    code = generate_verification_code()
    VERIFICATION_CODES[email] = code
    
    # Send verification email
    if send_verification_email(email, code):
        # Store user details temporarily
        users[email] = {
            'username': username,
            'password': password,  # In production, use password hashing!
            'verified': False,
            'portfolio': {
                'cash': 10000.00,
                'trades': []
            }
        }
        save_users(users)
        return True, "Verification email sent"
    else:
        return False, "Failed to send verification email"

def verify_user(email, code):
    """Verify a user's email"""
    if email not in VERIFICATION_CODES or VERIFICATION_CODES[email] != code:
        return False, "Invalid verification code"
        
    users = load_users()
    if email in users:
        users[email]['verified'] = True
        save_users(users)
        
        # Clean up verification code
        del VERIFICATION_CODES[email]
        
        return True, "Email verified successfully"
    else:
        return False, "User not found"

def login_user(email, password):
    """Log in a user"""
    users = load_users()
    if email not in users:
        return False, "Email not registered"
        
    user = users[email]
    if not user['verified']:
        return False, "Email not verified"
        
    if user['password'] != password:  # In production, use password verification!
        return False, "Incorrect password"
        
    # Set session data
    session['user_email'] = email
    session['username'] = user['username']
    
    return True, "Login successful"

def logout_user():
    """Log out a user"""
    session.pop('user_email', None)
    session.pop('username', None)
    return True, "Logout successful"
