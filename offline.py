import os
import sys
from utils import *

apkname = sys.argv[1]
appname= apkname.split('.apk')[0]

unpack_apk(appname)
# create_diff_file(appname,'5036003')