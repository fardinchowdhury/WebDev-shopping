import pymongo
import bcrypt
import numpy


# Checks if a user is already in our database. Returns false if not, true if he is
def check_for_user(username: str, email: str, user_database):
    hits1 = user_database.find_one({"user": username})
    hits2 = user_database.find_one({"email": email})

    if hits1 is None and hits2 is None:
        return False
    else:
        return True


# Checks if a password matches what's on file for the user; implemented with check_for_user so just call that
def check_password(username: str, password: str, user_database):
    if not check_for_user(username, user_database):
        return False
    else:
        user = user_database.find_one({"user": username})
        user_password = user["pass"]
        if bcrypt.checkpw(password.encode(), user_password):
            return True
        else:
            return False


# This code checks if the current request has an user token, and fetches the user profile associated with it
# If the profile is found successfully, the associated user's record in the database is returned
# Otherwise, None is returned
# -JG

# Simple code to get an ID for an item and then update the one on record
def get_item_id(id_database):
    old_id = id_database.find_one({})
    if not old_id:
        id_database.insert_one({"id": 1})
        return 1
    else:
        next_id = int(old_id['id']) + 1
        id_database.update_one({}, {'$set': {"id": next_id}})
        return next_id


def get_logged_in(request, user_database):
    if 'auth_token' in request.cookies and 'email' in request.cookies:

        email = request.cookies["email"]
        user_file = user_database.find_one({"email": email})

        if user_file is None:
            return None
        if user_file["token"] is None:
            return None
        token = request.cookies["auth_token"]
        hashed_token = user_file["token"]

        if bcrypt.checkpw(token.encode(), hashed_token):

            return user_file

        else:

            return None

    else:

        return None


def update_users_items(user_table, bought_items):
    users_to_update = user_table.find({"items": {"$in": bought_items}})
    for user in users_to_update:
        current_user = user["user"]
        current_items = user["items"]
        current_sold = user["sold_items"]
        # With help from https://stackoverflow.com/questions/65605535/how-can-i-find-matching-elements-and-indices-from-two-arrays
        items_to_remove = numpy.intersect1d(current_items, bought_items)
        for item in items_to_remove:
            current_items.remove(item)
            current_sold.append(item)
        user_table.update_one({"user": current_user}, {"$set": {"items":current_items,"sold_items":current_sold}})
    return None
