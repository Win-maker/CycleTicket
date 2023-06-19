from flask import Flask, render_template,redirect,request,session,Response,jsonify
from flask_sqlalchemy import SQLAlchemy
from constants import price
from sqlalchemy import LargeBinary
import base64
from img2txt import extract_data
from PIL import Image
from io import BytesIO
import json
# app
app = Flask(__name__)
app.secret_key = 'win'

# database
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:toor@localhost:5432/CircleTicket"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
app.app_context().push()

# create table
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False) 

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id= db.Column(db.Integer, nullable=False)
    user_name= db.Column(db.String(100), nullable=False) 
    ticket = db.Column(db.String(1000), nullable= False)
    img = db.Column(db.LargeBinary(), nullable=True)
    verify = db.Column(db.String(30), nullable=False)

db.create_all() 
# route
@app.route('/home')
def home():
    rangeTicket = []
    allTickets = []
    getData = Orders.query.filter(Orders.verify != 'Rejected').all()
    for tickets in getData:
        allTickets.extend(tickets.ticket.split(','))
    for i in range(1, 101):
        rangeTicket.append(f"{i:03}")
    if  session and session['username']:
        validUser = session['username']
    return render_template('home.html', username=validUser, rangeTicket=rangeTicket, allTickets = allTickets)

@app.route('/', methods=['POST','GET'])
def signup(): 
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        user=Users(username=username,password=password)
        db.session.add(user)
        db.session.commit()
        return render_template('login.html')
    return render_template('signup.html')

@app.route('/login', methods=['POST','GET'])
def login(): 
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        if username == 'winwinhtet' and password == '123':
            return redirect('/adminlogin')
        else:
            loginUser = Users.query.filter(Users.username == username, Users.password == password).first()
            if loginUser:
                session['username'] = loginUser.username
                return redirect('/home')
    return render_template('login.html')

@app.route('/adminlogin', methods=['POST','GET'])
def adminlogin(): 
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        session['username'] = username
        validUser = session['username']
        if username == 'winwinhtet' and password == '123':
            order_tickets = []
            getAllOrderData = Orders.query.order_by(Orders.id.desc()).all()
            for order in getAllOrderData:
                if order.img:
                    byteImg = BytesIO(order.img)
                    readImg = Image.open(byteImg)
                    paymentInfo = extract_data(readImg)
                    order.img = base64.b64encode(order.img).decode('utf-8')
                    dict_order = order.__dict__
                    dict_order.update({'payment':paymentInfo})
                    order_tickets.append(dict_order)
            return render_template('admindashboard.html',order_tickets=order_tickets,username=validUser)  
    return render_template('adminlogin.html')


@app.route('/ticket_order', methods=['POST', 'GET'])
def ticket_order():
    if request.method == 'POST':
        form_selected_tickets = request.form.getlist("ticket[]") 
        total = len(form_selected_tickets)*price
        if len(form_selected_tickets):
            selected_ticket = ''
            for ticket in form_selected_tickets:
                if selected_ticket:
                    selected_ticket += ','
                selected_ticket += ticket
            if "username" in session:
                validUser = session['username']
                user = Users.query.filter_by(username=validUser).first()
                validUserId = user.id
                if validUserId:
                    orders = {}
                    orders = {'user_id':validUserId, 'user_name':validUser, 'ticket':selected_ticket}
                    json_orders = json.dumps(orders)
                    session['orders']=json_orders
                    print(session['orders'])
                    return render_template('order.html', tickets=form_selected_tickets,
                                                        price=price,username=validUser,total=total)
                else:
                    return redirect('/ticket_order')
                            
            else:
                return redirect('/login') 
        else:
            return redirect('/login')       
    else:
        return 'error'           
                    

@app.route('/payment', methods=['POST'])
def payment():
    if request.method == 'POST':
        image_file = request.files['image']
        getDataFromSession = session['orders']
        getDataFromSession = json.loads(getDataFromSession)
        newOrder=Orders(user_name=getDataFromSession['user_name'], user_id=getDataFromSession['user_id'],
                        img=image_file.read(),ticket=getDataFromSession['ticket'],verify="Pending")
        db.session.add(newOrder)
        db.session.commit()
        session.pop('orders',False)
        return redirect('/userOrderList')
    else:
        return render_template('signup.html')
        
@app.route('/userOrderList', methods=['POST','GET'])
def userOrderList():
    order_tickets = []
    if session and session['username']:
        getData = Users.query.filter_by(username = session['username']).first()
        getAllOrderData = Orders.query.filter_by(user_id = getData.id)
    for order in getAllOrderData:
        if order.img:
            byteImg = BytesIO(order.img)
            readImg = Image.open(byteImg)
            paymentInfo = extract_data(readImg)
            order.img = base64.b64encode(order.img).decode('utf-8')
            dict_order = order.__dict__
            dict_order.update({'payment':paymentInfo})
            order_tickets.append(dict_order)
        if session and session['username']:
            validUser = session['username']
    return render_template('userOrderList.html', order_tickets=order_tickets,username=validUser)

@app.route('/submit/<int:id>', methods=['POST'])
def submit(id):
    order_tickets = []
    getData = Orders.query.filter_by(id=id).first()
    getData.verify = 'Accepted'
    db.session.commit()
    getAllOrderData = Orders.query.order_by(Orders.id.desc()).all()
    if session and session['username']:
        validUser = session['username']
    for order in getAllOrderData:
        if order.img:
            byteImg = BytesIO(order.img)
            readImg = Image.open(byteImg)
            paymentInfo = extract_data(readImg)
            order.img = base64.b64encode(order.img).decode('utf-8')
            dict_order = order.__dict__
            dict_order.update({'payment':paymentInfo})
            order_tickets.append(dict_order)
    return render_template('admindashboard.html',order_tickets = order_tickets, username=validUser)
    

@app.route('/admindelete/<int:id>', methods=['POST'])
def admindelete(id):
    getData = Orders.query.filter_by(id=id).first()
    getData.verify = 'Rejected'
    db.session.commit()
    if session and session['username']:
        validUser = session['username']
    order_tickets = []
    getAllOrderData = Orders.query.order_by(Orders.id.desc()).all()
    for order in getAllOrderData:
        if order.img:
            byteImg = BytesIO(order.img)
            readImg = Image.open(byteImg)
            paymentInfo = extract_data(readImg)
            order.img = base64.b64encode(order.img).decode('utf-8')
            dict_order = order.__dict__
            dict_order.update({'payment':paymentInfo})
            order_tickets.append(dict_order)
    return render_template('admindashboard.html',order_tickets=order_tickets,username=validUser)
    
         

@app.route('/logout', methods=['POST','GET'])
def logout(): 
    session.pop('username', False)
    return render_template('home.html')


if __name__ == "__main__":
    app.run(debug=True)

# photo = Photo.query.get(photo_id)    
# return send_file(BytesIO(photo.data), attachment_filename=photo.filename, mimetype='image/jpeg')
