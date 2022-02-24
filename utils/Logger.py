"""Logger.py

General purpose logger that handles creating logs with default information.

"""
import logging
import logging.handlers
import sys
import os
import re

# hacks to set stack frame info, so the right (calling) stack is reported
# as the origin for logging, rather than this log module
if hasattr(sys, '_getframe'):
    currentframe = lambda: sys._getframe(3)
_srcfile = os.path.normcase(currentframe.__code__.co_filename)


class Logger:
    """
    General purpose logger that handles creating logs with default information.

    Methods:
        __init__ - standard constructor
        createLogger - create logger object
        debug - convenience wrapper
        info - convenience wrapper
        logprint - convenience wrapper, maps to info,
            conditionally uses standard print if called
            in list context or no valid logger object
        warning - convenience wrapper
        error - convenience wrapper
        critical - convenience wrapper
        shutdown - convenience wrapper

    """

    def __init__(self, logfileName=None, logLevel=None, logTo=None, logName=None):
        self.logfileName = logfileName
        self.logLevel = logLevel
        self.logTo = logTo
        self.logName = logName

        self.logger = None

        # logLevel and logTo are required, logFileName may be optional,
        # logName always optional
        if logLevel and logTo:
            self.logger = self.createLogger(logfileName, logLevel, logTo, logName)

    @classmethod
    def shutdown(cls):
        logging.shutdown()

    def debug(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.debug(msg, *args, **kwargs)
        else:
            if not msg.find('\n') == len(msg) - 1:
                msg += '\n'
            sys.stdout.write(msg)

    def info(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.info(msg, *args, **kwargs)
        else:
            if not msg.find('\n') == len(msg) - 1:
                msg += '\n'
            sys.stdout.write(msg)

    def warning(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.warning(msg, *args, **kwargs)
        else:
            if not msg.find('\n') == len(msg) - 1:
                msg += '\n'
            sys.stderr.write(msg)

    def error(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.error(msg, *args, **kwargs)
        else:
            if not msg.find('\n') == len(msg) - 1:
                msg += '\n'
            sys.stderr.write(msg)

    def critical(self, msg, *args, **kwargs):
        if self.logger:
            self.logger.critical(msg, *args, **kwargs)
        else:
            if not msg.find('\n') == len(msg) - 1:
                msg += '\n'
            sys.stderr.write(msg)

    def createLogger(self, logfileName, logLevel, logTo, logName):
        """
        Create logger object. Currently shunts to file and/or console.

        Args:
            logfileName - name of file to log to, if None log to console only
                if indicated
            logLevel - threshold of log messages to output
            logTo - string indicating where (console and/or file) to output to
            logName - string indicating internal log name (defaults to calling module name)

        Returns:
            logger - logger object

        Raises:
            None
        """

        messageLevelMap = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL,
        }

        logFormat = '%(levelname)s [%(asctime)s %(module)s:%(funcName)s (line %(lineno)d, thread %(threadName)s)] - %(message)s'

        if not logName:
            logName = findCallerPatch()[0]
            logName = re.sub(r'\..+', '', logName)

        logger = logging.getLogger(logName)

        if logLevel and isinstance(logLevel, str):
            if logLevel.lower() in messageLevelMap:
                logger.setLevel(messageLevelMap[logLevel.lower()])

        # create formatter
        formatter = logging.Formatter(logFormat)

        if isinstance(logTo, str) and (logTo.find('console') >= 0):
            # create console handler and set level to debug
            consoleHandler = logging.StreamHandler()
            consoleHandler.setLevel(logging.DEBUG)
            if logLevel and isinstance(logLevel, str):
                if logLevel.lower() in messageLevelMap:
                    consoleHandler.setLevel(messageLevelMap[str(logLevel.lower())])

            # add formatter to console handler
            consoleHandler.setFormatter(formatter)

            # then add it to the logger
            logger.addHandler(consoleHandler)

        if isinstance(logTo, str) and (logTo.find('file') >= 0):
            # create console handler and set level to debug
            if logfileName:
                fileHandler = logging.handlers.TimedRotatingFileHandler(
                    logfileName, when='W6'
                )
                if logLevel and isinstance(logLevel, str):
                    if logLevel.lower() in messageLevelMap:
                        fileHandler.setLevel(messageLevelMap[str(logLevel.lower())])

                # add formatter to file handler
                fileHandler.setFormatter(formatter)

                # add file handler to logger
                logger.addHandler(fileHandler)

        # hack so log write wrappers report right code context
        logger.findCaller = findCallerPatch

        return logger


def findCallerPatch():
    """
    Find the stack frame of the real caller (not this module) so that we can
    note the source file name, line number and function name.
    """

    frame = currentframe()
    if frame is not None:
        frame = frame.f_back

    backFrameInfo = "(unknown file)", 0, "(unknown function)"
    while hasattr(frame, "f_code"):
        frameCode = frame.f_code

        filename = os.path.normcase(frameCode.co_filename)
        if filename == _srcfile:
            frame = frame.f_back
            continue

        backFrameInfo = (frameCode.co_filename, frame.f_lineno, frameCode.co_name)
        break

    return backFrameInfo

