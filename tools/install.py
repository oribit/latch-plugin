import sys, os
from shutil import copyfile

print "Welcome to the installation process for Latch Plugin for Mosquitto."
print "Before starting this script, be sure you already created the application through the web of Latch as the documentation explains, and all prerequisites are matched."

applicationId = raw_input("Introduce the Application Id: ")
secret = raw_input("Introduce the secret: ")
filepath = os.path.realpath(__file__)
filepath = filepath[0:filepath.rindex('/')]
directory = raw_input("Introduce the directory where you want to install Latch Plugin (" + filepath + ")")
if directory == '':
    directory = filepath
pythonpath = sys.path
librarypath = ''
pyauth_path = raw_input("Introduce the path where pyauth plugin (auth_plugin_pyauth.so) is intalled: ")
temp = pyauth_path
temp = pyauth_path.split('/')
pyauth_path = '/'
for i in temp:
    if i != 'auth_plugin_pyauth.so' and i != '':
        pyauth_path = pyauth_path + i + '/'
pyauth_path = pyauth_path + 'auth_plugin_pyauth.so'
if not os.path.isfile(pyauth_path):
    print "File " + pyauth_path + " is not accesible. Installation aborted."
    exit(-1)

# Checking Python library path
for i in pythonpath:
    if "dist-packages" in i and "local" in i:
        librarypath = i
        break
if librarypath == '':
    for i in pythonpath:
        if "dist-packages" in i:
            librarypath = i
            break
if librarypath == '':
    print "Can't find any valid library path for new Python library. Installation aborted."
    exit(-1)

# Checking Mosquitto conf file
mosquitto_conf_file = '/etc/mosquitto/mosquitto.conf'
if not os.path.isfile(mosquitto_conf_file):
    print "Can't find Mosquitto configuration file in " + mosquitto_conf_file
    mosquitto_conf_file = raw_input("Please, introduce full path for mosquitto.conf: ")
    if not os.path.isfile(mosquitto_conf_file):
        print str(mosquitto_conf_file) + " can't be read. Installation aborted"
        exit(-1)

# Adding configuration to Mosquitto
f = open(mosquitto_conf_file, 'a')
    f.write('auth_plugin '+ pyauth_path + '\n')
    f.write('auth_opt_pyauth_module mosquitto_latch\n')
    f.write('auth_opt_latch_conf latch.conf\n')
f.close()

# Creating directories for latch configurationd and tools files
latch_conf_dir = '/etc/mosquitto/plugin/latch'
# Makedirs creates all directories in the path that doesn't exist
os.makedirs(latch_conf_dir + '/tools')
# Copying/creating files files
copyfile('./latch.conf', latch_conf_dir + '/latch.conf')
f = open(latch_conf_dir + '/latch.accounts', 'w')
f.close()
f = open(latch_conf_dir + '/latch.instances', 'w')
f.close()
f = open(latch_conf_dir + '/mosquitto.acl', 'w')
f.close()
f = open(latch_conf_dir + '/mosquitto.users', 'w')
f.close()
copyfile('./tools/instances_op.py', latch_conf_dir + '/tools/instances_op.py')
copyfile('./tools/pair_op.py', latch_conf_dir + '/tools/pair_op.py')
copyfile('./tools/users_op.py', latch_conf_dir + '/tools/users_op.py')


exit()
