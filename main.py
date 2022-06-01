from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import qrcode
import cv2 as cv
import random
import os
from datetime import datetime
from functools import wraps


# admin decorator function
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


# letters for creating random wifi password
letters = [
           'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
           'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'
           'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
]

# menu
menu = {'iced coffee': '$2.25', 'cafe au lait': '$2.70', 'machiato': '$3.90', 'espresso': '$2.70',
        'double espresso': '$2.90', 'cafe latte': '$2.75', 'mocha': '$3.50', 'cappuccino': '$1.47',
        'americano': '$2.62', 'kona coffee': '$10.00', 'jamaica blue mountain coffee': '$25.00'}

all_passwords = []
opening_hour = 9
if datetime.now().hour < opening_hour:
    all_passwords.clear()
    path = 'C:/Users/GREATFAITH CHURCH/Desktop/python/pro projects/cafe-wifi website/static/qrcodes/'
    filelist = [file for file in os.listdir(path) if file.endswith('.png')]
    for files in filelist:
        os.remove(os.path.join(path, files))
else:
    pass


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hailmarymotherofgrace'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

QR_FOLDER = os.path.join('static', 'qrcodes')
app.config['UPLOAD_FOLDER'] = QR_FOLDER


login_manager = LoginManager()
login_manager.init_app(app)


class Users(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=False, nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(100))

class Blacklisted(db.Model):
    __tablename__ = 'blacklisted_users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250))

db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def home():
    logged_in = request.args.get('logged_in')
    username = request.args.get('name')
    
    if request.method == 'POST':
        name = request.form.get('name').lower()
        order = request.form.get('order').lower()
        table_num = request.form.get('tableNumber').lower()
        qty = request.form.get('amount').lower()
        
        if order in menu:
            with open('customer_order.txt', 'w') as receipt:
                receipt.write(f'Customer: {name}\n'
                              f'Order: {order}\n'
                              f'Table Number: {table_num}\n'
                              f'Quantity: {qty}\n'
                              f'Price: {menu[order]}.')
                
            wifi_password = ''
            for x in range(8):
                let = random.choice(letters)
                wifi_password += let
            all_passwords.append(wifi_password)
            
            # QR Code creation
            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                border=4
            )
            qr.add_data(wifi_password)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            img.save(
                f'C:/Users/GREATFAITH CHURCH/Desktop/python/pro projects/cafe-wifi website/static/qrcodes/{wifi_password}.png')
            
            filename = os.path.join(app.config['UPLOAD_FOLDER'], f'{wifi_password}.png')
            return redirect(url_for('qr_code', file=filename, fn=wifi_password))
        else:
            error = 'Your Order is not in our menu. Please go back and kindly pick an option from the menu'
            return redirect(url_for('error', error=error))

    return render_template('index.html', logged_in=logged_in, username=username, current_user=current_user)


@app.route('/qr')
@login_required
def qr_code():
    qr_code = request.args.get('file')
    qr_pin = request.args.get('fn')
    return render_template('qr.html', file=qr_code, fn=qr_pin, logged_in=True)


@app.route('/signup', methods=['GET', 'POST'])
def sign_up():
    error = request.args.get('error')
    all_users = db.session.query(Users).all()
    black_list = db.session.query(Blacklisted).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password_again = request.form.get('password_again')
        
        verified_user = Users.query.filter_by(email=email).first()
        blacklisted_user = Blacklisted.query.filter_by(email=email).first()
        
        if blacklisted_user in black_list:
            error = 'your email address has been banned from this website'.title()
            return redirect(url_for('sign_up', error=error))
        
        if verified_user in all_users:
            error = 'you already have an account. Login instead'.title()
            return redirect(url_for('login', error=error))
        else:
            if password == password_again:
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=9)
                new_user = Users(name=name,
                                 email=email,
                                 password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('login'))
            else:
                error = 'incorrect passwords'
                return redirect(url_for('sign_up', error=error))
    return render_template('signup.html', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error')
    all_users = db.session.query(Users).all()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        verified_user = Users.query.filter_by(email=email).first()
        
        if verified_user in all_users:
            checked_password = check_password_hash(verified_user.password, password)
            
            if checked_password:
                login_user(verified_user)
                return redirect(url_for('home', logged_in=current_user.is_authenticated, name=verified_user.name))
            else:
                error = 'wrong password'
                return redirect(url_for('login', error=error))
            
        else:
            error = 'wrong email address'
            return redirect(url_for('login', error=error))
        
    return render_template('login.html', error=error)


@app.route('/password')
@login_required
def password():
    file = request.args.get('file')
    im = cv.imread(
        f'C:/Users/GREATFAITH CHURCH/Desktop/python/pro projects/cafe-wifi website/static/qrcodes/{file}.png'
    )
    det = cv.QRCodeDetector()
    retval, points, straight_qrcode = det.detectAndDecode(im)
    return render_template('pass.html', password=retval, logged_in=True)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/delete', methods=['GET', 'POST'])
@login_required
@admin_only
def delete():
    message = request.args.get('message')
    all_users = db.session.query(Users).all()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        verified_user = Users.query.filter_by(email=email).first()
        admin = Users.query.filter_by(email='admin@email.com').first()
        
        if verified_user in all_users:
            check_password = check_password_hash(admin.password, password)
            
            if check_password:
                black_listed_user = Blacklisted(email=email)
                db.session.add(black_listed_user)
                db.session.commit()
                
                db.session.delete(verified_user)
                db.session.commit()
                message = 'User successfully deleted'
                return redirect(url_for('delete', message=message))
            else:
                message = 'wrong password'
                return redirect(url_for('delete', message=message))
            
        else:
            message = 'That user does not exist in the database'
            return redirect(url_for('delete', message=message))
        
    return render_template('admin.html', message=message)


@app.route('/error')
@login_required
def error():
    error = request.args.get('error')
    return render_template('error.html', error=error)


if __name__ == '__main__':
    app.run(debug=True)
