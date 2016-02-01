#!/usr/bin/python2.7

from __future__ import print_function
DO_CLEAN_FUNCTIONS = False
DEBUG = False
import collections
import types
import termios
import shutil
import select
import random
import time
import sys
import tty
import os
os.chdir('/home/elijah/Git/emucios/emucios 0.x/')
_stdout = sys.stdout
_stderr = sys.stderr
_stdin = sys.stdin

def remove_item(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def check_stdin(*args):
    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
        return sys.stdin.read(1)
    else:
        return ''


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


@clean_class

class FileSystem(object):

    def __init__(self, path, parent = None, livecd = False):
        self.path = path
        self.parent = parent
        self.livecd = livecd

    def next(self):
        return self

    def get(self, name):
        self.__clean()
        if name == '..':
            yield self.parent
        elif name == '.':
            yield self
        if self.path == './dev' and name in function_devices:
            while True:
                yield function_devices[name]()

        elif self.path == './dev' and name in file_devices:
            while True:
                yield file_devices[name].read(1)

        else:
            name = name.replace('/', '_')
            try:
                ls = os.listdir(os.path.join(self.path, name))
            except OSError as e:
                if '[Errno 20]' in str(e):
                    try:
                        with open(os.path.join(self.path, name)) as f:
                            while True:
                                yield f.read(1)

                    except:
                        raise

                else:
                    raise IOError, 'File ' + name + ' does not exist'

            if name == 'livecd' and self.livecd:
                yield FileSystem('../livecd', self)
            else:
                yield FileSystem(os.path.join(self.path, name), self)

    def __getitem__(self, name):
        try:
            ls = os.listdir(os.path.join(self.path, name))
        except OSError as e:
            return self.get(name)

        next = FileSystem(os.path.join(self.path, name), self)
        if False:
            log(next.path)
            log(os.path.join(self.path, name))
            log()
        return next

    def __setitem__(self, name, value):
        self.__clean()
        name = name.replace('/', '_')
        if self.path == './dev':
            if name in function_devices:
                function_devices[name](value)
                return
            if name in file_devices:
                file_devices[name].write(str(value)[0])
                file_devices[name].flush()
                return
        if type(value) is Directory:
            os.mkdir(os.path.join(self.path, name))
            return
        try:
            if value:
                with open(os.path.join(self.path, name), 'a') as f:
                    f.write(str(value)[0])
            else:
                open(os.path.join(self.path, name), 'w').close()
        except IOError:
            raise IOError, 'File ' + name + ' does not exist'

    def set(self, name, value):
        self.__setitem__(name, value)

    def __delitem__(self, name):
        self.__clean()
        name = name.replace('/', '_')
        if self.path == './dev':
            return
        remove_item(os.path.join(self.path, name))

    def rm(self, name):
        self.__delitem__(name)

    def listdir(self):
        self.__clean()
        if self.path.startswith('./dev'):
            return os.listdir(self.path) + file_devices.keys() + function_devices.keys()
        if self.path == '.':
            return os.listdir(self.path) + ['livecd']
        return os.listdir(self.path)

    def __clean(self):
        self.path = self.path.replace('..', '.')
        if self.path.startswith('/'):
            self.path = '.' + self.path
        clean_path = ''
        for char in self.path:
            if char in PATH_CHAR:
                clean_path += char

        self.path = clean_path

    def __repr__(self):
        return repr(self.listdir())


fs = FileSystem('.')

class SystemInterrupt(Exception):
    pass


os.chdir('./fs/')
builtins = {}

def log(*args):
    with open('../pyos.log', 'a') as log:
        for item in args:
            log.write(str(item))

        log.write('\n')


builtins['SystemInterrupt'] = SystemInterrupt
builtins['clean_function'] = clean_function
builtins['clean_class'] = clean_class
builtins['force_clean_function'] = force_clean_function
builtins['force_clean_class'] = force_clean_class
builtins['__module__'] = sys.__class__
builtins['Directory'] = Directory
builtins['__files__'] = fs
builtins['__log__'] = log
builtins['print'] = None
if DEBUG:
    builtins['__debug__'] = print
keep = ('KeyboardInterrupt', 'str', 'int', 'dict', 'list', 'True', 'False', 'None', 'tuple', 'object', 'StopIteration', 'SyntaxError', 'Exception', 'compile', 'OSError', 'IOError', 'chr', 'ord', 'TypeError', 'repr', 'NameError', 'intern', 'ImportError', 'bool', 'float')
for builtin in keep:
    try:
        builtins[builtin] = __builtins__.__dict__[builtin]
    except AttributeError:
        builtins[builtin] = __builtins__[builtin]        

scope = {'__builtins__': builtins,
 '__name__': 'kernel'}
scope['__dict__'] = scope

def _main(f = None, data = None, arguments = None, handled = False):
    try:
        __exec__
    except:
        pass
    else:
        if not handled:
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                _main(f, data, arguments, True)
            except:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                raise
            else:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    if arguments is None:
        arguments = sys.argv
    else:
        arguments.insert(0, 'emucios')
        
    if os.path.exists('sys/kernel'):
        with open('sys/kernel') as f:
            code = f.read()
    elif os.path.exists('../livecd/kernel'):
        with open('../livecd/kernel') as f:
            code = f.read()
    else:
        code = "raise OSError, 'No bootable medium detected'"
    code = 'CIOS_MAGIC = ' + repr(arguments) + '\n' + code
    obj = compile(code, 'kernel', 'exec')
    exec obj in scope

try:
    __exec__
except:
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        _main()
    except:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        raise
    else:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
