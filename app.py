from utils import *
from flask import Flask, request, render_template, redirect
from maketree import *
from threading import Thread
from config import *
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import os
import sys
import ast


app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = ''
app.config['SECRET_KEY'] = secret_key

down = '</br>'
space = '&emsp;'

#do we have apktool?
try:
	out=cmd_get_output('apktool')
except:
	print "apktool not found"
	sys.exit()



@login_manager.user_loader
def load_user(user_id):
	return User(user_id)


class User(UserMixin):
	def __init__(self, id):
		self.id = id


@app.route('/')
def home():
	if current_user.is_authenticated:
		return redirect('/app', code=302)
	return "home: <a href='/login'>Login</a> <a href='/app'>App</a> <a href='/logout'>Logout</a>"


@app.route('/login', methods=['GET'])
def login():
	key = request.args.get('key')  # type: object
	if key:
		if key == secret_key:
			login_user(User("admin"))
			return "you are logged in"
		else:
			return "Wrong key :("
	else:
		return "Give me your key"


@app.route('/app')
@login_required
def protected():
	applist = {}
	prjname = os.listdir('project')
	for name in prjname:
		logger.info("Check name:" + name)
		applist[name] = os.listdir('project/{}/'.format(name))
	return render_template('index.html', applist=applist)


@app.route('/logout/')
@login_required
def logout():
	logout_user()
	return "you are logged out"


@app.route('/up', methods=['GET', 'POST'])
def upload_file():
	if request.method == 'POST':
		#TODO: Android app handle response
		if request.form['key'] == android_secret:
			file = request.files['uploaded_file']
			file.save(file.filename + '.apk')
			thread = Thread(target=unpack_apk, args=(file.filename,))
			thread.start()
			return "ok"
		return "Android secret key mismatch"


#get version code ver?app=com.example
@app.route('/ver', methods=['GET'])
def app_vercode():
	appname = request.args.get('app')
	if appname:
		if os.path.isdir('project/%s' % appname):
			return get_last_appver('project/%s/' % appname)
		else:
			os.mkdir('project/%s' % appname)
			return "0"
	else:
		return ""

@app.route('/filediff', methods=['GET'])
@login_required
def filediff():
	location = request.args.get('fname')
	package_name = location.split('/')[0]
	filename = location.split('/', 1)[1]
	package_location = 'project/{}'.format(package_name)
	appvers = os.listdir(package_location)

	if len(appvers) == 0:
		return "Look like this app does't exist"

	if len(appvers) == 1:

		file_location = package_location + '/' + appvers[0] + '/' + filename
		return render_file(file_location)

	appvers.sort(reverse=True)
	logger.info("Sorted appver %s" % appvers)
	check_ver = request.args.get('vercode')

	if not check_ver:
		l1, l2 = appvers[0], appvers[1]
	else:
		l1, l2 = get_diff_version(appvers,check_ver)
		logger.info("Get diff data with version code {} {}".format(l1,l2))

	l1_location = '{}/{}/smali_code/{}'.format(package_location, l1, filename)
	l2_location = '{}/{}/smali_code/{}'.format(package_location, l2, filename)
	logger.info(l1_location)

	if not file_exist(l1_location) and not file_exist(l2_location):
		logger.error("Something go wrong :(")
	elif file_exist(l1_location) and file_exist(l2_location):
		return diff_output('git diff apkdb/{} apkdb/{}'.format(l1_location, l2_location))
	elif file_exist(l1_location) and not file_exist(l2_location):
		return diff_output('git diff apkdb/{} /dev/null'.format(l1_location))
	elif not file_exist(l1_location) and file_exist(l2_location):
		return diff_output('git diff /dev/null apkdb/{}'.format(l2_location))
	else:
		pass


@app.route('/core_diff/<name>')
@login_required
def app_diff(name):
	
	appvers = os.listdir('project/{}/'.format(name))
	appvers.sort(reverse=True)
	logger.info("Sorted appver %s" % appvers)
	location = 'project/{}'.format(name)

	check_ver = request.args.get('vercode')
	if not check_ver:
		l1, l2 = appvers[0], appvers[1]
	else:
		logger.info("request diff with versioncode" +check_ver)
		l1, l2 = get_diff_version(appvers,check_ver)

	logger.info("Cheking 2 different version {} {}".format(l1,l2))
	diff_file = '{}/{}/{}_{}'.format(location, l1, l1, l2)
	logger.info("Make diff file {}".format(diff_file))
	if file_exist(diff_file):
		logger.info("Diff file exits")
		with open(diff_file, 'r') as r:
			ret = r.read()
	else:
		logger.error("File not found")

	allfile = {}
	x = ret.split('\n')
	for i in x[1:]:
		k = i.split('\t')
		# if not blacklist_filter(k[1]):
		try:
			allfile[k[1].split('smali_code')[1]] = k[0]
		except:
			allfile[k[1]] = k[0]
	tree = make_diff_tree(allfile, name, l1)
	return render_template("diff.html", tree=tree)

@app.route('/diff/<name>')
@login_required
def main_diff(name):
	appvers = os.listdir('project/{}/'.format(name))
	appvers.sort(reverse=True)
	logger.info("Sorted appver %s" % appvers)
	location = 'project/{}'.format(name)

	check_ver = request.args.get('vercode')
	if not check_ver:
		l1, l2 = appvers[0], appvers[1]
	else:
		logger.info("request diff with versioncode" +check_ver)
		l1, l2 = get_diff_version(appvers,check_ver)

	diff_file = '{}/{}/{}_{}_line'.format(location, l1, l1, l2)
	logger.info("DIFFFILE"+ diff_file)
	with open(diff_file,'r') as f:
		data = f.read()
	diff_data = ast.literal_eval(data)
	# print diff_data
	choose_one = []
	for keys,values in sorted(diff_data.items()):
		if values[0]!= values[1]:
			if not in_black_list(keys):
				choose_one.append(keys)

	tree = simple_tree(choose_one,name,l1)

	return render_template("diff.html", tree=tree)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)