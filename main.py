 #!/usr/bin/python
 # -*- coding: utf-8 -*-
"你好"
from functools import wraps
from flask import *
import random
import json

from flask.ext.bootstrap import Bootstrap
from flaskext.mysql import MySQL
from flask.ext.redis import FlaskRedis
from flask_bootstrap import Bootstrap

import elasticsearch
from flask.ext.moment import Moment  #time module
from datetime import datetime, timedelta
import math

es = elasticsearch.Elasticsearch(["115.159.160.136:9200"])
app = Flask(__name__)
bootstrap = Bootstrap(app)
moment = Moment(app) # time module
app.secret_key = 'A0Zr98j/3yX R~XHH!jDLfdsa22'

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'hack15DL'
app.config['MYSQL_DATABASE_DB'] = 'test'
# app.config['MYSQL_DATABASE_HOST'] = '115.159.160.136'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql = MySQL()
mysql.init_app(app)

app.config['REDIS_URL'] = "redis://:@115.159.160.136:6379/"
cache = FlaskRedis(app)

buyer_type = 0
seller_type = 1
sender_type = 2

create_table = '''
create table if not exists users(
                        id int NOT NULL AUTO_INCREMENT,
                        name VARCHAR(64) NOT NULL,
                        password VARCHAR(64) NOT NULL DEFAULT '',
                        type int NOT NULL default 0,
                        PRIMARY KEY(id),
                        UNIQUE(name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8
'''

add_line = '''
insert into users(name, password, type) values("%s", "%s", "%s");
'''

get_user = '''
select * from users where name='%s'
'''

user_ids=list()
def init():
	ret = es.search(index="hackathon", doc_type='order', body={"size": 40, "from": 10})
	ret = ret["hits"]['hits']
	for order in ret:
		user_ids.append(order['_source']['user_id'])

def rad(a):
	return a * math.pi / 180

def dist(pos1, pos2):
	'''
	lat1 = 31.245120521563523
	lon1 = 121.38083458062272
	lat2 = 31.245892678034142
	lon2 = 121.38089756833982
	'''
	lat1 = pos1['latitude']
	lat2 = pos2['latitude']
	lon1 = pos1['longitude']
	lon2 = pos2['longitude']
	b = (lat1 + lat2) /2
	dx = lon2 - lon1
	dy = lat2 - lat1
	lx = rad(dx) * 6367000.0* math.cos(rad(b))
	ly = 6367000.0 * rad(dy)
	return math.sqrt(lx * lx + ly * ly)

def count_request(func):
	@wraps(func)
	def func_wrapper(*args, **kwargs):
		cache.incr("count", 1)
		return func(*args, **kwargs)
	return func_wrapper

def get_rest_info(rest_id):
	ret = es.get(index="hackathon", doc_type='restaurant', id=rest_id)[u'_source']
	return ret

def need_login(func):
	@wraps(func)
	def func_wrapper(*args, **kwargs):
		if 'login' not in session:
			return redirect(url_for("login_page"))
		return func(*args, **kwargs)
	return func_wrapper

def get_kv():
	kv=dict()
	if 'login' in session :
		kv['login'] = 1
	else:
		kv['login'] = 0
	if 'user_id' in session :
		kv['user_id'] = session['user_id']
	else:
		kv['user_id'] = random.choice(user_ids)
		session['user_id'] = kv['user_id']
	if 'type' in session :
		kv['type'] = session['type']
	else:
		kv['type'] = -1
	if 'uid' in session :
		kv['uid'] = session['uid']
	else:
		kv['uid'] = -1
	return kv

@app.route("/create")
@count_request
def create():
	curse = mysql.connect().cursor()
	curse.execute(create_table)
	data = curse.fetchone()
	return render_template("info.html", info="done", kv=get_kv())

@app.route("/")
@count_request
def index():
	urls = dict()
	urls['reg_url']=url_for("reg_page")
	urls['login_url']=url_for("login_page")
	urls['user_commit_url']=url_for("user_commit", user_id=149484)
	urls['user_order_url']=url_for("user_order", user_id=149484)
	urls['rest_post_url']=url_for("rest_post")
	urls['dispatch_list_url']=url_for("dispatch_list")

	return render_template("index.html", urls=urls, kv=get_kv())

@app.route("/login", methods=["post"])
def login_action():
	curse = mysql.connect().cursor()
	username = request.form["username"]
	passwd = request.form["password"]
	sql = get_user % (username)
	curse.execute(sql)
	data = curse.fetchone()
	if data is None:
		return render_template("info.html", info="user not found", kv=get_kv(), url=url_for("login_page"))
	# print data, passwd
	if data[2]==passwd:
		session['login'] = 1
		session['type'] = data[3]
		session['uid'] = data[0]
		# return render_template("info.html", info="login ok")
		if session['type'] ==0 :
			return redirect(url_for("user_commit"))
		if session['type'] ==1 :
			return redirect(url_for("rest_post"))
		if session['type'] ==2	:
			return redirect(url_for("dispatch_list"))
	return render_template("info.html", info="password not correct", kv=get_kv(), url=url_for("login_page"))

@app.route("/login")
def login_page():
	if 'login' in session:
		# return render_template("info.html", info="already loged in.")
		redirect(url_for("home"))	
	return render_template("login.html", url=url_for("login_action"), kv=get_kv())

@app.route("/home")
@need_login
def home():
	return render_template("home.html", kv=get_kv())


@app.route("/logout")
@need_login
def logout():
	session.pop('login', None)
	session.pop('user_id', None)
	session.pop('type', None)
	return render_template("logout.html", kv=get_kv())

@app.route("/reg", methods=["post"])
def reg_action():
	username = request.form["username"]
	passwd = request.form["password"]
	user_type = request.form["type"]
	sql = add_line % (username, passwd, user_type)

	ret = "unexpected error"
	try:
		conn = mysql.connect()
		curse = conn.cursor()
		curse.execute(sql)
		data = curse.fetchone()
		conn.commit()
		ret = "ok"
	except Exception as e:
		print e
		ret="already exists"
	finally:
		return render_template("info.html", info=ret, kv=get_kv())

@app.route("/reg")
def reg_page():
	return render_template("reg.html", url=url_for("reg_action"), kv=get_kv())

def add_order_info(order_id, info):
	time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")	
	info=time+" " + info
	key = "of"+str(order_id)
	cache.lpush(key, info)

def get_order_log(order_id):
	key = "of"+str(order_id)
	logs = cache.lrange(key, 0, -1)
	data=[]
	for log in logs:
		data.append(log.decode("utf8"))
	return data

@app.route("/receive_rest_order/<int:order_id>", methods=["post"])
def receive_rest_order(order_id):
	ret = eval(cache.hget("user_orders", order_id))
	user_id = ret['user_id']
	rest_id = ret['restaurant_id']

	now = datetime.now() 
	ready_time = request.form['ready_time'].strip()
	if ready_time  =='':
		ready_minute = 5
	else:
		ready_minute = int(ready_time)
	ready_time = (now + timedelta(minutes=ready_minute)).strftime("%Y-%m-%d %H:%M:%S")
	deliver_time = request.form['dlv_time'].strip()
	if deliver_time =='':
		deliver_minute = 30
	else:
		deliver_minute = int(deliver_time)
	deliver_time= (now + timedelta(minutes=deliver_minute)).strftime("%Y-%m-%d %H:%M:%S")
	rest_info = get_rest_info(rest_id)
	rest_order = {
		"order_id":order_id,
		"user_id": user_id,
		"dispatch_price": request.form['disp_fee'],
		"address": request.form['target_adr'],
		"rest_address": request.form['shop_adr'],
		"phone": "18817555221",
		"ready_time" :ready_time,
		"deliver_time" :deliver_time,
		"latitude": ret['latitude'],
		"longitude": ret['longitude'],
		"rest_longitude" : rest_info['longitude'],
		"rest_latitude" : rest_info['latitude'],
		"restaurant_name" : rest_info['restaurant_name'],
	}
	cache.hset("rest_orders", order_id, str(rest_order))	
	cache.sadd("rest_order_list", order_id)
	order = eval(str(rest_order))
	add_order_info(order_id, "美食已出锅，正在等待配送")	
	# print order
	return render_template("info.html", info="ok", url=url_for("rest_post"), kv=get_kv())

@app.route("/receive_user_order/<int:order_id>")
def receive_user_order(order_id):
	query = {
		"query":{
			"match" : {
				"order_id" :order_id 
			}
		},
		"sort": { "order_id" : "desc"},
	}
	ret = es.search(index="hackathon", doc_type='order', body=query)['hits']['hits'][0]['_source']
	ret['order_id'] = str(ret['order_id'])
	cache.sadd("user_order_list", order_id)
	cache.hset("user_orders", order_id, ret)
	add_order_info(order_id, "客户已下单")	
	return render_template("info.html", info="ok", url=url_for("user_commit"), kv=get_kv())	

@app.route("/user_commit")
@need_login
def user_commit():
	user_id = get_kv()['user_id']
	print user_id
	query = {
		"query":{
			"match" : {
				"user_id" : user_id
			}
		},
		"sort": { "order_id" : "desc"},
	}
	retr = es.search(index="hackathon", doc_type='order', body=query)
	ret = retr['hits']['hits']
	exist_orders = cache.hkeys("user_orders")
	data = []
	for k in ret:
		oder_id = k['_source']['order_id']
		if str(oder_id) not in exist_orders:
			data.append(k)
	return render_template("user_commit.html", data=data, kv=get_kv())

def user_get_order_info(order_id):
	order_id=str(order_id)
	done_orders = cache.smembers("done_orders")
	making_orders = cache.hkeys("user_orders")
	on_the_way_orders = cache.smembers("on_the_way_orders")
	order = eval(cache.hget("user_orders", order_id))
	order['restaurant_name'] = get_rest_info(order['restaurant_id'])['restaurant_name']
	order['status']="waiting"
	if order_id in making_orders:
		order['status']="making"
	if order_id in done_orders:
		order['status']="done"
	if order_id in on_the_way_orders:
		order['status']="on_the_way"	
	return order

@app.route("/buyer")
@app.route("/user_order")
@need_login
def user_order():
	user_id = session["user_id"]
	orders = cache.hkeys("user_orders")
	done_orders = cache.smembers("done_orders")
	making_orders = cache.hkeys("user_orders")
	on_the_way_orders = cache.smembers("on_the_way_orders")
	data = []
	for order_id in orders:
		order = eval(cache.hget("user_orders", order_id))
		if order['user_id'] != user_id:
			continue
		order['restaurant_name'] = get_rest_info(order['restaurant_id'])['restaurant_name']
		order['status']="waiting"
		if order_id in making_orders:
			order['status']="making"
		if order_id in done_orders:
			order['status']="done"
		if order_id in on_the_way_orders:
			order['status']="on_the_way"
		data.append(order)
	# print data
	return render_template("buyer.html", current_time=datetime.utcnow(), orders=data, kv=get_kv())

@app.route("/order_detail/<int:order_id>")
@need_login
def order_detail(order_id):
	order_log = get_order_log(order_id)
	order = user_get_order_info(order_id)
	order['sender_uid'] = cache.hget("order_sender", order_id)
	return render_template("order_detail.html", order=order, log=order_log, kv=get_kv())

@app.route("/rest_post")
@need_login
def rest_post():
	orders = cache.smembers("user_order_list")
	data = list()
	exist_orders = cache.hkeys("rest_orders")
	for order_id in orders:
		order = eval(cache.hget("user_orders", order_id))
		if str(order_id) in exist_orders:
			continue
		send_price = 0
		for ex in order['detail']['extra']:
			send_price += ex['price']
		order['send_price'] = send_price
		order['seller_address'] = get_rest_info(order['restaurant_id'])['address_text']
		# order['seller_address'] = get_rest_info(order['restaurant_id'])['restaurant_name']
		data.append(order)
	return render_template("rest_post.html", orders=data, kv=get_kv())

@app.route("/dispatch_list")
@need_login
def dispatch_list():
	orders = cache.smembers("rest_order_list")
	data = list()
	otw_orders = cache.smembers("on_the_way_orders")
	done_orders = cache.smembers("done_orders")
	for order_id in orders:
		if order_id in otw_orders:
			continue
		if order_id in done_orders:
			continue
		order = eval(cache.hget("rest_orders", order_id))
		print order
		data.append(order)
	return render_template("/dispatch_list.html", orders=data, kv=get_kv())

@app.route("/sender_post/<int:order_id>")
@need_login
def sender_post(order_id):
	order_id=str(order_id)
	cache_ret = cache.hget("rest_orders", order_id)
	order = eval(cache_ret)
	uid = session['uid']
	ret = cache.sadd("on_the_way_orders", order_id)
	if ret==0:
		return render_template("/info.html", info="get failed.", kv=get_kv(), url=url_for("dispatch_list"))
	cache.sadd(uid, order_id)
	cache.hset("order_sender", order_id, uid)
	add_order_info(order_id, "配送员已接单，正在配送中")
	return render_template("/info.html", info="ok", kv=get_kv(), url=url_for("dispatch_list"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404

@app.route("/seller")
def seller():
	return render_template("seller.html", kv=get_kv())

#@app.route("/buyer")
#def buyer():
#	return render_template('buyer.html', kv=get_kv())

def save_pos(uid, pos):
	cache.hset("sender_pos", uid, str(pos))

@app.route("/get_sender_pos/<int:uid>")
def get_sender_pos(uid):
	pos = eval(cache.hget("sender_pos", uid))
	return json.dumps(pos)

@app.route("/sender_api", methods=["post", "get"])
def sender_api():
	uid = request.json['uid']
	longitude= request.json['longitude']
	latitude= request.json['latitude']
	pos=dict()
	pos['longitude']=longitude
	pos['latitude']=latitude
	save_pos(uid, pos)
	# print uid, longitude, latitude

	orders = cache.hkeys("rest_orders")
	data = list()
	otw_orders = cache.smembers("on_the_way_orders")
	done_orders = cache.smembers("done_orders")
	for order_id in orders:
		if order_id in otw_orders:
			continue
		if order_id in done_orders:
			continue
		order = eval(cache.hget("rest_orders", order_id))
		op= dict()
		op['longitude'] = order['longitude']
		op['latitude'] = order['latitude']
		# print dist(pos, op)
		if dist(pos, op) > 500000:
			continue
		order['order_id'] = str(order['order_id'])
		data.append(order)
	return json.dumps(data)

@app.route("/sender")
def sender():
	uid = session['uid']
	my_order_ids = cache.smembers(uid)
	orders = list()
	done_orders = cache.smembers("done_orders")
	for order_id in my_order_ids:
		order = eval(cache.hget("rest_orders", order_id))
		if order_id in done_orders:
			order['done'] = 1
		else:
			order['done'] = 0
		orders.append(order)

	return render_template('sender.html', kv=get_kv(), orders=orders)

@app.route("/arrival/<int:order_id>")
def arrival(order_id):
	ret = cache.sadd("done_orders", order_id)
	ret = cache.srem("on_the_way_orders", order_id)
	uid = session['uid']
	add_order_info(order_id, "外卖已送达")
	return render_template("info.html", info="ok", url=url_for("sender"), kv=get_kv())



init()
app.run(host="0.0.0.0", port=80, debug=True)
