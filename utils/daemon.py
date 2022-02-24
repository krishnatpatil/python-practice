# -*- coding: utf-8 -*-
# Copyright (c) 2009-2014 Sauce Labs Inc
#
# Portions taken from twistd:
#
# Copyright (c) 2001-2009
# Allen Short
# Andrew Bennetts
# Apple Computer, Inc.
# Benjamin Bruheim
# Bob Ippolito
# Canonical Limited
# Christopher Armstrong
# David Reid
# Donovan Preston
# Eric Mangold
# Itamar Shtull-Trauring
# James Knight
# Jason A. Mobarak
# Jean-Paul Calderone
# Jonathan Lange
# Jonathan D. Simms
# JÃ¼rgen Hermann
# Kevin Turner
# Mary Gardiner
# Matthew Lefkowitz
# Massachusetts Institute of Technology
# Moshe Zadka
# Paul Swartz
# Pavel Pergamenshchik
# Ralph Meijer
# Sean Riley
# Software Freedom Conservancy
# Travis B. Hartwell
# Thomas Herve
# Eyal Lotem
# Antoine Pitrou
# Andy Gayton
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# basic usage
#
# import Utils.daemon as daemon
#
# # run using pidfile to check if already running
# daemon.daemonize(pidfile = '/tmp/daemon.pid')
#
# # or run using signature string that matches running process name
# # to check if already running
# daemon.daemonize(pidsignature = 'process matching string')
#
# # or run using pidfile double checked against process signature
# daemon.daemonize(pidfile = '/tmp/daemon.pid',
#     pidsignature = 'process matching string')

import os
import sys
import errno
import subprocess


def basic_daemonize():
    # See http://www.erlenstar.demon.co.uk/unix/faq_toc.html#TOC16
    if os.fork():  # launch child and...
        os._exit(0)  # kill off parent
    os.setsid()
    if os.fork():  # launch child and...
        os._exit(0)  # kill off parent again.
    os.umask(0o022)  # Don't allow others to write
    null = os.open('/dev/null', os.O_RDWR)
    for i in range(3):
        try:
            os.dup2(null, i)
        except OSError as e:
            if e.errno != errno.EBADF:
                raise
    os.close(null)


def writePID(pidfile):
    if not pidfile:
        return
    f = None
    try:
        f = open(pidfile, 'wb')
        f.write(str(os.getpid()))
    finally:
        if f:
            f.close()
    if not os.path.exists(pidfile):
        raise Exception("pidfile %s does not exist" % pidfile)


def checkPID(pidfile, pidsignature):
    if (not pidfile) and (not pidsignature):
        return

    if pidfile and os.path.exists(pidfile):
        f = None
        pid = None

        try:
            f = open(pidfile)
            pid = int(f.read())
        except ValueError:
            sys.exit('Pidfile %s contains non-numeric value' % pidfile)
        finally:
            if f:
                f.close()

        if pid:
            if pidsignature:
                command = (
                    'ps au -e | grep '
                    + "'"
                    + pidsignature
                    + "'"
                    + ' | grep '
                    + str(pid)
                    + ' | grep -v grep | grep -v '
                    + str(os.getpid())
                )

                processCheck = (
                    subprocess.Popen([command,], shell=True, stdout=subprocess.PIPE)
                    .communicate()[0]
                    .decode("utf-8")
                )

                if not processCheck:
                    print('Removing stale pidfile %s' % pidfile)
                    os.remove(pidfile)

                    pid = None

        if pid:
            try:
                os.kill(pid, 0)
            except OSError as why:
                if why[0] == errno.ESRCH:
                    # The pid doesnt exists.
                    print('Removing stale pidfile %s' % pidfile)
                    os.remove(pidfile)
                else:
                    sys.exit(
                        "Can't check status of PID %s from pidfile %s: %s"
                        % (pid, pidfile, why[1])
                    )
            else:
                sys.exit("Another server is running, PID %s\n" % pid)
    elif pidsignature:
        command = (
            'ps au -e | grep '
            + "'"
            + pidsignature
            + "'"
            + ' | grep -v grep | grep -v '
            + str(os.getpid())
            + " | awk '{print $2}'"
        )

        processCheck = (
            subprocess.Popen([command,], shell=True, stdout=subprocess.PIPE)
            .communicate()[0]
            .decode("utf-8")
        )

        if processCheck:
            pid = int(processCheck.rstrip().splitlines()[0])
            sys.exit("Another server is running, PID %s\n" % pid)


def killPID(pidfile, pidsignature):
    if (not pidfile) and (not pidsignature):
        return

    if pidfile and os.path.exists(pidfile):
        f = None
        pid = None

        try:
            f = open(pidfile)
            pid = int(f.read())
        except ValueError:
            sys.exit('Pidfile %s contains non-numeric value' % pidfile)
        finally:
            if f:
                f.close()

        if pid:
            if not pidsignature:
                os.kill(pid, 9)

            print('Removing stale pidfile %s' % pidfile)
            os.remove(pidfile)

    if pidsignature:
        command = (
            'ps au -e | grep '
            + "'"
            + pidsignature
            + "'"
            + ' | grep -v grep | grep -v '
            + str(os.getpid())
            + " | awk '{print $2}'"
        )
        print(command)

        processCheck = (
            subprocess.Popen([command,], shell=True, stdout=subprocess.PIPE)
            .communicate()[0]
            .decode("utf-8")
        )

        if processCheck:
            pid = int(processCheck.rstrip().splitlines()[0])
            os.kill(pid, 9)


def daemonize(**args):
    pidfile = None
    pidsignature = None
    if 'pidfile' in args:
        pidfile = args['pidfile']
    if 'pidsignature' in args:
        pidsignature = args['pidsignature']
    checkPID(pidfile, pidsignature)
    basic_daemonize()
    writePID(pidfile)

