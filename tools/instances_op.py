# File to work with latch.instances file
# This script allow:
# - Create instance
# - Remove instance
# - Sync with web in case any instance was created via web

import os
import latch_sdk.latch as latch
from shutil import copyfile

def backupFile(filename):
    backupfile = filename + '.2'
    if os.path.isfile(backupfile):
        copyfile(backupfile, filename + '.3')
    backupfile = filename + '.1'
    if os.path.isfile(backupfile):
        copyfile(backupfile, filename + '.2')
    backupfile = filename + '.1'
    copyfile(filename, backupfile)

filepath = os.path.realpath(__file__)
filepath = filepath[0:filepath.rindex('/')]
if "tools" in filepath:
    t = filepath.split('/')
    filepath = ''
    for i in t:
        if i and i != "tools":
            filepath = filepath + '/' + i

f = open(filepath + '/latch.conf')
for line in f:
    if not '#' in line:
        line = line.strip(' ')
        if line != '':
            line = line.split('=')
            if line[0] == 'app_id':
                appId = line[1].strip()
            if line[0] == 'secret_key':
                secret_key = line[1].strip()
            if line[0] == 'publish':
                publishId = line[1].strip()
            if line[0] == 'subscribe':
                subscribeId = line[1].strip()
f.close()

user = raw_input("Introduce username:")

f = open(filepath + '/latch.accounts')
accountId = ''
for line in f:
    if not '#' in line:
        data = line.split('=')
        if data[0] == user:
            accountId = data[1].strip()
            break
f.close()

if not accountId:
    exit("User invalid. There is no user " + str(user) + " configured in latch.accounts.")

while 1:
    print "What do you want to do?"
    print "1) Add instance."
    print "2) Remove instance."
    print "3) Sync with web."
    print "4) Exit."
    opt = raw_input("Please, choose an option: ")

    if opt == '1':
        newInstance = str(raw_input("Introduce instance name: "))
        api = latch.Latch(appId, secret_key)
        responseLatch = api.createInstance(newInstance, accountId)
        if responseLatch.get_error() == '':
            backupFile(filepath + '/latch.instances')
            f = open(filepath + '/latch.instances')
            all_lines = f.readlines()
            f.close()
            f = open(filepath + '/latch.instances', 'w')
            for line in all_lines:
                f.write(line)
            line = newInstance + ' ' + str(responseLatch.get_data()['instances'].keys()[0]) + ' ' + str(user) + '\n'
            f.write(line)
            f.close()
            print "Instance " + newInstance + " created succesfully."
        else:
            print 'ERROR: Latch not available to create instance. ERROR CODE:', responseLatch.get_error()

    elif opt == '2':
        print "Which instance do you want to delete?"
        f = open(filepath + '/latch.instances')
        i = 0
        instanceList = []
        all_lines = f.readlines()
        f.close()
        for line in all_lines:
            line = line.strip('\n')
            if line != '':
                data = line.split(' ')
                if data[2] == user:
                    i=i+1
                    instanceList.append([data[0], data[1]])
                    print str(i) + ') ' + data[0]
        if i > 0:
            opt = raw_input("Choose one: ")
            try:
                opt = int(opt)
            except:
                print "Value not correct."
                exit()
            if opt > 0 and opt <= len(instanceList):
                instanceId = instanceList[opt-1][1]
                opt = raw_input("Are you sure you want to remove instance '" + instanceList[opt-1][0] + "'(" + instanceId + ") ? (yes/NO) ")
                if opt == 'yes':
                    print 'DELETING Instance...'
                    api = latch.Latch(appId, secret_key)
                    responseLatch = api.deleteInstance(instanceId, accountId)
                    if responseLatch.get_error() == '':
                        print "Instance deleted"
                        backupFile(filepath + '/latch.instances')
                        f = open(filepath + '/latch.instances', 'w')
                        for line in all_lines:
                            data = line.split(' ')
                            if data[1] != instanceId:
                                f.write(line)
                        f.close()
                    else:
                        print 'ERROR: Latch not available to delete instance. ERROR CODE:', responseLatch.get_error()

            else:
                print "Value not correct."
        else:
            print "There is no instances associated to this user."
    elif opt == '3':
        api = latch.Latch(appId, secret_key)
        webList = api.getInstances(accountId)
        webList = webList.get_data()
        print "Instances found in web:"
        x = 0
        instancesWeb = []
        for i in webList:
            x=x+1
            instancesWeb.append([i, webList[i]['name']])
            print str(x) + '.- ' + i + ' (' + webList[i]['name'] + ')'
        print ""
        print "Instances found in file:"
        f = open(filepath + '/latch.instances')
        i = 0
        instanceList = []
        all_lines = f.readlines()
        f.close()
        for line in all_lines:
            line = line.strip('\n')
            if line != '':
                data = line.split(' ')
                if data[2] == user:
                    i=i+1
                    instanceList.append([data[0], data[1]])
                    print str(i) + '.- ' + data[1] + ' (' + data[0] + ')'
        print ""
        opt = raw_input("Do you want to sync local files with the web information? (Y/N)")
        if opt == 'Y':
            backupFile(filepath + '/latch.instances')
            f = open(filepath + '/latch.instances', 'w')
            for i in webList:
                data = webList[i]['name'] + ' ' + i + ' ' + user + '\n'
                f.write(data)
            f.close()
            print "Sync DONE!"
    elif opt == '4':
        break

exit()
