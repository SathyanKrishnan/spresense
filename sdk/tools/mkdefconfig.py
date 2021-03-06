#!/usr/bin/env python3
# -*- coding: utf-8 -*-
############################################################################
# tools/mkdefconfig.py
#
#   Copyright 2018, 2020 Sony Semiconductor Solutions Corporation
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name of Sony Semiconductor Solutions Corporation nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
############################################################################

import os
import sys
import logging
import re

is_not_set = re.compile(r'^# (?P<symbol>.*) is not set')
is_config = re.compile(r'(?P<symbol>.*)=(?P<value>.*)')

DEFCONFIG_HEADER = '''#
# This file is autogenerated: PLEASE DO NOT EDIT IT.
#
# You can use "make menuconfig" to make any modifications to the installed .config file.
# You can then do "make savedefconfig" to generate a new defconfig file that includes your
# modifications.
#'''

class Defconfig:

    def __init__(self, path=None):
        self.path = path
        self.opts = {}

    def load(self, path=None):
        if path == None:
            path = self.path
        if path == None or not os.path.exists(path):
            return -1

        with open(path, 'r') as f:
            for line in f:
                m = is_not_set.match(line)
                if m:
                    sym = m.group('symbol').replace('CONFIG_', '', 1)
                    self.opts[sym] = 'n'
                else:
                    m = is_config.match(line)
                    if m:
                        sym = m.group('symbol').replace('CONFIG_', '', 1)
                        self.opts[sym] = m.group('value')
                    else:
                        logging.debug('[IGNORE]: %s' % line.strip())

    def save(self, path=None):
        if path == None:
            path = self.path

        # Save config as defconfig, for default defconfig
        config = []
        for (sym, val) in sorted(self.opts.items()):
            if val == 'n':
                config += ['# CONFIG_%s is not set' % sym]
            else:
                config += ['CONFIG_%s=%s' % (sym, val)]

        with open(path, 'w') as f:
            print(DEFCONFIG_HEADER, file=f)
            print('\n'.join(sorted(config)), file=f)

    def save_diff(self, target, path=None):
        '''
        Create differences list from target defconfig.
        The configs will be stored into 3 lists as follows:

        plus : The option is existed in self, not in target
        changes : The option is existed both, but value is changed
        minus : The option is not existed in self, in target
        '''
        if path == None:
            path = self.path

        plus = []
        changes = []
        minus = []

        for (sym, val) in target.opts.items():
            if sym not in self.opts:
                minus.append('-%s=%s' % (sym, val))
        for (sym, val) in self.opts.items():
            if sym not in target.opts:
                plus.append('+%s=%s' % (sym, val))
            if sym in target.opts and target.opts[sym] != val:
                changes.append(' %s=%s->%s' % (sym, target.opts[sym], val))

        out = sorted(minus) + sorted(changes) + sorted(plus)
        with open(path, 'w') as f:
            print('\n'.join(out), file=f)

    def __repr__(self):
        r = []
        for (sym, val) in sorted(self.opts.items()):
            r += ['(%s = %s)' % (sym, val)]
        return ','.join(r)

def make_savedefconfig():
    ''' Run 'make savedefconfig' at specified directory
    '''
    command = 'make savedefconfig'
    if logging.getLogger().getEffectiveLevel() > logging.INFO:
        command += ' 2>&1 >/dev/null'

    logging.debug('command: "%s"', command)

    return os.system(command)

def confirm(msg):
    ''' Tell to user with msg
    '''
    while True:
        try:
            res = input(msg + ' (y/n)? ')
        except KeyboardInterrupt:
            print()
            sys.exit(0)
        if res == 'y':
            return True
        if res == 'n':
            return False

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(description='Make default config from current config')
    parser.add_argument('configname', metavar='<config name>', type=str, nargs=1,
                        help='configuration name')
    parser.add_argument('-k', dest='kernel', action='store_true',
                        help='DEPRECATED')
    parser.add_argument('-d', '--dir', type=str, nargs=1,
                        help='change configs directory')
    parser.add_argument('-y', action='store_true',
                        help='overwrite existing defconfig')
    parser.add_argument('--all', action='store_true',
                        help='DEPRECATED')
    parser.add_argument('--verbose', '-v', action='count',
                        help='verbose messages')

    opts = parser.parse_args()

    configname = opts.configname[0]

    loglevel = logging.WARNING
    if opts.verbose == 1:
        loglevel = logging.INFO
    if opts.verbose == 2:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)

    if opts.kernel:
        logging.warning("-k option is deprecated. Ignored.")
    if opts.all:
        logging.warning("--all option is deprecated. Ignored.")

    # If -d options has been specified, then replace base config directory to
    # specified ones.

    if opts.dir:
        path = os.path.realpath(opts.dir[0])
        if path.endswith('configs'):
            configdir = os.path.join(path)
        else:
            configdir = os.path.join(path, 'configs')
    else:
        configdir = os.path.join('configs')

    dotconfigpath = os.path.join('..', 'nuttx', '.config')
    if not os.path.exists(dotconfigpath):
        print("NuttX is not configured.")
        sys.exit(1)

    newconfigdir = os.path.join(configdir, configname)

    if os.path.exists(newconfigdir):
        if not os.path.isdir(newconfigdir):
            print("configuration couldn't saved.")
            sys.exit(1)
        else:
            if not opts.y:
                yes = confirm(configname + ' is already exists, overwrite? ')
                if not yes:
                    sys.exit(0)

    # Create defconfig file by savedefconfig, this target moves defconfig
    # from nuttx/ to sdk/.

    ret = make_savedefconfig()
    if ret:
        sys.exit(ret)

    os.makedirs(newconfigdir, exist_ok=True)

    newconfig = Defconfig(os.path.join(newconfigdir, 'defconfig'))
    newconfig.load('defconfig')

    if '/' not in configname:
        newconfig.save()
    else:
        baseconfig = Defconfig(os.path.join(configdir, 'default', 'defconfig'))
        baseconfig.load()
        newconfig.save_diff(baseconfig)

    os.remove('defconfig')
