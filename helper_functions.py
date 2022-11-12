import pymongo
import bcrypt


# Checks if a user is already in our database. Returns false if not, true if he is
def check_for_user(username: str, user_database):
    hits = user_database.find_one({"user": username})
    if hits is None:
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
