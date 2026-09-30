from flask import Flask , render_template , session , request , redirect ,flash
import bcrypt , datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from functools import wraps
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage
load_dotenv()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect("/admin/login")

        return f(*args, **kwargs)

    return decorated_function
    
def login_required(f):
    
    @wraps(f)
    def wrapper(*args , **kwargs):
            if not session.get("ss_id"):
                return redirect("/login")
            return f(*args,**kwargs)
    return wrapper

def send_reminder_email(user, event):

    msg = EmailMessage()

    msg["Subject"] = f"Reminder Set - {event.title}"
    msg["From"] = os.getenv("MAIL_USERNAME")
    msg["To"] = user.email

    msg.set_content(f"""
Hi {user.name},

Your reminder has been set successfully.

Event : {event.title}
Date  : {event.event_date}
Time  : {event.event_time}
Venue : {event.venue}

We hope to see you there!

College Event Manager
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(
            os.getenv("MAIL_USERNAME"),
            os.getenv("MAIL_PASSWORD")
        )

        smtp.send_message(msg)


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]= os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
app.secret_key = os.getenv("SECRET_KEY")

class User(db.Model):
    __tablename__ = "users"

    std_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(30), nullable=False, unique=True)
    u_year = db.Column(db.String(10), nullable=False)
    branch = db.Column(db.String(15), nullable=False)
    roll_no = db.Column(db.Integer, nullable=False)
    fav_cat = db.Column(db.String(20), nullable=True)
    u_pass = db.Column(db.String(255), nullable=False)
    
class Event(db.Model):
    __tablename__ = "events"
    event_id = db.Column(db.Integer ,primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text , nullable=False)
    event_date = db.Column(db.Date , nullable=False)
    event_time = db.Column(db.Time , nullable=False)
    category = db.Column(db.String(30), nullable=False)
    image = db.Column(db.String(255))
    venue = db.Column(db.String(100), nullable=False)
    contact_faculty = db.Column(db.String(100),nullable=False)
    deadline = db.Column(db.Date , nullable=False)
    duration = db.Column(db.String(50),nullable=True)
    
class Reminder(db.Model):
    __tablename__ = "reminders"
    reminder_id = db.Column(db.Integer, primary_key=True)
    std_id = db.Column(db.Integer,db.ForeignKey("users.std_id", ondelete="CASCADE"),nullable=False)
    event_id = db.Column(db.Integer,db.ForeignKey("events.event_id", ondelete="CASCADE"),nullable=False)
    __table_args__ = (db.UniqueConstraint("std_id", "event_id"),)
    event = db.relationship("Event")
    
@app.context_processor
def inject_user():
    userin = session.get("ss_id")
    return {"userin": userin}

@app.route("/")
def home():
    today = datetime.date.today()
    ongoing_events = Event.query.filter(Event.event_date == today).all()
    upcoming_events = Event.query.filter(Event.event_date > today).all()
    past_events = Event.query.filter(Event.event_date < today).all()
    event01 = Event.query.filter_by(category="Hackathon").first()
    event02 = Event.query.filter_by(category="History").first()
    event03 = Event.query.filter_by(category="Workshop").first()
    event04 = Event.query.filter_by(category="Science").first()
    return render_template("home.html" ,ongoing_events=ongoing_events, upcoming_events=upcoming_events,past_events=past_events, event01=event01,event02=event02,event03=event03 , event04=event04 )

@app.route("/events")
def event():
    events = Event.query.all()
    return render_template("alleventpg.html" , events=events)

@app.route("/about")
def aboutus():
    return render_template("about.html")

@app.route("/contact")
def contactus():
    return render_template("contact.html")

@app.route("/signup" , methods=["GET", "POST"])
def signup():
    if request.method =="POST" :
        name = request.form["user_name"]
        email = request.form["user_email"]
        year =  request.form["user_year"]
        branch = request.form["user_branch"]
        rollno = request.form["user_rollno"]
        fcategory = request.form["fav_category"]
        password = request.form["user_pass"]
        cfpass = request.form["conf_pass"]
        
        user = User.query.filter_by(email=email).first()
        if user is None : 
            if password == cfpass:
                hashedpw = bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt()).decode("utf-8")
                
                user = User(
                    name=name,
                    email=email,
                    u_year=year,
                    branch=branch,
                    roll_no=rollno,
                    fav_cat=fcategory,
                    u_pass=hashedpw
                )
                db.session.add(user)
                db.session.commit()
                return redirect("/login")
            else :
                flash("Password Did not matched.")
                return redirect("/signup")
                
        
        else :
            flash("Email is already registered.")
            return redirect("/login")
        
    return render_template("signup.html")

@app.route("/login" , methods=["GET" , "POST"])
def login():
    
    if request.method == "POST":
        rollno = request.form["user_rollno"]
        year =  request.form["user_year"]
        branch = request.form["user_branch"]
        password = request.form["user_pass"]
        user = User.query.filter_by(roll_no=rollno , branch=branch, u_year=year).first()
        if user is None :
            flash("You have not signed Up ")
            return redirect("/signup")
        else :
            if bcrypt.checkpw(password.encode("utf-8") , user.u_pass.encode("utf-8")):
                session["ss_id"] = user.std_id
                return redirect("/")
            else :
                flash("Entered password is Wrong")
                return redirect("/login")
                
    return render_template("login.html")


@app.route("/profile")
@login_required
def profile():
    user = User.query.filter_by(std_id=session["ss_id"]).first()
    reminder = Reminder.query.filter_by(std_id=session["ss_id"]).all()
    return render_template("profile.html",user=user, reminder=reminder)


@app.route("/logout")
@login_required
def logout():
    session.pop("ss_id")
    return redirect("/")

@app.route("/eventpage/<int:event_id>")
@login_required
def eventpage(event_id):
    event = Event.query.get_or_404(event_id)
    reminder = Reminder.query.filter_by(event_id=event_id , std_id=session["ss_id"]).first()
    return render_template("specificevent.html" , event=event ,reminder=reminder)

@app.route("/admin/login" , methods=["POST" , "GET"])
def admin_login():
    if request.method == "POST" :
        email= request.form["admin-email"]
        password = request.form["admin-pass"]
        if email == os.getenv("ADMIN_EMAIL") and password == os.getenv("ADMIN_PASSWORD"):
            session["admin_logged_in"] = True
            return redirect("/admin/dashboard")
        else :
            flash("Email or Password did not matched.")
            return redirect("/admin/login")
        
    return render_template("admin/admin-login.html")

@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.pop("admin_logged_in" , None)
    return redirect("/")
        

@app.route("/admin/dashboard")
@admin_required
def admin():
    today = datetime.date.today()
    events =  Event.query.all()
    total_events=len(events)
    upcoming = 0
    ongoing = 0 
    complete = 0
    for event in events :
        if event.event_date > today:
            upcoming+=1
        elif event.event_date < today:
            complete+=1
        else :
            ongoing+=1
    recent_events = Event.query.order_by(Event.event_id.desc()).limit(3).all()
    
    return render_template("admin/dashboard.html", total_events=total_events , upcoming=upcoming , ongoing=ongoing , complete=complete , recent_events=recent_events)

@app.route("/admin/create-event" ,methods=[ "GET","POST"])
@admin_required
def create_event():
    if request.method == "POST":
        title = request.form["event-name"]
        description = request.form["event-desc"]
        date = datetime.datetime.strptime(request.form["event-date"], "%Y-%m-%d").date()
        time = datetime.datetime.strptime(request.form["event-time"], "%H:%M").time()
        category = request.form["event-cat"]
        image = request.files["event-image"]
        venue = request.form["event-venue"]
        faculty = request.form["event-faculty"]
        deadline = datetime.datetime.strptime(request.form["event-deadline"], "%Y-%m-%d").date()
        duration = request.form["event-duration"]
        filename = secure_filename(image.filename)
        image.save(os.path.join("static/uploads/events" , filename))
        image_path = "uploads/events/" + filename
        
        event = Event(
            title=title,
            description=description,
            event_date=date,
            event_time=time,
            category=category,
            image=image_path,
            venue=venue,
            contact_faculty=faculty,
            deadline=deadline,
            duration=duration
            
        )
        db.session.add(event)
        db.session.commit()
        return redirect("/admin/manage-event")
    
    return render_template("admin/create-event.html")

@app.route("/admin/manage-event")
@admin_required
def manage_event():
    event = Event.query.all()
    return render_template("admin/manage-event.html" ,event=event)

@app.route("/admin/view-event/<int:event_id>")
@admin_required
def view_event(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template("admin/view-event.html" , event=event)

@app.route("/admin/edit-event/<int:event_id>"  , methods=["GET","POST"])
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == "POST":
        event.title = request.form["event-name"]
        event.description = request.form["event-desc"]
        event.event_date = datetime.datetime.strptime(request.form["event-date"], "%Y-%m-%d").date()
        event.event_time = datetime.datetime.strptime(request.form["event-time"], "%H:%M").time()
        event.category = request.form["event-cat"]
        image = request.files["event-image"]
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join("static/uploads/events", filename))
            image_path = "uploads/events/" + filename
            event.image = image_path
            
        event.venue = request.form["event-venue"]
        event.contact_faculty = request.form["event-faculty"]
        event.deadline = datetime.datetime.strptime(request.form["event-deadline"], "%Y-%m-%d").date()
        event.duration = request.form["event-duration"]
        
        db.session.commit()
        return redirect("/admin/manage-event")

    return render_template("admin/edit-event.html" , event=event )

@app.route("/admin/delete-event/<int:event_id>")
@admin_required
def delete_event(event_id):
    del_event = Event.query.get_or_404(event_id)
    db.session.delete(del_event)
    db.session.commit()
    return redirect("/admin/manage-event")

@app.route("/add-reminder/<int:event_id>")
@login_required
def add_reminder(event_id):
    user = User.query.get_or_404(session["ss_id"])
    event = Event.query.get_or_404(event_id)
    
    rmd = Reminder(
        event_id=event.event_id,
        std_id=user.std_id
    )
    db.session.add(rmd)
    db.session.commit()
    send_reminder_email(user,event)
    return redirect(f"/eventpage/{event_id}")

@app.route("/delete-reminder/<int:event_id>")
@login_required
def delete_reminder(event_id):
    rmdtable = Reminder.query.filter_by(std_id = session["ss_id"], event_id=event_id).first()
    db.session.delete(rmdtable)
    db.session.commit()
    return redirect("/profile")


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000,debug=True)