from flask import Flask, render_template, url_for, request, flash
import pymongo
import bcrypt
from helper_functions import *

app = Flask(__name__, template_folder="templates", static_folder="static")
# Database pointers
mongo_client = pymongo.MongoClient('mongo')
database = mongo_client["Site_Info"]
user_table = database["users"]  # Table for user info (usernames, etc.)
current_listings = database["listings"]  # Records for all current items listed on the site
transaction_records = database["transactions"]  # Holds a record of all previous finished transactions


@app.route('/')  # Serving home page and associated content
def home():
    return render_template('home.html', error=None)

@app.route('/signup', methods=["POST"])
def signup():
    username = request.form.get("register_username")
    password = request.form.get("register_password")
    # Checking if the user exists already; if false, we continue with registration
    if not check_for_user(username, user_table):
        return render_template('home.html')
    else:
        flash("Username already in use!")
        return render_template('home.html')


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
