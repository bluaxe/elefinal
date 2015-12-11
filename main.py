from functools import wraps
from flask import *

from flaskext.mysql import MySQL

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jDLfdsa22'

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'hack15DL'
app.config['MYSQL_DATABASE_DB'] = 'test'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql = MySQL()
mysql.init_app(app)

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

def need_login(func):
	@wraps(func)
	def func_wrapper(*args, **kwargs):
		if 'login' not in session:
			return redirect(url_for("login_page"))
		return func(*args, **kwargs)
	return func_wrapper

@app.route("/create")
def create():
	curse = mysql.connect().cursor()
	curse.execute(create_table)
	data = curse.fetchone()
	return render_template("info.html", info="done")

@app.route("/")
def index():
	return render_template("index.html", reg=url_for("reg_page"), login=url_for("login_page"))

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


app.run(host="0.0.0.0", port=8080, debug=True)
