from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import io
import uuid
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here' # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///iot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login Manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    districts = db.relationship('District', backref='region', lazy=True)

class District(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=False)
    devices = db.relationship('Device', backref='district', lazy=True)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False) # Custom ID
    name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    token = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=False)
    district_id = db.Column(db.Integer, db.ForeignKey('district.id'), nullable=False)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and default user
with app.app_context():
    db.create_all()
    
    # Create or update the specific user
    target_username = 'Hydrosensor'
    target_password = 'DiliAble'
    
    user = User.query.filter_by(username=target_username).first()
    if not user:
        print(f"Creating user: {target_username}")
        user = User(username=target_username)
        user.set_password(target_password)
        db.session.add(user)
        db.session.commit()
    else:
        # Ensure password is correct even if user exists
        print(f"Updating password for user: {target_username}")
        user.set_password(target_password)
        db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        print(f"Login attempt for: {username}") # Debug print
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            if user.check_password(password):
                print("Password correct, logging in...")
                login_user(user, remember=True)
                return redirect(url_for('index'))
            else:
                print("Password incorrect")
                flash('Parol noto\'g\'ri')
        else:
            print("User not found")
            flash('Bunday foydalanuvchi topilmadi')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    regions = Region.query.all()
    devices = Device.query.all()
    total_devices = len(devices)
    active_devices = Device.query.filter_by(is_active=True).count()
    return render_template('index.html', regions=regions, total_devices=total_devices, active_devices=active_devices)

@app.route('/api/districts/<int:region_id>')
@login_required
def get_districts(region_id):
    districts = District.query.filter_by(region_id=region_id).all()
    return jsonify([{'id': d.id, 'name': d.name} for d in districts])

@app.route('/api/devices')
@login_required
def get_devices():
    region_id = request.args.get('region_id')
    district_id = request.args.get('district_id')
    
    query = Device.query
    if region_id:
        query = query.filter_by(region_id=region_id)
    if district_id:
        query = query.filter_by(district_id=district_id)
        
    devices = query.all()
    device_list = []
    for d in devices:
        region = Region.query.get(d.region_id)
        district = District.query.get(d.district_id)
        device_list.append({
            'id': d.id,
            'device_id': d.device_id,
            'name': d.name,
            'lat': d.latitude,
            'lng': d.longitude,
            'token': d.token,
            'region': region.name if region else '',
            'district': district.name if district else '',
            'is_active': d.is_active
        })
    return jsonify(device_list)

@app.route('/add_region', methods=['POST'])
@login_required
def add_region():
    name = request.form.get('name')
    if name:
        if not Region.query.filter_by(name=name).first():
            db.session.add(Region(name=name))
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_district', methods=['POST'])
@login_required
def add_district():
    name = request.form.get('name')
    region_id = request.form.get('region_id')
    if name and region_id:
        db.session.add(District(name=name, region_id=region_id))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_device', methods=['POST'])
@login_required
def add_device():
    device_id = request.form.get('device_id')
    name = request.form.get('name')
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    region_id = request.form.get('region_id')
    district_id = request.form.get('district_id')
    
    if device_id and name and region_id and district_id:
        new_device = Device(
            device_id=device_id,
            name=name,
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            region_id=region_id,
            district_id=district_id
        )
        db.session.add(new_device)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_device/<int:id>', methods=['POST'])
@login_required
def edit_device(id):
    device = Device.query.get_or_404(id)
    device.name = request.form.get('name')
    device.device_id = request.form.get('device_id')
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    device.latitude = float(lat) if lat else None
    device.longitude = float(lng) if lng else None
    device.region_id = request.form.get('region_id')
    device.district_id = request.form.get('district_id')
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_device/<int:id>')
@login_required
def delete_device(id):
    device = Device.query.get_or_404(id)
    db.session.delete(device)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/export_excel')
@login_required
def export_excel():
    devices = Device.query.all()
    data = []
    for d in devices:
        region = Region.query.get(d.region_id)
        district = District.query.get(d.district_id)
        data.append({
            'ID': d.device_id,
            'Name': d.name,
            'Region': region.name if region else '',
            'District': district.name if district else '',
            'Latitude': d.latitude,
            'Longitude': d.longitude,
            'Token': d.token,
            'Active': 'Yes' if d.is_active else 'No'
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Devices')
    output.seek(0)
    
    return send_file(output, download_name='devices.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
