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
item_ids = database["ids"]


@app.route('/')  # Serving home page and associated content
def home():
    if get_logged_in(request, user_table):
        # NOTE: We still need to load the current items on sale and the XSRF token here -JG
        current_user = get_logged_in(request, user_table)
        current_xsrf = current_user["xsrf_tokens"]
        return render_template('catalogue.html', listings=None, error=None, xsrf_token=current_xsrf)
    return render_template('home.html', error=None)


@app.route('/add_item')
def add_item():
    if get_logged_in(request, user_table):

        item_xsrf = request.form.get("xsrf_token")
        current_user = get_logged_in(request, user_table)
        current_xsrf = current_user["xsrf_tokens"]

        if item_xsrf == current_xsrf:
            name = request.form.get("item_name")
            description = request.form.get("item_description")
            price = request.form.get("item_price")
            image = request.form.get("item_image")
            new_id = get_item_id(item_ids)
            current_listings.insert_one(
                {"id": new_id, "seller": current_user["user"], "name": name, "description": description, "image": image,
                 "price": price})
            return redirect("/", 200, "OK")

        flash("Cross site request forgery detected!")
        return render_template('home.html', error=None)

    return render_template('home.html', error=None)


@app.route('/login_page')
def login_page():
    if get_logged_in(request, user_table):
        return redirect('/', 400, "Bad Request")
    return render_template('log.html')


@app.route('/signup_page')
def signup_page():
    if get_logged_in(request, user_table):
        return redirect('/', 400, "Bad Request")
    return render_template('sign.html')


@app.route('/signup', methods=["POST"])  # Handles sign-in requests
def signup():
    if get_logged_in(request, user_table):
        return redirect('/', 400, "Bad Request")
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
        return redirect(request.referrer, 400, "Bad Request")


@app.route('/login', methods=["POST"])  # Login handler
def login():
    if get_logged_in(request, user_table):
        return redirect('/', 400, "Bad Request")
    email = request.form.get("login_email")
    password = request.form.get("login_password")
    # Checking if the user is actually registered to us
    user = user_table.find_one({"email": email})
    if user is None:
        flash("Invalid credentials!")
        return redirect("/", 403, "Forbidden")
    else:
        # Then we authenticate their password
        hashed = user["pass"]
        if bcrypt.checkpw(password.encode(), hashed):
            auth_token = secrets.token_urlsafe()
            hashed_token = bcrypt.hashpw(auth_token.encode(), bcrypt.gensalt())
            user_table.update_one({"email": email}, {"$set": {"token": hashed_token}})
            xsrf_token = secrets.token_urlsafe()
            user_table.update_one({"email": email}, {"$set": {"xsrf_tokens": xsrf_token}})
            response = make_response(redirect("/", 200, "OK"))
            response.set_cookie('auth_token', value=auth_token, httponly=True, max_age=604800)
            response.set_cookie('email', value=email, httponly=True, max_age=604800)
            return response

        else:
            flash("Invalid credentials!")
            return redirect("/", 403, "Forbidden")


@app.route('/logout', methods=["POST"])
def logout():
    if get_logged_in(request, user_table):
        # Help with deleting cookies from https://sparkdatabox.com/tutorials/python-flask/delete-cookies
        email = request.cookies["email"]
        user_table.update_one({"email": email}, {"$set": {"token": None}})
        user_table.update_one({"email": email}, {"$set": {"xsrf_tokens": None}})
        response = make_response(render_template('home.html', error=None))
        response.set_cookie('auth_token', value="", httponly=True, max_age=0)
        response.set_cookie('email', value="", httponly=True, max_age=0)
        return response
    else:
        return redirect("/", 400, "Bad Request")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
