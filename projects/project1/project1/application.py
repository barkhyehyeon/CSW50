import os, requests, json

from flask import Flask, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
	return render_template("login.html", message="Log in with username and password")

@app.route("/logout")
def logout():
	session["userid"] = None
	session["isbn"] = None
	return render_template("login.html", message="Logged out")

@app.route("/register")
def register():
	return render_template("register.html", message="Register with username and password")

@app.route("/registered", methods=["POST"])
def registered():
	if request.method == "GET":
		render_template("register.html", message="Invalid access")
	username = request.form.get("username")
	password = request.form.get("password")
	existingUser = db.execute("SELECT * FROM users WHERE username = :username", {"username":username})
	if existingUser.rowcount != 0:
		return render_template("register.html", message="Username already exists")
	db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username":username, "password":password})
	db.commit()
	return render_template("register.html", message="Register successful")

@app.route("/search", methods=["GET", "POST"])
def search():
	if request.method == "GET":
		if session.get("userid") is None:
			return render_template("login.html", message="Invalid access")
	if request.method == "POST":
		username = request.form.get("username")
		password = request.form.get("password")
		user = db.execute("SELECT * FROM users WHERE username = :username and password = :password", {"username":username, "password":password})
		if user.rowcount != 1:
			return render_template("login.html", message="Wrong username or password")
		user = user.fetchone()
		session["userid"] = user['userid']
	db.commit()
	return render_template("search.html")

@app.route("/result", methods=["POST"])
def result():
	if request.method == "GET":
		if session.get("userid") is None:
			return render_template("login.html", message="Invalid access")
		else:
			return render_template("search.html", message="Invalid access")
	keyword = '%' + request.form.get("keyword").lower() + '%'
	result = db.execute("SELECT * FROM books WHERE LOWER(isbn) LIKE :keyword or LOWER(title) LIKE :keyword or LOWER(author) LIKE :keyword", {"keyword":keyword})
	db.commit()
	return render_template("result.html", result=result)

@app.route("/bookpage", methods=["POST"])
def bookpage():
	if request.method == "GET":
		if session.get("userid") is None:
			return render_template("login.html", message="Invalid access")
		else:
			return render_template("search.html", message="Invalid access")
	isbn = request.form.get("isbn")
	session["isbn"] = isbn
	book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn}).fetchone()

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "b0gIucYZHfS9iMHGQkqDQ", "isbns": isbn})
	try:
		resJson = res.json()
		count = resJson['books'][0]['ratings_count']
		average = resJson['books'][0]['average_rating']
	except:
		count = "NA"
		average = "NA"

	reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
	
	db.commit()
	return render_template("bookpage.html", book=book, count=count, average=average, reviews=reviews, message="Please submit a review for the book")

@app.route("/reviewed", methods=["POST"])
def reviewed():
	if request.method == "GET":
		if session.get("userid") is None:
			return render_template("login.html", message="Invalid access")
		else:
			return render_template("search.html", message="Invalid access")
	isbn = session.get("isbn")
	book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn}).fetchone()

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "b0gIucYZHfS9iMHGQkqDQ", "isbns": isbn})
	try:
		resJson = res.json()
		count = resJson['books'][0]['ratings_count']
		average = resJson['books'][0]['average_rating']
	except:
		count = "NA"
		average = "NA"

	reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn}).fetchall()

	###
	userid = session.get("userid")
	rating = float(request.form.get("rating"))
	description = request.form.get("description")
	review = db.execute("SELECT * FROM reviews where isbn = :isbn and userid = :userid", {"isbn":isbn, "userid":userid})
	if review.rowcount != 0:
		return render_template("bookpage.html", book=book, count=count, average=average, reviews=reviews, message="This book is already reviewed")
	db.execute("INSERT INTO reviews (isbn, userid, rating, description) VALUES (:isbn, :userid, :rating, :description)", 
		{"isbn":isbn, "userid":userid, "rating":rating, "description":description})	
	reviews = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn}).fetchall()	
	db.commit()
	return render_template("bookpage.html", book=book, count=count, average=average, reviews=reviews, message="Review submitted")

@app.route("/api/<string:isbn>")
def getJson(isbn):
	book = db.execute("SELECT * FROM books where isbn = :isbn", {"isbn":isbn}).fetchone()
	tmp = dict()
	tmp["title"] = book["title"]
	tmp["author"] = book["author"]
	tmp["year"] = book["year"]
	tmp["isbn"] = book["isbn"]

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "b0gIucYZHfS9iMHGQkqDQ", "isbns": isbn})
	try:
		resJson = res.json()
		count = resJson['books'][0]['ratings_count']
		average = resJson['books'][0]['average_rating']
	except:
		count = "NA"
		average = "NA"

	tmp["ratings_count"] = count
	tmp["average_score"] = average

	return json.dumps(dict)
