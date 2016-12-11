import os
import paho.mqtt.client as mqtt
import mosquitto_auth as mauth

from shutil import copyfile

DEBUG=0

def pdebug(DEBUGp, *text):
    global DEBUG
    DEBUG=DEBUGp
    if DEBUGp:
        print "[#DEBUG]", text

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

def parse_acl_file(filename):
    dictACLs = {}
    f = open(filename)
    for line in f:
        # The character # is the wildcard char for MQTT, so the comment is
        # two ##
        if "##" in line:
            line, comment = line.split("##", 1)
        # Checking tabs
        line = line.replace("\t", " ")
        line = line.strip()

        if line != "":
            acl, users = line.split(" ", 1)
            users = users.replace(" ", "")
            dictACLs[acl] = users.split(',')
    f.close()
    return dictACLs

def parse_instances_file(filename):
    dictInsta = {}
    f = open(filename)
    for line in f:
        line = line.strip()
        if line != "":
            topic, insta, user = line.split(" ", 2)
            if dictInsta.has_key(user):
                dictInsta[user].append([insta, topic])
            else:
                dictInsta[user] = [[insta, topic]]
    f.close()
    return dictInsta

def checkLatch(api, username, account_id, topic, operation_id, dInstances, default_action, PUBsub, clientMQTT):
    global DEBUG

    latchResponse = api.status(account_id)
    pdebug(DEBUG, "Checking Latch", latchResponse)
    # Checking first general status with APP ID
    if latchResponse.error:
        if default_action == 'open':
            pdebug(DEBUG, "Latch ERROR but default_action = open. Continuing.", latchResponse)
            return True
        else:
            print('#LATCH: Latch not available and default_action is not open. Message not delivered.(Error code: ', latchResponse.get_error(),')')
            clientMQTT.publish('LATCH/status', str(topic) + ',ND=1')
            clientMQTT.loop()
            clientMQTT.loop()
            return False

    latchData = latchResponse.get_data()
    if latchData['operations'].values()[0]['status'] == 'off':
        print('#LATCH: Latch for application ON for user:' + username + '. Message not delivered.')
        clientMQTT.publish('LATCH/status', str(topic) + ',ND=2')
        clientMQTT.loop()
        clientMQTT.loop()
        return False

    # Check if operation is ON
    latchResponse = api.operationStatus(account_id, operation_id)
    if latchResponse.get_error() == '':
        latchData = latchResponse.get_data()
        if latchData['operations'][operation_id]['status'] == 'off':
            print '#LATCH: Latch for', 'Publish' if PUBsub else 'Subscribe', 'ON for user ' + username + '. Message NOT delivered.'
            clientMQTT.publish('LATCH/status', str(topic) + ',ND=2')
            clientMQTT.loop()
            clientMQTT.loop()
            return False
    else:
        if default_action == 'open':
            print '#LATCH: WARNING: Latch not available for', 'Publish' if PUBsub else 'Subscribe', 'operation. Using default_action configuration. Message delivered. ERROR CODE:', latchResponse.get_error()
            return True
        else:
            print '#LATCH: ERROR: Latch not available for', 'Publish' if PUBsub else 'Subscribe', 'operation and default_action is not open. Message NOT delivered. ERROR CODE:', latchResponse.get_error()
            clientMQTT.publish('LATCH/status', str(topic) + ',ND=1')
            clientMQTT.loop()
            clientMQTT.loop()
            return False

    # Operation OFF, checking topics
    # Looking if the user has instances
    pdebug(DEBUG, "Instances:", dInstances)
    if username in dInstances:
        listInstances = dInstances[username]
        for insta in listInstances:
            # We need to go through all instances to follow MQTT hierarchy.
            # Only when all of them are passed, the message can be delivered (firewall style)
            # list = instace_id, topic
            if mauth.topic_matches_sub(insta[1], topic):
                latchResponse = api.instanceStatus(insta[0], account_id)
                if latchResponse.get_error() == '':
                    latchData = latchResponse.get_data()
                    if latchData['operations'][insta[0]]['status'] == 'off':
                        print '#LATCH: Latch for topic "' + topic + '" and username', username, 'ON. Message NOT delivered.'
                        clientMQTT.publish('LATCH/status', str(topic) + ',ND=2')
                        clientMQTT.loop()
                        clientMQTT.loop()
                        return False
                else:
                    if default_action == 'open':
                        print '#LATCH: WARNING: Latch not available for Instance:', topic, ' Using default_action configuration. Message delivered. ERROR CODE:', latchResponse.get_error()
                        return True
                    else:
                        print 'ERROR: Latch not available for Instance:', topic, ' Message NOT published. ERROR CODE:', latchResponse.get_error()
                        clientMQTT.publish('LATCH/status', str(topic) + ',ND=1')
                        clientMQTT.loop()
                        clientMQTT.loop()
                        return False

    return True

def createDynInstance(api, account_id, username, topic, filepath):
    global DEBUG

    pdebug(DEBUG, 'instances=' + topic, account_id)
    responseLatch = api.createInstance(topic, account_id)
    if responseLatch.get_error() == '':
        instance_id = responseLatch.get_data()['instances'].keys()[0]
        f = open(filepath + '/latch.instances', 'a')
        f.write(topic + " " + instance_id + " " + username + "\n")
        f.close()
    else:
        print '#ERROR: Latch not available to create new Instance:', topic, '. ERROR CODE:', responseLatch.get_error()
        return False

    return True

def dynPairing (api, token, username, filepath):
    global DEBUG

    latchResponse = api.pair(token)
    if latchResponse.error:
        print '#ERROR pairing user', username, '(ERROR CODE:', latchResponse.error.get_code(), latchResponse.error.get_message(), ')'
        return False
    f = open(filepath + '/latch.accounts', 'a')
    f.write(username + '=' + latchResponse.data['accountId'] + '\n')
    f.close()
    pdebug(DEBUG,"Paring DONE OK")

    return True

def dynUnpairing (api, accountId, username, filepath):
    global DEBUG

    latchResponse = api.unpair(accountId)
    if latchResponse.error:
        print '#ERROR unpairing user', username, '(ERROR CODE:', latchResponse.error.get_code(), latchResponse.error.get_message(), ')'
        return False

    # Update file latch.accounts
    backupFile(filepath + '/latch.accounts')
    f = open(filepath + '/latch.accounts', 'r')
    all_lines = f.readlines()
    f.close()
    f = open(filepath + '/latch.accounts', 'w')
    for line in all_lines:
        data = line.split('=')
        if data[1].strip('\n') != accountId:
            f.write(line)
    f.close()

    # Update files with instances
    backupFile(filepath + '/latch.instances')
    f = open(filepath + '/latch.instances', 'r')
    all_lines = f.readlines()
    f.close()
    f = open(filepath + '/latch.instances', 'w')
    for line in all_lines:
        data = line.split(' ')
        if data[2].strip('\n') != username:
            f.write(line)
    f.close()

    pdebug(DEBUG, "Unpair DONE OK")
