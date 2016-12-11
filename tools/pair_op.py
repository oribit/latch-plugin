import latch_sdk.latch as latch
import os, hashlib
from shutil import copyfile

COMMENT_CHAR = '#'
OPTION_CHAR =  '='
debugging = True


def backupFile(filename):
    backupfile = filename + '.2'
    if os.path.isfile(backupfile):
        copyfile(backupfile, filename + '.3')
    backupfile = filename + '.1'
    if os.path.isfile(backupfile):
        copyfile(backupfile, filename + '.2')
    backupfile = filename + '.1'
    copyfile(filename, backupfile)

def parse_config(filename):
    COMMENT_CHAR = '#'
    OPTION_CHAR =  '='
    options = {}
    f = open(filename)
    for line in f:
        # First, remove comments:
        if COMMENT_CHAR in line:
            # split on comment char, keep only the part before
            line, comment = line.split(COMMENT_CHAR, 1)
        # Second, find lines with an op tion=value:
        if OPTION_CHAR in line:
            option, value = line.split(OPTION_CHAR, 1)
            option = option.strip()
            value = value.strip()
            options[option] = value
    f.close()
    return options

def check_user(filename, user, password):
    user_ok = False
    f = open(filename)
    for line in f:
        line = line.strip('\n')
        data = line.split('=')
        if data[0] == user:
            p = hashlib.md5()
            p.update(password)
            user_ok = data[1] == p.hexdigest()
    f.close()
    return user_ok

filepath = os.path.realpath(__file__)
filepath = filepath[0:filepath.rindex('/')]
if "tools" in filepath:
    t = filepath.split('/')
    filepath = ''
    for i in t:
        if i and i != "tools":
            filepath = filepath + '/' + i

options = parse_config(filepath + '/latch.conf')

user = raw_input("Introduce username: ")
password = raw_input("Introduce password: ")
if not check_user(filepath + '/mosquitto.users', user, password):
    print "User/password not valid."
    exit()

while 1:
    print "What do you want to do?"
    print "1) Pairing new user"
    print "2) Unpair user"
    print "3) Exit"
    opt = raw_input("Please, choose an option: ")

    if opt == '1':
        tokenl = raw_input("Introduce token value from App:")
        print ("Paring app...")
        api = latch.Latch(options['app_id'], options['secret_key'])
        if not api is None:
            response = api.pair(tokenl)
            #for attr in dir(response):
            #    print "obj.%s = %s" % (attr, getattr(response, attr))

            if not response.error:
                f = open(filepath + '/latch.accounts', 'a')
                f.write(user + '=' + response.data['accountId'] + '\n')
                f.close()
                print "Paring DONE OK!"
            else:
                print "Error paring: ", response.error.get_code(), response.error.get_message()
        else:
            print "Error connecting Latch app"
    elif opt == '2':
        api = latch.Latch(options['app_id'], options['secret_key'])
        if api is not None:
            answer = raw_input("Are you sure you want to unpair the user " + str(user) + "? (yes/No)")
            if answer == 'yes':
                response = api.unpair(accountId)
                if responseLatch.get_error() == '':
                    print "User unpaired!"
                    f = open(filepath + '/latch.accounts')
                    all_lines = f.readlines()
                    f.close()
                    backupFile(filepath + '/latch.accounts')
                    f = open(filepath + '/latch.accounts', 'w')
                    for line in all_lines:
                        data = line.split('=')
                        if data[0] != user:
                            f.write(line)
                    f.close()
                else:
                    print "Error unpairing user ", responseLatch.get_error()
    elif opt == '3':
        break
exit()
