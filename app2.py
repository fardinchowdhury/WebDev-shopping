import socket
import time
import base64
from bson import ObjectId
from flask import Flask, jsonify, redirect, render_template, request, url_for, send_file, make_response
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
#print(__name__)
app=Flask(__name__)


app.config['MONGO_URI'] = 'mongodb://localhost:27017/User_info'
mongo = PyMongo(app)

db= mongo.db
#================ login page ===================================
@app.route('/',methods=['POST','GET'])
def log_():
    if request.method == 'POST':
        return redirect(url_for('ItemAddingPage_',user=request.form['username'])) # <- This can fix by find user by its email in database
    else:
        return render_template('log.html')


#================= itemchoosing page ===========================
@app.route('/<string:user>/itemaddingpage',methods=['GET','POST'])
def ItemAddingPage_(user):
    print(url_for('ItemAddingPage_',user=user))
    return render_template('item.html')


#================= Image ================================

@app.route('/image/<image_name>',methods=['GET'])
def Get_image(image_name):
    print()
    print(image_name)
    print()
    file_id = mongo.db.fs.files.find_one({'filename':image_name})['_id']
    file = mongo.db.fs.chunks.find_one({'files_id':file_id})
    res = make_response(file['data'])
    res.headers['Content-Type'] = 'image/jpeg'
    return res


#================= shoppingcart ================================

@app.route("/<string:user>/shoppingcart",methods=['GET'])
def Shoppingcart_(user):
    output=[]
    # filename = mongo.db.User_info.find()[0]['profile_image_name']
    # file_id = mongo.db.fs.files.find_one({'filename':filename})['_id']
    # file = mongo.db.fs.chunks.find_one({'files_id':file_id})
    # print(type(file['data']))
    # print()
    # print()
    # print()
    # encode_img = base64.b64encode(file['data'])
    # res = make_response(file['data'])
    # res.headers['Content-Type'] = 'image/jpeg'
    
    # return res


    for i in mongo.db.User_info.find():
        filename = i['profile_image_name']
        # file_id = mongo.db.fs.files.find_one({'filename':filename})['_id']
        # file = mongo.db.fs.chunks.find_one({'files_id':file_id})

        # res = make_response(file['data'])
        # res.headers['Content-Type'] = 'image/jpeg'

        output.append({'Item_name':i['item'],'profile_image_name':filename,'Number':i['Number'],'Price':i['Price'],'seller':i['seller'],'Description':i['Description']})
    return render_template('cart.html',tasks=output)


#================= ADD DATA ====================================
@app.route('/item-upload',methods=['POST','GET'])
def Create_():
    if request.method=='POST':
        print("in create post")
        if 'upload_image' in request.files:
            print("Posted file : {}".format(request.files['upload_image']))
            file =  request.files['upload_image']
            if not file:
                return "no picture", 400
            #sec_file_name = secure_filename(file.filename)
            mongo.save_file(file.filename,file)
            mongo.db.User_info.insert_one({'seller':request.form.get('seller'),'profile_image_name':file.filename,'Number':1,'item':request.form['itemname'],'Description':request.form['description'],'Price':request.form['price'],"Username":request.form['username']})
            try:
                return redirect(url_for('Shoppingcart_',user=request.form['username']))
            except:
                return "There was an issue when add task"



#========================= Add Number ==========================
# @app.route('/item-update',methods=['POST'])
# def Add_():
#     print("in add")
#     if 'seller' and 'itemname' in request.form:
#         seller= request.form['seller']
#         print(seller)
#         itemname= request.form['itemname']
#         print(itemname)
#         Current_user_item = mongo.db.User_info.find_one_or_404({"seller":seller,"item":itemname})
#         print("id = ",request.form.get('plus',""))
#         is_number=request.form['number'].isnumeric()
#         print("it is a number ",is_number)
#         if is_number:
#             number=request.form['number']
#         else:
#             number=1

#         if request.form.get('plus') == '+':
#             print("plus")
#             mongo.db.User_info.update_one({'seller':seller,'item':itemname},{"$set":{"Number":Current_user_item['Number']+int(number)}})
#         elif request.form.get('minus') == '-':
#             print("minus")
#             mongo.db.User_info.update_one({'seller':seller,'item':itemname},{"$set":{"Number":Current_user_item['Number']-int(number)}})
    
#     return redirect('/')



#====================Delete Item========================
@app.route('/item-delete',methods=['POST'])
def Delete_():
    print("in delete")
    if 'seller' and 'itemname' in request.form:
        seller= request.form['seller']
        itemname= request.form['itemname']
        user=mongo.db.User_info.find_one({'seller':seller,'item':itemname})
        mongo.db.User_info.delete_one({'seller':seller,'item':itemname})
        print("this is ",user['Username'])
    return redirect(url_for('Shoppingcart_',user=user['Username']))






app.run(debug=True)
# if __name__=="__main__":
#    app.run(debug=True)
#     print("this is the main module")
# else:
#     print("this is not the main module, imported by other")
