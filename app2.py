import socket
import time

from bson import ObjectId
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
#print(__name__)
app=Flask(__name__)


app.config['MONGO_URI'] = 'mongodb://localhost:27017/User_info'
mongo = PyMongo(app)

db= mongo.db

#================= Main Page ===========================
@app.route('/',methods=['GET'])
def Add_Task():
    return render_template('index2.html')


#================= ADD DATA ============================
@app.route('/item-upload',methods=['POST'])
def Create_():
    if 'upload_image' in request.files:
        print("Posted file : {}".format(request.files['upload_image']))
        file =  request.files['upload_image']
        if not file:
            return "no picture", 400
        #sec_file_name = secure_filename(file.filename)
        mongo.save_file(file.filename,file)
        mongo.db.Users.insert_one({'username':request.form.get('username'),'profile_image_name':file.filename,'Number':1,'item':request.form['itemname']})
        try:
            return redirect('/')
        except:
            return "There was an issue when add task"



#========================= Add Number ===================
@app.route('/item-update',methods=['POST'])
def Add_():
    print("in add")
    if 'username' and 'itemname' in request.form:
        username= request.form['username']
        print(username)
        itemname= request.form['itemname']
        print(itemname)
        Current_user_item = mongo.db.Users.find_one_or_404({"username":username,"item":itemname})
        print("id = ",request.form.get('plus',""))
        is_number=request.form['number'].isnumeric()
        print("it is a number ",is_number)
        if is_number:
            number=request.form['number']
        else:
            number=1


        if request.form.get('plus') == '+':
            print("plus")
            mongo.db.Users.update_one({'username':username,'item':itemname},{"$set":{"Number":Current_user_item['Number']+int(number)}})
        elif request.form.get('minus') == '-':
            print("minus")
            mongo.db.Users.update_one({'username':username,'item':itemname},{"$set":{"Number":Current_user_item['Number']-int(number)}})
    
    return redirect('/')



#====================Delete Item========================
@app.route('/item-delete',methods=['POST'])
def Delete_():
    print("in delete")
    if 'username' and 'itemname' in request.form:
        username= request.form['username']
        print(username)
        itemname= request.form['itemname']
        print(itemname)
        mongo.db.Users.delete_one({'username':username,'item':itemname})
    return redirect('/')






app.run(debug=True)
# if __name__=="__main__":
#    app.run(debug=True)
#     print("this is the main module")
# else:
#     print("this is not the main module, imported by other")
