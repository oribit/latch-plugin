# Utility to create, remove, modify users for plugin
#
import os, hashlib

user = raw_input("Introduce username:")
password = raw_input("Introduce password:")
p = hashlib.md5()
p.update(password)
password = p.hexdigest()

f = open('../conf/latch.users', 'a')
f.write(user + '=' + password + '\n')
f.close()
