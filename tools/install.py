import sys, os
from shutil import copyfile
from shutil import copytree

print "Welcome to the installation process for Latch Plugin for Mosquitto."
print "Before starting this script, be sure you already created the application through the Latch web as the documentation explains,"
print "and all prerequisites are matched."

applicationId = raw_input("Introduce the Application Id: ")
secret = raw_input("Introduce the secret: ")

directory = os.path.realpath(__file__)
directory = directory[0:directory.rindex('/')]
if "tools" in directory:
    t = directory.split('/')
    directory = ''
    for i in t:
        if i and i != "tools":
            directory = directory + '/' + i

# Pyauth library
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
copyfile('./latch.conf.example', latch_conf_dir + '/latch.conf')
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

# Creating links for python files
os.system('ln -s ' + directory + '/latch_sdk ' + librarypath + '/latch_sdk')
os.system('ln -s ' + directory + '/mosquitto_latch.py ' + librarypath + '/mosquitto_latch.py')
os.system('ln -s ' + directory + '/mosquitto_latch_bag.py ' + librarypath + '/mosquitto_latch_bag.py')

# Creating operations publish/subscribe
import latch_sdk.latch as latch
api = latch.Latch(applicationId, secret)
latchResponse = api.createOperation(applicationId, 'publish', 'DISABLED', 'DISABLED')
if not latchResponse.get_error() == '':
    print 'Error creating Publish operation. Installation aborted at 90%.'
    print 'Please, edit the file', latch_conf_dir + '/latch.conf', 'adding the values for app_id, secret_key, publish and subscribe operations.'
    exit(-1)
publishId = latchResponse.get_data()
publishId = publishId['operationId']

latchResponse = api.createOperation(applicationId, 'subscribe', 'DISABLED', 'DISABLED')
if not latchResponse.get_error() == '':
    print 'Error creating Subscribe operation. Installation aborted at 90%.'
    print 'Please, edit the file', latch_conf_dir + '/latch.conf', 'adding the values for app_id, secret_key, publish and subscribe operations.'
    exit(-1)
subscribeId = latchResponse.get_data()
subscribeId = subscribeId['operationId']

# Preparing latch.conf
f = open(latch_conf_dir + '/latch.conf')
all_lines = f.readlines()
f.close()
f = open(latch_conf_dir + '/latch.conf', 'w')
for line in all_lines:
    if line.startswith('app_id='):
        line = line.strip('\n')
        tline = line.split('=')
        tline[1] = applicationId
        line = tline[0] + '=' + tline[1] + '\n'
    elif line.startswith('secret_key='):
        line = line.strip('\n')
        tline = line.split('=')
        tline[1] = secret
        line = tline[0] + '=' + tline[1] + '\n'
    elif line.startswith('publish='):
        line = line.strip('\n')
        tline = line.split('=')
        tline[1] = publishId
        line = tline[0] + '=' + tline[1] + '\n'
    elif line.startswith('subscribe='):
        line = line.strip('\n')
        tline = line.split('=')
        tline[1] = subscribeId
        line = tline[0] + '=' + tline[1] + '\n'
    f.write(line)
f.close()

# Changing permissions
os.system('chown -R mosquitto ' + latch_conf_dir + '/*')

print 'Congratulations! Installation finished with no errors.'
print 'Please, remember you need to create a user to start to user Latch.'
print 'You can do it with executing: python ./tools/users_op.py'
exit(0)
