# Mosquito auth plugin for Latch v0.1
#
# Author: Alvaro Caso (acaso@ixeya.com)

from sys import exit
from sys import stderr
import os, hashlib
import paho.mqtt.client as mqtt
import threading, time

from mosquitto_latch_bag import *
import mosquitto_auth as mauth
import latch_sdk.latch as latch

api = None
application_id = ''
dUsers = {}
dAccounts = {}
dACLs = {}
dInstances = {}
instance_mode = 'static'
security_mode='open'
default_action='open'
latchAvailable=True
configfilepath='/etc/mosquitto/plugin/latch'
DEBUG=0
# MQTT
clientMQTT = mqtt.Client()

class mqttBackground(object):
    #Calculate different data in the background and display it. The update is every 5 seconds.

    def __init__(self, clientMQTT):
        self.clientMQTT = clientMQTT
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        time.sleep(5)
        self.clientMQTT.connect("127.0.0.1", 1883, 60)
        self.clientMQTT.username_pw_set("latch_plugin")
        self.clientMQTT.loop_start()

def plugin_init(opts):
    global DEBUG, configfilepath
    global api, application_id, publish_id, subscribe_id, latchAvailable, default_action
    global dAccounts
    global dACLs
    global dUsers, security_mode
    global dInstances, instance_mode
    global clientMQTT

    latch_conf_file = ''
    # Checking plugin options
    for eachopt in opts:
        if eachopt[0] == 'debug':
            DEBUG = 1
        elif eachopt[0] == 'latch_conf':
            latch_conf_file = eachopt[1]

    latch_conf_file = configfilepath + '/' + latch_conf_file
    pdebug(DEBUG, 'plugin_init', opts)
    if not latch_conf_file:
        # No file defined in mosquitto conf file
        exit('ERROR: Please, use "auth_opt_latch_conf" inside mosquitto configuration file, to configure Latch config file path.')

    if not os.path.isfile(latch_conf_file) or not os.access(latch_conf_file, os.R_OK):
        exit('ERROR: Latch config file "' + latch_conf_file + '" is not accessible.')

    # Parsing Latch config file
    optionsLatch = parse_config(latch_conf_file)

    # Loading accounts ID
    if not os.path.isfile(configfilepath + '/latch.accounts') or not os.access(configfilepath + '/latch.accounts', os.R_OK):
        exit('ERROR: Latch account file "' + configfilepath + '/latch.accounts is not accessible.')
    else:
        dAccounts = parse_config(configfilepath + '/latch.accounts')

    if optionsLatch.has_key('instance_mode'):
        instance_mode = optionsLatch['instance_mode'].lower()

    # Loading users
    if optionsLatch.has_key('security_mode'):
        security_mode = optionsLatch['security_mode'].lower()
    if not os.path.isfile(configfilepath + '/mosquitto.users') or not os.access(configfilepath + '/mosquitto.users', os.R_OK):
        exit('ERROR: Latch users file "' + configfilepath + '/mosquitto.users is not accessible.')
    else:
        dUsers = parse_config(configfilepath + '/mosquitto.users')
        pdebug(DEBUG, "Users: ", dUsers)

    # Loading ACLs
    if not os.path.isfile(configfilepath + '/mosquitto.acl') or not os.access(configfilepath + '/mosquitto.acl', os.R_OK):
        pdebug(DEBUG, 'ACLs file "' + configfilepath + '/mosquitto.acl is not accessible.')
    else:
        dACLs = parse_acl_file(configfilepath + '/mosquitto.acl')
    pdebug(DEBUG, "ACLs: ", dACLs)

    # Loading Instances
    if not os.path.isfile(configfilepath + '/latch.instances') or not os.access(configfilepath + '/latch.instances', os.R_OK):
        exit('ERROR: instances file "' + configfilepath + '/latch.instances is not accessible.')
    else:
        dInstances = parse_instances_file(configfilepath + '/latch.instances')
    pdebug(DEBUG, "instances: ", dInstances)


    # More options
    if optionsLatch.has_key('default_action'):
        default_action = optionsLatch['default_action'].lower()

    if optionsLatch.has_key('app_id') and \
    optionsLatch.has_key('publish') and \
    optionsLatch.has_key('subscribe') and \
    optionsLatch.has_key('secret_key'):
        application_id = optionsLatch['app_id']
        publish_id = optionsLatch['publish']
        subscribe_id = optionsLatch['subscribe']
        secret_key = optionsLatch['secret_key']
        api = latch.Latch(application_id, secret_key)
    else:
        lathAvailable = False
        if default_action != 'open':
            exit('ERROR: Latch is not available and default_action is not configured as open.')
    mqttBackground(clientMQTT)

def plugin_cleanup():
    pdebug(DEBUG, 'plugin_cleanup')
    clientMQTT.disconnect()
    clientMQTT.loop_stop()

def unpwd_check(username, password):
    global dUsers, security_mode
    # This procedure is called only if a user is provided when the publish is
    # done.
    # For the subscriber only is done one time in the beginnig, when it
    # connects to the broker.
    pdebug(DEBUG, 'unpwd_check', dUsers)

    if security_mode == 'password':
        okuser = False
        if username in dUsers:
            p = hashlib.md5()
            p.update(password)
            okuser = dUsers[username] == p.hexdigest()
        else:
            pdebug(DEBUG, 'username not found')
        if not okuser:
            print '#PASSWORD: security_mode configured, user and password do not match with any user stored in mosquitto.users. Message not delivered.'
            return False

    return True

def acl_check(clientid, username, topic, access):
    global api, usersLatch, publish_id, subscribe_id, default_action
    global dUsers, security_mode
    global dAccounts
    global dACLs
    global dInstances, instance_mode
    global configfilepath
    global clientMQTT


    pdebug(DEBUG, 'acl_check', clientid, username, topic, 'PUBLISH' if access == mauth.MOSQ_ACL_WRITE else 'SUBSCRIBE')

    # Checking users. The user/password is checked in unpwd_check, but if there
    # is no user, it's never called, so we need to check it
    if security_mode == 'password' and username == None:
        if access == mauth.MOSQ_ACL_READ:
            print '#ACL: security_mode configured but not user/password provided for a subscriber. Message not delivered.'
        elif access == mauth.MOSQ_ACL_WRITE:
            print '#ACL: security_mode configured but not user/password provided for a publisher. Message not delivered.'
        return False

    # Checking ACLs
    for acl in dACLs:
        if mauth.topic_matches_sub(acl, topic):
            pdebug(DEBUG, 'ACL MATCH', acl)
            if not username in dACLs[acl]:
                print '#ACL configured for topic ' + topic + ' but user does not match. Message not delivered'
                return False

    # Checking Latch topic
    if topic.startswith('LATCH'):
        if access == mauth.MOSQ_ACL_WRITE:
            # MODE dynamic_pairing
            if topic.startswith('LATCH/pairing'):
                pdebug(DEBUG, 'dynamic pairing', topic, username)
                notneed, token = topic.split("=", 1)
                if username in dAccounts:
                    print '#ERROR: Request dynamic pairing for user', username, 'but this user is already paired.'
                    return False
                if dynPairing(api, token, username, configfilepath):
                    dAccounts = parse_config(configfilepath + '/latch.accounts')
                    return True
                else:
                    return False
            elif topic.startswith('LATCH/unpairing'):
                pdebug(DEBUG, 'dynamic unpairing', topic, username)
                if username in dAccounts:
                    notneed, password = topic.split("=", 1)
                    p = hashlib.md5()
                    p.update(password)
                    okuser = dUsers[username] == p.hexdigest()
                    if okuser:
                        if dynUnpairing(api, dAccounts[username], username, configfilepath):
                            dAccounts = parse_config(configfilepath + '/latch.accounts')
                            return True
                        else:
                            return False
                    else:
                        print '#ERROR: Password provided for user', username, 'to do the unpair not maching.'
                        return False
                else:
                    print'#ERROR: User', username, 'is not paired.'
                    return False
            # Dynamic instances
            elif topic.startswith('LATCH/create_instance'):
                # Instances need a user
                if username in dAccounts:
                    pdebug(DEBUG, 'create instance through topic LATCH/create_instance', topic, dAccounts[username], username)
                    notneed, topic = topic.split("=", 1)
                    if createDynInstance(api, dAccounts[username], username, topic, configfilepath):
                        dInstances = parse_instances_file(configfilepath + '/latch.instances')
                        return True
                    else:
                        return False
            elif topic.startswith('LATCH/status'):
                return True
        elif access == mauth.MOSQ_ACL_READ:
            if topic.startswith('LATCH/status'):
                return True
            else:
                # The pluggin reserves LATCH as an internal topic, it's not allowed
                # to have any subscriber to this topic but for the LATCH/status that
                # is used to control LATCH activities
                print 'Topic LATCH is reserverd and can not be used for a subscriber'
                return False

    # Processing PUBLISH
    if access == mauth.MOSQ_ACL_WRITE and username in dAccounts:
        ok = checkLatch(api, username, dAccounts[username], topic, publish_id, dInstances, default_action, True, clientMQTT)
        if not ok:
            return False
        else:
            # Checking if we have to add the instance
            # only if the message was delivered
            if instance_mode == 'dynamic':
                lInstanceExist = False
                if username in dInstances:
                    for instancesUser in dInstances[username]:
                        if topic in instancesUser:
                            lInstanceExist = True
                if not lInstanceExist:
                    pdebug(DEBUG, 'create instance', topic, dAccounts[username], username)
                    if createDynInstance(api, dAccounts[username], username, topic , configfilepath):
                        dInstances = parse_instances_file(configfilepath + '/latch.instances')
    # Processing SUBSCRIBE
    elif access == mauth.MOSQ_ACL_READ and username in dAccounts:
        ok = checkLatch(api, username, dAccounts[username], topic, subscribe_id, dInstances, default_action, False, clientMQTT)
        if not ok:
            return False

    # Everythin OK, message delivered
    pdebug(DEBUG, 'Message published. Topic:', topic)
    return True

def security_init(opts, reload):
    pdebug (DEBUG, 'security_init', 'reload:', reload, 'options:', opts)


def security_cleanup(reload):
    pdebug (DEBUG, 'security_cleanup', 'reload:', reload)
