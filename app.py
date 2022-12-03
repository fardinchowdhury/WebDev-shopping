import secrets
import pymongo
import bcrypt
import os
from helper_functions import *
from flask import Flask, render_template, url_for, request, flash, redirect, make_response, send_file, send_from_directory
from werkzeug.utils import secure_filename

# Assistance with file uploads couresty of https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/ -JG

UPLOAD_FOLDER = './images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = int.to_bytes(3, secrets.randbits(24), byteorder="big")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
        current_user = get_logged_in(request, user_table)
        current_xsrf = current_user["xsrf_tokens"]
        items = current_listings.find({})
        return render_template('catalogue.html', listings=items, error=None, xsrf_token=current_xsrf,
                               user=current_user["user"])
    return render_template('home.html', error=None)

@app.route('/add_to_cart', methods=["POST"])
def add_to_cart():

    if get_logged_in(request, user_table):

        current_user = get_logged_in(request, user_table)
        item_xsrf = request.form.get("xsrf_token")
        item_id = request.form.get("item_id")
        current_xsrf = current_user["xsrf_tokens"]

        if item_xsrf == current_xsrf:

            item = current_listings.find_one({"id": int(item_id)})
            if current_user["user"] != item["seller"]:

                return redirect("/", 302, "Found")

            return redirect("/", 302, "Invalid request")

        return redirect("/", 302, "Access Forbidden")

    return redirect("/", 302, "Access Forbidden")

@app.route('/delete_item', methods=["POST"])
def delete_item():

    if get_logged_in(request, user_table):

        current_user = get_logged_in(request, user_table)
        item_xsrf = request.form.get("xsrf_token")
        item_id = request.form.get("item_id")
        current_xsrf = current_user["xsrf_tokens"]

        if item_xsrf == current_xsrf:
            current_listings.delete_one({"id": int(item_id)})
            return redirect("/", 302, "Found")

        return redirect("/", 302, "Access Forbidden")

    return redirect("/", 302, "Access Forbidden")



@app.route('/add_item', methods=["POST"])
def add_item():

    if get_logged_in(request, user_table):

        if 'item_image' not in request.files:
            flash("Missing image!")
            return render_template('home.html', error=None)

        item_xsrf = request.form.get("xsrf_token")
        current_user = get_logged_in(request, user_table)
        current_xsrf = current_user["xsrf_tokens"]

        if item_xsrf == current_xsrf:

            name = request.form.get("item_name")
            description = request.form.get("item_description")
            price = request.form.get("item_price")
            image = request.files["item_image"]

            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                print("IT GOT PAST CREATING THE FILENAME", flush=True)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                print("IT GOT PAST SAVING THE FILE", flush=True)
            else:
                flash("Invalid file type!")
                return render_template('home.html', error=None)

            new_id = get_item_id(item_ids)

            if current_listings.count_documents({"name": name}) > 0:

                flash("Item name already taken!")
                return redirect("/", 302, "Found")

            current_listings.insert_one(
                {"id": new_id, "seller": current_user["user"], "name": name, "description": description,
                 "image": filename,
                 "price": price})

            return redirect("/", 302, "Found")

        flash("Cross site request forgery detected!")
        return render_template('home.html', error=None)

    return render_template('home.html', error=None)


@app.route('/login_page')
def login_page():
    if get_logged_in(request, user_table):
        return redirect('/', 302, "Bad Request")
    return render_template('log.html')


@app.route('/signup_page')
def signup_page():
    if get_logged_in(request, user_table):
        return redirect('/', 302, "Bad Request")
    return render_template('sign.html')


@app.route('/signup', methods=["POST"])  # Handles sign-in requests
def signup():
    if get_logged_in(request, user_table):
        return redirect('/', 302, "Bad Request")
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
        return redirect(request.referrer, 302, "Bad Request")


@app.route('/login', methods=["POST"])  # Login handler
def login():
    if get_logged_in(request, user_table):
        return redirect('/', 302, "Bad Request")
    email = request.form.get("login_email")
    password = request.form.get("login_password")
    # Checking if the user is actually registered to us
    user = user_table.find_one({"email": email})
    if user is None:
        flash("Invalid credentials!")
        return redirect("/", 302, "Forbidden")
    else:
        # Then we authenticate their password
        hashed = user["pass"]
        if bcrypt.checkpw(password.encode(), hashed):
            auth_token = secrets.token_urlsafe()
            hashed_token = bcrypt.hashpw(auth_token.encode(), bcrypt.gensalt())
            user_table.update_one({"email": email}, {"$set": {"token": hashed_token}})
            xsrf_token = secrets.token_urlsafe()
            user_table.update_one({"email": email}, {"$set": {"xsrf_tokens": xsrf_token}})
            response = make_response(redirect("/", 302, "OK"))
            response.set_cookie('auth_token', value=auth_token, httponly=True, max_age=604800)
            response.set_cookie('email', value=email, httponly=True, max_age=604800)
            return response

        else:
            flash("Invalid credentials!")
            return redirect("/", 302, "Forbidden")


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
        return redirect("/", 302, "Bad Request")


@app.route('/image/<image_id>', methods=["GET"])
def load_image(image_id):
    if get_logged_in(request, user_table):
        item = current_listings.find_one({"id": int(image_id)})
        if item is None:
            return send_file("images/invalid_image.jpg")
        image_name = item["image"]
        print("Image name is:" + image_name, flush=True)
        return send_from_directory(app.config["UPLOAD_FOLDER"], image_name)
    return send_file("images/invalid_image.jpg")


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
