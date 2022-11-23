import secrets
import pymongo
import bcrypt
from helper_functions import *
from flask import Flask, render_template, url_for, request, flash, redirect, make_response

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = int.to_bytes(3, secrets.randbits(24), byteorder="big")

# Database pointers
mongo_client = pymongo.MongoClient('mongo')
database = mongo_client["Site_Info"]
user_table = database["users"]  # Table for user info (usernames, etc.)
current_listings = database["listings"]  # Records for all current items listed on the site
transaction_records = database["transactions"]  # Holds a record of all previous finished transactions


@app.route('/')  # Serving home page and associated content
def home():
    if get_logged_in(request, user_table): return render_template('item.html', error=None)
    return render_template('home.html', error=None)


@app.route('/login_page')
def login_page():
    if get_logged_in(request, user_table):
        return redirect('/', 302, None)
    return render_template('log.html')


@app.route('/signup_page')
def signup_page():
    if get_logged_in(request, user_table):
        return redirect('/', 302, None)
    return render_template('sign.html')


@app.route('/signup', methods=["POST"])  # Handles sign-in requests
def signup():
    if get_logged_in(request, user_table):
        return redirect('/', 302, None)
    username = request.form.get("register_username")
    password = request.form.get("register_password")
    email = request.form.get("register_email")
    # Checking if the user exists already; if false, we continue with registration. Otherwise, flash an error message
    if not check_for_user(username, email, user_table):
        print("Creating user!", flush=True)
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        user_table.insert_one({"user": username, "email": email, "pass": hashed_password})
        flash("Signup successful!")
        return render_template('home.html')
    else:
        flash("Email or username already in use!")
        return redirect(request.referrer, 302, None)


@app.route('/login', methods=["POST"])  # Login handler
def login():
    if get_logged_in(request, user_table):
        return redirect('/', 302, None)
    email = request.form.get("login_email")
    password = request.form.get("login_password")
    # Checking if the user is actually registered to us
    user = user_table.find_one({"email": email})
    if user is None:
        flash("Invalid credentials!")
        return redirect("/", 302, None)
    else:
        # Then we authenticate their password
        hashed = user["pass"]
        if bcrypt.checkpw(password.encode(), hashed):
            auth_token = secrets.token_urlsafe()
            hashed_token = bcrypt.hashpw(auth_token.encode(), bcrypt.gensalt(1))
            user_table.update_one({"email": email}, {"$set": {"token": hashed_token}})
            response = make_response(render_template())  # FILL THIS OUT TO LEAD TO THE FIRST PAGE
            response.set_cookie('auth_token', value=auth_token, httponly=True, max_age=604800)
            response.set_cookie('email', value=email, httponly=True, max_age=604800)
            return response

        else:
            flash("Invalid credentials!")
            return redirect("/", 302, None)


@app.route('/logout', methods=["POST"])
def logout():
    if get_logged_in(request, user_table):
        # Help with deleting cookies from https://sparkdatabox.com/tutorials/python-flask/delete-cookies
        response = make_response(render_template('home.html', error=None))  # FILL THIS OUT TO LEAD TO THE LOGIN PAGE
        response.set_cookie('auth_token', value="", httponly=True, max_age=0)
        response.set_cookie('email', value="", httponly=True, max_age=0)
        return response
    else:
        return redirect("/", 302, None)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
