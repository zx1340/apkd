import logging
import os
import subprocess
import glob
import time
import re
from config import *

logging.basicConfig(level=logging.INFO)
logging.addLevelName(logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
logging.addLevelName(logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))

logger = logging.getLogger(__name__)

def get_all_file(source_folder):
	ret = []
	for r, d, f in os.walk(source_folder):
		for file in f:
			if ".smali" in file:
				ret.append(os.path.join(r, file))
	return ret

def file_exist(fpath):
	return os.path.isfile(fpath)

def folder_exist(folder_path):
	return os.path.isdir(folder_path)


def get_app_version(location):
	with open('%s/AndroidManifest.xml'%location,'r') as f:
		data = f.read()
	return re.findall(r'platformBuildVersionCode=\"(\d+)',data)[0]



# get appversion by app name
def get_last_appver(location):
	logger.info("Get last appver location %s"%location)
	if folder_exist(location):
		appvers = os.listdir(location)
		appvers.sort(reverse=True)
		return appvers[0]
	else:
		logger.info("Project folder not exist")
		return "Folder not exist"



def project_exist(app_name):

	if not os.path.exists('project/%s'%app_name):
		logger.info("Creating folder project/%s"%app_name)
		os.mkdir('project/%s'%app_name)

	app_version = get_app_version(app_name)
	logger.info("Get app version: %s"%app_version)
	if not os.path.exists('project/%s/%s'%(app_name,app_version)):
		create_project(app_name,app_version)
	else:
		logger.info('Found project/%s/%s'%(app_name,app_version))
	return app_version


# def parse_line_change(data):
# 	filedatas = data.split('../')
# 	ret = {}
# 	for filedata in filedatas:
# 		if len(filedata): 
# 			filelocation = filedata.split(' ')[0]
# 			finsertion = re.findall(r'(\d+) insertions',filedata)[0] if 'insertions' in filedata else 0
# 			fdeleteion = re.findall(r'(\d+) deletions',filedata)[0] if 'deletions' in filedata else 0
# 			ret[filelocation] = [finsertion,fdeleteion]
# 	return ret

def create_diff_file(app_name,app_version):
	location = 'project/{}'.format(app_name)
	appvers = os.listdir(location)
	if len(appvers) > 1:

		#File change
		appvers.sort(reverse=True)
		l1, l2 = appvers[0], appvers[1]
		diff_file = '{}/{}/{}_{}'.format(location, l1, l1, l2)
		ret = diff_output('git diff --name-status --no-renames apkdb/{}/{}/smali_code/ apkdb/{}/{}/smali_code'.format(location, l1, location, l2))
		with open(diff_file, 'w') as w:
			w.write(ret)
		#number of line change
		r = ret.split('\n')
		line_change = {}
		for df in r:
			fname = df.split('smali_code/')[1]
			tchange = df.split('\t')[0]
			f1_location = 'apkdb/{}/{}/smali_code/{}'.format(location,l1,fname)
			f2_location = 'apkdb/{}/{}/smali_code/{}'.format(location,l2,fname)

			if tchange == 'M':
				line_change[fname] = get_line_change(diff_output('git diff --stat {} {}'.format(f1_location,f2_location)))
			elif tchange == 'D':
				line_change[fname] = get_line_change(diff_output('git diff --stat {} {}'.format(f1_location,'/dev/null')))
			elif tchange == 'A':
				line_change[fname] = get_line_change(diff_output('git diff --stat {} {}'.format('/dev/null',f2_location)))
		
		# line_change = parse_line_change(line_change)
		with open(diff_file + '_line','w') as fw:
			fw.write(str(line_change))

	else:
		logger.info("Project contain 1 version")

def get_line_change(filedata):
	finsertion = re.findall(r'(\d+) insertions',filedata)[0] if 'insertions' in filedata else 0
	fdeleteion = re.findall(r'(\d+) deletions',filedata)[0] if 'deletions' in filedata else 0
	return [finsertion,fdeleteion]



def create_project(app_name,app_version):
	logger.info('Create project folder: project/%s/%s'%(app_name,app_version))
	os.mkdir('project/%s/%s'%(app_name,app_version))
	os.system('mv %s.apk project/%s/%s/'%(app_name,app_name,app_version))
	make_smali_code(app_name,app_version)
	create_diff_file(app_name,app_version)
	#decompile(app_name,app_version)



def hexdump(src, length=16):
	FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
	lines = []
	for c in xrange(0, len(src), length):
		chars = src[c:c+length]
		while u'' in chars:
			chars.remove(u'')
		hex = ' '.join(["%02x" % (int(x) if int(x)>=0 else 0xff+int(x) )for x in chars])
		printable = ''.join(["%s" % ((int(x) <= 127 and FILTER[int(x)]) or '.') for x in chars])
		lines.append("%04x  %-*s  %s\n" % (c, length*3, hex, printable))
	return ''.join(lines)


def which(program):
	def is_exe(fpath):
		return file_exist(fpath)# and os.access(fpath, os.X_OK)

	fpath, fname = os.path.split(program)
	if fpath:
		if is_exe(program):
			return program
	else:
		for path in os.environ["PATH"].split(os.pathsep):
			exe_file = os.path.join(path, program)
			if os.path.isfile(exe_file):
				return exe_file
	return None


def cmd_get_output(cmd):
	# logger.info("CMD:"+cmd)
	process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr= subprocess.PIPE)
	result,error = process.communicate()
	if error:
		logger.warning(error)
	return result[:-1]


#TODO: ....
def diff_output(cmd):
	os.chdir('../')
	output = cmd_get_output(cmd)
	os.chdir('apkdb')
	return output

def make_smali_code(process_name,app_version):
	logger.info("Making smali code "+ process_name + "|"+app_version)

	os.system('unzip -q -o project/%s/%s/%s.apk -d project/tmp'%(process_name,app_version,process_name))
	
	all_dex = glob.glob('project/tmp/*.dex')
	if not len(all_dex):
		raise SystemExit("Cannot found any dex file")
	for dex_file in all_dex:
		os.system('java -jar baksmali.jar d %s -o project/%s/%s/smali_code/'%(dex_file,process_name,app_version))
	os.system('rm -rf project/tmp')
	logger.info("Smali code done")


def decompile(process_name,app_version):
	cmd_get_output('./jadx/bin/jadx -d project/%s/%s/java_decompiled/ project/%s/%s/%s.apk'%(process_name,app_version,process_name,app_version,process_name))


def basic_check():
	out = cmd_get_output('adb devices')
	if out == 'List of devices attached\n\n':
		raise SystemExit('Device not found')


def current_time():
	return str(time.time())



def unpack_apk(appname):
	os.system('apktool -f -s d %s.apk'%appname)
	appversion = get_app_version(appname)
	os.system('rm -rf %s'%appname)
	create_project(appname,appversion)
	return 'file uploaded successfully'


def render_file(filename):
	logger.info("Return file data {}".format(filename))
	with open(filename,'r') as f:
		data = f.read()
	return data

def get_diff_version(appver,checkver):
	try:
		check_ver_index = appver.index(checkver)
	except:
		return "ERROR cannot get this version code"
	logger.info("Get versionindex"+ str(check_ver_index))
	if len(appver) > check_ver_index + 1:
		return checkver,appver[check_ver_index+1]
	return "ERROR This is oldest version"


def in_black_list(data):
	for b in black_list:
		if data.startswith(b):
			return True
	return False