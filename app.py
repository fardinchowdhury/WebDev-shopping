import secrets
import pymongo
import bcrypt
import os
from helper_functions import *
from flask import Flask, render_template, url_for, request, flash, redirect, make_response, send_file, \
    send_from_directory
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room, leave_room
from datetime import datetime, timedelta

# Assistance with file uploads couresty of https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/ -JG

UPLOAD_FOLDER = './images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = int.to_bytes(3, secrets.randbits(24), byteorder="big")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app)

# Database pointers
mongo_client = pymongo.MongoClient('mongo')
database = mongo_client["Site_Info"]
user_table = database["users"]  # Table for user info (usernames, etc.)
current_listings = database["listings"]  # Records for all current items listed on the site
transaction_records = database["transactions"]  # Holds a record of all previous finished transactions
item_ids = database["ids"]
auctions_listings = database["auctions"]


@app.route('/')  # Serving home page and associated content
def home():
    if get_logged_in(request, user_table):
        current_user = get_logged_in(request, user_table)
        current_xsrf = current_user["xsrf_tokens"]
        items = current_listings.find({"auction":False})
        return render_template('catalogue.html', listings=items, error=None, xsrf_token=current_xsrf,
                               user=current_user["user"], cart=current_user["cart"])
    return render_template('home.html', error=None)

@app.route('/profile', methods=["GET"])
def profile():
    if get_logged_in(request, user_table):
        current_user = get_logged_in(request, user_table)

        items = current_user["items"]
        print(items, flush=True)
        bought_items = current_user["bought_items"]
        sold_items = current_user["sold_items"]

        item_list = current_listings.find({"id": {"$in": items}})
        bought_list = transaction_records.find({"id": {"$in":bought_items}})
        sold_list = transaction_records.find({"id": {"$in":sold_items}})

        return render_template('profile.html', error=None, items=item_list, bought=bought_list, sold=sold_list, user=current_user)
        # Need to finish the template above
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
                current_cart = current_user["cart"]
                if type(current_cart) == type(None):

                    current_cart = [int(item_id)]
                else:
                    current_cart.append(int(item_id))
                user_table.update_one({"user": current_user["user"]}, {"$set": {"cart": current_cart}})
                return redirect("/", 302, "Found")

            return redirect("/", 302, "Invalid request")

        return redirect("/", 302, "Access Forbidden")

    return redirect("/", 302, "Access Forbidden")


@app.route('/remove_from_cart', methods=["POST"])
def remove_from_cart():
    if get_logged_in(request, user_table):

        current_user = get_logged_in(request, user_table)
        item_xsrf = request.form.get("xsrf_token")
        item_id = request.form.get("item_id")
        current_xsrf = current_user["xsrf_tokens"]

        if item_xsrf == current_xsrf:

            if int(item_id) in current_user["cart"]:
                current_cart = current_user["cart"]
                current_cart.remove(int(item_id))
                user_table.update_one({"user": current_user["user"]}, {"$set": {"cart": current_cart}})

                return redirect("/", 302, "Found")

            return redirect("/", 302, "Invalid request")

        return redirect("/", 302, "Access Forbidden")

    return redirect("/", 302, "Invalid Request")


@app.route('/cart', methods=["GET"])
def cart():
    if get_logged_in(request,user_table):
        current_user = get_logged_in(request, user_table)
        cart_items = current_user["cart"]
        cart_items = current_listings.find({"id": {"$in": cart_items}})
        current_xsrf = current_user["xsrf_tokens"]
        items_length = len(list(cart_items))
        print(items_length, flush=True)
        return render_template("cart.html", error=None, items=cart_items, items_length=items_length, user = current_user, xsrf_token=current_xsrf)
    return redirect("/", 302, "Invalid Request")

@app.route('/checkout', methods=["POST"])
def checkout():
    if get_logged_in(request, user_table):
        current_user = get_logged_in(request, user_table)
        item_xsrf = request.form.get("xsrf_token")
        current_xsrf = current_user["xsrf_tokens"]
        if item_xsrf == current_xsrf:
            bought_items = current_user["cart"]
            current_items = current_user["bought_items"]
            current_items = bought_items + current_items
            add_to_transactions(transaction_records, current_listings, bought_items, current_user["user"])
            user_table.update_one({"user": current_user["user"]}, {"$set": {"bought_items": current_items, "cart": []}})
            user_table.update_many({"cart": {"$in": bought_items}}, {"$pull": {"cart": {"$in": bought_items}}})
            update_users_items(user_table, bought_items)
            current_listings.delete_many({"id": {"$in": bought_items}})

            # Handle the owners of the items having it removed from their listed items and put into their sold items
            flash("Order processed successfully")
            return redirect("/", 302, "Found")
        return redirect("/", 302, "Access Forbidden")

    return redirect("/", 302, "Invalid Request")


@app.route('/delete_item', methods=["POST"])
def delete_item():
    if get_logged_in(request, user_table):

        current_user = get_logged_in(request, user_table)
        item_xsrf = request.form.get("xsrf_token")
        item_id = request.form.get("item_id")
        current_xsrf = current_user["xsrf_tokens"]

        if item_xsrf == current_xsrf:
            current_listings.delete_one({"id": int(item_id)})
            current_items = current_user["items"]
            current_items.remove(int(item_id))
            user_table.update_one({"user": current_user["user"]}, {"$set": {"items": current_items}})
            user_table.update_many({"cart": int(item_id)}, {"$pull": {"cart": int(item_id)}})
            return redirect("/", 302, "Found")

        return redirect("/", 302, "Access Forbidden")

    return redirect("/", 302, "Invalid Request")


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
            print("New ID is: " + str(new_id), flush=True)
            if current_listings.count_documents({"name": name}) > 0:
                flash("Item name already taken!")
                return redirect("/", 302, "Found")
            if "item_time" in request.form:
                current_listings.insert_one(
                    {"id": new_id, "seller": current_user["user"], "name": name, "description": description,
                     "image": filename,
                     "price": price, "auction": True})
                time = datetime.now() + timedelta(minutes=int(request.form.get("item_time")))
                auctions_listings.insert_one({"seller":current_user["user"], "id":new_id, "description":description, "name": name, "time":time})
            else:
                current_listings.insert_one(
                    {"id": new_id, "seller": current_user["user"], "name": name, "description": description,
                    "image": filename,
                    "price": price, "auction":False})

            current_items = current_user["items"]
            print(current_items, flush=True)
            if type(current_items) == type(None):
                print("IT'S INSIDE THE CURRENT ITEMS CHECK", flush=True)
                current_items = [new_id]
            else:
                current_items.append(new_id)
            print(current_items, flush=True)
            user_table.update_one({"user": current_user["user"]}, {"$set": {"items": current_items}})

            if "item_time" in request.form:
                return redirect("/auction", 302, "Found")
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

@app.route('/auction')
def auction_page():
    if get_logged_in(request, user_table):
        current_user = get_logged_in(request, user_table)
        current_xsrf = current_user["xsrf_tokens"]
        auctions = auctions_listings.find({})
        return render_template('auction.html', auctions=auctions, user=current_user, xsrf_token=current_xsrf)
    return redirect('/', 302, "Access Denied")

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
        user_table.insert_one(
            {"user": username, "email": email, "pass": hashed_password, "cart": [], "token": None, "xsrf_tokens": None,
             "bought_items": [], "sold_items": [], "items": []})
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


@app.route('/logout', methods=["GET"])
def logout():
    if get_logged_in(request, user_table):
        # Help with deleting cookies from https://sparkdatabox.com/tutorials/python-flask/delete-cookies
        email = request.cookies["email"]
        user_table.update_one({"email": email}, {"$set": {"token": None}})
        user_table.update_one({"email": email}, {"$set": {"xsrf_tokens": None}})
        response = make_response(redirect("/", 302, "Found"))
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
    socketio.run(app, debug=True, host='0.0.0.0')
