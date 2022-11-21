import pymongo
import bcrypt


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
def get_logged_in(request, user_database):
    if 'auth_token' in request.cookies and 'email' in request.cookies:

        email = request.cookies["email"]
        user_file = user_database.find_one({"email": email})

        if user_file is None:

            return None

        token = request.cookies["auth_token"]
        hashed_token = user_file["token"]

        if bcrypt.checkpw(token.encode(), hashed_token):

            return user_file

        else:

            return None

    else:

        return None

