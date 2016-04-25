#!/usr/bin/python2.7

from __future__ import print_function

from archive import open_archive, FileSystem

from multiprocessing import Process
from threading import Thread

DO_CLEAN_FUNCTIONS = False

import collections
import marshal
import types
import termios
import shutil
import select
import random
import time
import sys
import tty
import os
import re
_stdout = sys.stdout
_stderr = sys.stderr
_stdin = sys.stdin

class CPU(Thread):
    def __init__(self, scope, code = ""):
        self.code = code
        self.scope = scope

        super(CPU, self).__init__()
        
        self.daemon = True

    def run(self):
        while True:
            #if self.code != "":
            if False:
                _stderr.write(self.code + "\n")
                _stderr.flush()

            exec self.code in self.scope
            self.code = ""
            time.sleep(0.01)

    def isAlive(self):
        return self.code != ""

"""def check_stdin(*args):
    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
        return sys.stdin.read(1)
    else:
        return ''"""
def check_stdin():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])    

def cleanerrorfunc(func):

    def cleaned_function(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return -1

    return cleaned_function


def cleanerrorgen(func):

    def cleaned_generator(*args, **kwargs):
        while True:
            try:
                yield func(*args, **kwargs)
            except StopIteration:
                raise
            except:
                yield -1

    return cleaned_generator


def force_clean_function(func):
    if type(func) is types.GeneratorType:
        return cleanerrorgen(func)
    else:
        return cleanerrorfunc(func)


def force_clean_class(cls):

    class CleanedClass(cls):

        def __getattribute__(self, attr_name):
            obj = super(CleanedClass, self).__getattribute__(attr_name)
            if hasattr(obj, '__call__'):
                return clean_function(obj)
            return obj

    return CleanedClass

if DO_CLEAN_FUNCTIONS:
    clean_function = force_clean_function
    clean_class = force_clean_class
else:
    clean_function = clean_class = cleanerrorgen = cleanerrorfunc = lambda x: x

def fetch_code(code):
    obj = marshal.loads(code)

    assert type(obj) == types.CodeType, "Object should be <code object>, is " + repr(type(obj))
    return obj

PATH_CHAR = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ012356789./'
file_devices = {'stdout': _stdout,
 'stderr': _stderr,
 '_stdin': _stdin}
function_devices = {'clock': time.time,
 'error': sys.exc_info,
 'stdin': check_stdin,
 'random': lambda : os.urandom(1)}

class Directory(object):
    pass

superpass = lambda: None

def bind_file(f):
    def file_wrapper(arg = None):
        if arg is None:
            return f.read(1)
        else:
            f.write(str(arg))
            f.flush()
    return file_wrapper

fs = open_archive("./fs.pya", False)
fs.magic.update({
    'stderr' : (superpass, bind_file(_stderr)),
    'stdout' : (superpass, bind_file(_stdout)),
    '_stdin' : (check_stdin, superpass),
    'clock'  : (time.time, superpass),
    'stdin'  : (bind_file(_stdin), superpass),
    'error'  : (sys.exc_info, superpass),
    'random' : (lambda : os.urandom(1), superpass),
    'sleep'  : (lambda: time.sleep(1), time.sleep)
    })

class SystemInterrupt(Exception):
    pass

builtins = {}

def log(*args):
    with open('../pyos.log', 'a') as log:
        for item in args:
            log.write(str(item))

        log.write('\n')

builtins['fetch_code'] = fetch_code
builtins['SystemInterrupt'] = SystemInterrupt
builtins['clean_function'] = clean_function
builtins['clean_class'] = clean_class
builtins['force_clean_function'] = force_clean_function
builtins['force_clean_class'] = force_clean_class
builtins['__module__'] = sys.__class__
builtins['Directory'] = Directory
builtins['__files__'] = fs
builtins['__log__'] = log
builtins['str'] = unicode
if len(sys.argv) > 1:
    builtins['__debug__'] = print
else:
    builtins['__debug__'] = lambda *args: None
keep = ('KeyboardInterrupt', 'int', 'dict', 'list', 'True', 'False', 'None', 'tuple', 'object', 'StopIteration', 'SyntaxError', 'Exception', 'compile', 'OSError', 'IOError', 'chr', 'ord', 'TypeError', 'repr', 'NameError', 'intern', 'ImportError', 'bool', 'float')
for builtin in keep:
    try:
        builtins[builtin] = __builtins__.__dict__[builtin]
    except AttributeError:
        builtins[builtin] = __builtins__[builtin]        

scope = {'__builtins__': builtins,
 '__name__': 'emucios'}
scope['__dict__'] = scope

header = re.compile("#\$ (\w+) = (\w+)")

def find_code(fs, code = None):
    code = code if code is not None else[]

    def recurse( (key, value) ):
        if isinstance(value, str):
            lines = value.split("\n")
	    if len(lines) > 3:
            	if lines[2] == "#$ CIOS HEADER $#":
		    data = {}
		    for line in lines:
			match = header.match(line)
		        if match is not None: 
		            name, define = match.group(1, 2)
		            data[name.lower()] = define
		    data["code"] = value
		    code.append(data)

    fs.walk(recurse)
    
    return code

def _main(f = None, data = None, arguments = None, handled = False):
    if not handled:
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            _main(f, data, arguments, True)
        except:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            fs.flush()
            raise
        else:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            fs.flush()
    if arguments is None:
        arguments = sys.argv
    else:
        arguments.insert(0, 'illegal')

    kernels = find_code(fs)

    if len(kernels) > 1:

        for num, kernel in enumerate(kernels, 0):
            print(num, ":", kernel.get("name", "Kernel"), kernel.get("version", ""))

        num = input("Kernel number: ")
        code = kernels[num]["code"]

        print(num)
    elif len(kernels) == 1:
        code = kernels[0]["code"]
    else:
        code = "raise OSError, \"No bootable medium detected.\""

    arguments[0] = "cios2"
    code = 'CIOS_MAGIC = ' + repr(arguments) + '\n' + code
    obj = compile(code, 'kernel', 'exec')
    
    cpus = [CPU(scope) for i in xrange(4)]
    for cpu in cpus:
        cpu.start()

    scope["__cpu__"] = cpus

    cpus[0].code = code

    while cpus[0].isAlive():
        time.sleep(0.1)

if __name__ == "__main__":
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        _main(handled = True)
    except:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        fs.flush()
        raise
    else:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    fs.flush()
