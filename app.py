from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from datetime import timedelta, datetime
import os
from dotenv import load_dotenv
from flask_mail import Mail, Message
import secrets

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='../build', static_url_path='/')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')  # Change in production
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', 'yes', '1')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
mail = Mail(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"User('{self.email}')"

# Create database tables
@app.before_first_request
def create_tables():
    db.create_all()

# Routes
@app.route('/api/auth/signin', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Please provide email and password'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        'message': 'Sign in successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email
        }
    }), 200

@app.route('/api/auth/signup', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Please provide email and password'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists'}), 400
    
    # Hash password
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # Create new user
    new_user = User(email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(identity=new_user.id)
    
    return jsonify({
        'message': 'User created successfully',
        'access_token': access_token,
        'user': {
            'id': new_user.id,
            'email': new_user.email
        }
    }), 201

@app.route('/api/user/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'created_at': user.created_at
    }), 200

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password_request():
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'message': 'Please provide an email'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    # Generate token even if user doesn't exist (for security)
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=1)
    
    # If user exists, save the token
    if user:
        user.reset_token = token
        user.reset_token_expiry = expiry
        db.session.commit()
        
        # Email the reset link
        reset_url = f"{request.host_url.rstrip('/')}/reset-password/{token}"
        try:
            msg = Message("Password Reset Request", recipients=[user.email])
            msg.body = f"""To reset your password, visit the following link:
            
{reset_url}

This link is valid for 1 hour.

If you did not make this request, please ignore this email.
"""
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Failed to send email: {str(e)}")
    
    # Always return success for security (don't leak info about existing emails)
    return jsonify({'message': 'Password reset instructions sent if email exists'}), 200

@app.route('/api/auth/reset-password/<token>', methods=['POST'])
def reset_password_with_token(token):
    data = request.get_json()
    
    if not data or not data.get('password'):
        return jsonify({'message': 'Please provide a new password'}), 400
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or user.reset_token_expiry < datetime.now():
        return jsonify({'message': 'Invalid or expired reset token'}), 401
    
    # Hash new password and save
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user.password = hashed_password
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    
    return jsonify({'message': 'Password updated successfully'}), 200

# Catch-all route to serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return app.send_static_file(path)
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)