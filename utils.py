# -*- mode: python; coding: utf-8 -*-

__author__    = "Alvaro Lopez Ortega"
__email__     = "alvaro@alobbs.com"
__copyright__ = "Copyright (C) 2013 Alvaro Lopez Ortega"

import os
import sys
import time
import select
import hashlib
import subprocess

import xattr


#
# Pathsx
#
def get_downloads_default():
    return os.path.expanduser ("~/Downloads/Pasalo")

def get_basedir_default():
    return os.path.expanduser ('~/.pasalo')

def get_config_fp (confdir=None):
    confdir = confdir or get_basedir_default()
    return os.path.join (confdir, 'config.json')

#
# Main & CLI
#
def assert_cli_args (params, ns):
    missing = []
    for p in params:
        if not ns.__dict__.get(p):
            missing.append (p)

    if missing:
        print >> sys.stderr, "ERROR: %s paramaters must be provided" % (' ,'.join(['--%s'%(p) for p in missing]))
        raise SystemExit

#
# MD5 file attr
#
def md5_file (fullpath, blocksize=1024*1024):
    afile = open(fullpath, 'rb')
    hasher = hashlib.md5()
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()

def set_md5_attr (fullpath, force=False):
    set_md5 = force

    attrs = xattr.listxattr (fullpath)
    if not 'md5' in attrs or \
       not 'md5_time' in attrs:
        set_md5 = True
    else:
        mtime     = os.path.getmtime (fullpath)
        attr_md5  = xattr.getxattr (fullpath, 'md5')
        attr_time = xattr.getxattr (fullpath, 'md5_time')

        if mtime > attr_md5:
            set_md5 = True

    if set_md5:
        xattr.setxattr (fullpath, 'md5_time', str(time.time()))
        xattr.setxattr (fullpath, 'md5', md5_file(fullpath))


def getxattr (fullpath, attr, default=None):
    try:
        return xattr.getxattr (fullpath, attr)
    except IOError, e:
        # Attribute not found
        if e.errno == 93:
            return default
        raise

def format_size (num_bytes):
    KiB = 1024
    MiB = KiB * KiB
    GiB = KiB * MiB
    TiB = KiB * GiB
    PiB = KiB * TiB
    EiB = KiB * PiB
    ZiB = KiB * EiB
    YiB = KiB * ZiB

    if num_bytes > YiB:
        return '%.3g YiB' %(num_bytes / YiB)
    elif num_bytes > ZiB:
        return '%.3g ZiB' %(num_bytes / ZiB)
    elif num_bytes > EiB:
        return '%.3g EiB' %(num_bytes / EiB)
    elif num_bytes > PiB:
        return '%.3g PiB' %(num_bytes / PiB)
    elif num_bytes > TiB:
        return '%.3g TiB' %(num_bytes / TiB)
    elif num_bytes > GiB:
        return '%.3g GiB' %(num_bytes / GiB)
    elif num_bytes > MiB:
        return '%.3g MiB' %(num_bytes / MiB)
    elif num_bytes > KiB:
        return '%.3g KiB' %(num_bytes / KiB)
    return '%d' %(num_bytes)


class PopenAsync (subprocess.Popen):
    def __init__(self, argv, stdin = subprocess.PIPE, timeout=0):
        self.timeout = timeout
        subprocess.Popen.__init__(self, argv, shell = True,
                                  stdin  = stdin,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE)

    def read(self, n = 1):
        poll = select.poll()
        poll.register(self.stdout.fileno(), select.POLLIN or select.POLLPRI)
        fd = poll.poll(self.timeout)
        if len(fd):
            f = fd[0]
            if f[1] > 0:
                return self.stdout.read(n)

    def write(self, data):
        poll = select.poll()
        poll.register(self.stdin.fileno(), select.POLLOUT)
        fd = poll.poll(self.timeout)
        if len(fd):
            f = fd[0]
            if f[1] > 0:
                self.stdin.write(data)

    def close(self):
        self.terminate()
        self.wait()
