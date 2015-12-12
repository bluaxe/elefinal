from functools import wraps
from flask import *

from flask.ext.bootstrap import Bootstrap
from flaskext.mysql import MySQL
from flask.ext.redis import FlaskRedis
from flask_bootstrap import Bootstrap

import elasticsearch
from flask.ext.moment import Moment  #time module
from datetime import datetime

es = elasticsearch.Elasticsearch(["115.159.160.136:9200"])
app = Flask(__name__)
bootstrap = Bootstrap(app)
moment = Moment(app) # time module
app.secret_key = 'A0Zr98j/3yX R~XHH!jDLfdsa22'

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'hack15DL'
app.config['MYSQL_DATABASE_DB'] = 'test'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql = MySQL()
mysql.init_app(app)

app.config['REDIS_URL'] = "redis://:@115.159.160.136:6379/"
cache = FlaskRedis(app)

create_table = '''
create table if not exists users(
                        id int NOT NULL AUTO_INCREMENT,
                        name VARCHAR(64) NOT NULL,
                        password VARCHAR(64) NOT NULL DEFAULT '',
                        PRIMARY KEY(id),
                        UNIQUE(name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8
'''

add_line = '''
insert into users(name, password) values("%s", "%s");
'''

get_user = '''
select * from users where name='%s'
'''

def init():
	pass

def count_request(func):
	@wraps(func)
	def func_wrapper(*args, **kwargs):
		cache.incr("count", 1)
		return func(*args, **kwargs)
	return func_wrapper

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
		kv['user_id'] = 0
	return kv

@app.route("/create")
@count_request
def create():
	curse = mysql.connect().cursor()
	curse.execute(create_table)
	data = curse.fetchone()
	return render_template("info.html", info="done")

@app.route("/")
@count_request
def index():
	urls = dict()
	urls['reg_url']=url_for("reg_page")
	urls['login_url']=url_for("login_page")
	urls['user_commit_url']=url_for("user_commit", user_id=149484)
	urls['user_order_url']=url_for("user_order")
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
		return render_template("info.html", info="user not found")
	print data, passwd
	if data[2]==passwd:
		session['login'] = 1
		# return render_template("info.html", info="login ok")
		return redirect(url_for("home"))
	return render_template("info.html", info="password not correct")

@app.route("/login")
def login_page():
	if 'login' in session:
		# return render_template("info.html", info="already loged in.")
		redirect(url_for("home"))	
	return render_template("login.html", url=url_for("login_action"))

@app.route("/home")
@need_login
def home():
	return render_template("home.html")


@app.route("/logout")
@need_login
def logout():
	session.pop('login', None)
	return render_template("logout.html")

@app.route("/reg", methods=["post"])
def reg_action():
	username = request.form["username"]
	passwd = request.form["password"]
	sql = add_line % (username, passwd)

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
		return render_template("info.html", info=ret)

@app.route("/reg")
def reg_page():
	return render_template("reg.html", url=url_for("reg_action"))

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
	cache.sadd("user_order_list", order_id)
	cache.hset("user_orders", order_id, ret)
	user_id = ret['user_id']
	rest_id = ret['restaurant_id']
	# print user_id, rest_id
	rest_order = {
		"order_id":order_id,
		"user_id": user_id,
		"dispatch_price": 5,
		"address": "ssss",
		"phone": "18817555221",
		"latitude": 12.22,
		"longitude": 214.12,
	}
	cache.hset("rest_orders", order_id, str(rest_order))	
	cache.sadd("rest_order_list", order_id)
	order = eval(str(rest_order))
	print order['order_id']
	return render_template("info.html", info="ok")	

@app.route("/user_commit/<int:user_id>")
def user_commit(user_id):
	session["user_id"]=user_id
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
	return render_template("user_commit.html", data=data)

@app.route("/user_order")
def user_order():
	kv = get_kv()
	return render_template("user_order.html", current_time=datetime.utcnow(), kv=kv)

@app.route("/rest_post")
def rest_post():
	orders = cache.smembers("user_order_list")
	data = list()
	for order_id in orders:
		order = eval(cache.hget("user_orders", order_id))
		send_price = 0
		for ex in order['detail']['extra']:
			send_price += ex['price']
		order['send_price'] = send_price
		order['seller_address'] = "seller_address place_holder"
		data.append(order)
	return render_template("rest_post.html", orders=data)

@app.route("/dispatch_list")
def dispatch_list():
	orders = cache.smembers("rest_order_list")
	data = list()
	for order_id in orders:
		order = eval(cache.hget("rest_orders", order_id))
		data.append(order)
	return render_template("/dispatch_list.html", orders=data)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404

@app.route("/seller")
def seller():
	return render_template('seller.html')

@app.route("/buyer")
def buyer():
	return render_template('buyer.html')

@app.route("/sender")
def sender():
	return render_template("sender.html")

init()
app.run(host="0.0.0.0", port=8080, debug=True)
