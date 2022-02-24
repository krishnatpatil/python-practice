"""DetachProcess.py

Daemonization class, subclassed by application bootstrap class

SYNOPSIS
    import sys
    import Utils.DetachProcess as DetachProcess

    class YourApplicationEntryClassHere(DetachProcess.Daemon):
        ...
        def run(self):
            ...

    if __name__ == "__main__":
        daemon = YourApplicationEntryClassHere(yourConstructorArgsHere)
        if len(sys.argv) == 2:
                if 'start' == sys.argv[1]:
                        daemon.start()
                elif 'stop' == sys.argv[1]:
                        daemon.stop()
                elif 'restart' == sys.argv[1]:
                        daemon.restart()
                else:
                        print "Unknown command"
                        sys.exit(2)
                sys.exit(0)
        else:
                print "usage: %s start|stop|restart" % sys.argv[0]
                sys.exit(2)

OVERVIEW

    Pass filepath as 'pidfile' to constructor to manage start/stop/restart
    via process ID stored in pidfile

    Pass process signature string (something that would uniquely
    show up in a ps command) as 'pidsignature' to constructor to
    manage start/stop/restart via process signature

    If both passed, daemon process is managed by process ID in pidfile
    when active process with that ID also matches the signature (reduces
    chance of trying to affect a process ID that belongs to an entirely
    unrelated job)

TBD

FILE FORMAT

COMMENTS

Pulled from the net and tweaked, bare bones from source. Needs better in
code docs and some cleanup.

METHODS

TBD
"""

import sys
import os
import time
import signal
import errno
import atexit
import subprocess

# daemon class pulled from net
class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(
        self,
        pidfile=None,
        pidsignature=None,
        stdin='/dev/null',
        stdout='/dev/null',
        stderr='/dev/null',
    ):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.pidsignature = pidsignature

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        if self.pidfile:
            atexit.register(self.delpid)
            pid = str(os.getpid())
            file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def checkprocessactive(self, pid, command=None):
        if not command:
            command = (
                'ps au -e | grep '
                + str(pid)
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
            return int(processCheck.rstrip().splitlines()[0])
        else:
            message = "No process with specified pid/signature is running. A pidfile may be stale.\n"
            sys.stderr.write(message)

            return None

    def checkpid(self):
        pid = self.getpid()

        # check to see if a process with that ID is actually running
        if pid:
            return self.checkprocessactive(pid)

        return None

    def checksignature(self):
        command = None
        pid = None

        if self.pidfile:
            pid = self.getpid()

            if pid:
                # check to see if a process with that ID and signature is
                # actually running
                command = (
                    'ps au -e | grep '
                    + "'"
                    + self.pidsignature
                    + "'"
                    + ' | grep '
                    + str(pid)
                    + ' | grep -v grep | grep -v '
                    + str(os.getpid())
                    + " | awk '{print $2}'"
                )

                return self.checkprocessactive(pid, command)
        else:
            # check to see if a process with that signature is actually
            # running
            command = (
                'ps au -e | grep '
                + self.pidsignature
                + ' | grep -v grep | grep -v '
                + str(os.getpid())
                + " | awk '{print $2}'"
            )

            return self.checkprocessactive(pid, command)

        return None

    def start(self):
        """
        Start the daemon
        """

        pid = None

        # check for pidfile process matching signature
        if self.pidsignature:
            pid = self.checksignature()
        # else just check for a pidfile to see if the daemon already runs
        elif self.pidfile:
            pid = self.checkpid()

        if pid:
            message = "Process at pid %s already exists. Daemon already running?\n"
            sys.stderr.write(message % pid)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def getpid(self):
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
            return pid
        except IOError:
            return None

    def stop(self):
        """
        Stop the daemon
        """

        if (not self.pidsignature) and (not self.pidfile):
            return

        pid = None

        # Check for pidfile process matching signature
        if self.pidsignature:
            pid = self.checksignature()
        # Else just get the pid from the pidfile
        elif self.pidfile:
            pid = self.checkpid()

        if not pid:
            if self.pidfile:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            return

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if self.pidfile:
                    if os.path.exists(self.pidfile):
                        os.remove(self.pidfile)
            else:
                print(str(err))
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

