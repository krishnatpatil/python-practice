#!/usr/bin/env python

"""argsHandler.py
An utility to handle command line and config arguments.
Standard usage arguments gets created with instance.
All boolean args are set to False by default.
Command Line Arguments takes precedence over any other type of argument.
Configuration Arguments takes precendence over manifested arguments.

Usage:
    from utils.argsHandler import ArgumentHandler

    # create an handler instance
    parser = ArgumentHandler()
    # or to pass the command line args i.e. in test cases
    parser = ArgumentHandler(sys.argv[1:])

    # Manifest arguments
    parser.addArgs(
        argName: {
            type: str Or bool Or int
            default: args default value
            required: boolean
            help: "help string"
        }

    # create args namespace
    args = parser.handleArgs()

Defaults:
    following default arguments get created with class instance and
    their value can be overridden using addArgs method.

    'configfile': defaults to calling script location/name
    'logfile':    defaults to calling script location/name
    'loglevel':   info
    'logto':      file
    'debug':      False

"""

import os
import sys
import argparse
import configparser


def _getCallerPath():
    """Find the stack frame of the real caller (not this module)
    so that we can note the source file path."""

    # hack to set calling script location.
    frame = sys._getframe()
    _srcPath = frame.f_code.co_filename

    depth = 0
    while hasattr(frame, "f_code"):
        depth += 1
        if frame is not None:
            try:
                _srcPath = frame.f_back.f_code.co_filename
            except AttributeError:
                break
        frame = sys._getframe(depth)

    _srcBase, _ = os.path.splitext(_srcPath)

    # normalize the dir path for windows machines
    _srcBase = os.path.normcase(_srcBase)

    return _srcBase


class ArgumentHandler:
    """
    General purpose command line arguments and config arguments handler
    returns a set args objects with result.

    Methods:
        __init__          - standard constructor
        addArgs           - manifest arguments
        _missingArgsAlert - raise error if required args are missing
        handleCommandArgs - command line args handler
        handleArgs        - config args handler

    Args:
        argv              - optional command line arguments

    """

    def __init__(self, argv=None):
        """
        Class constructor.

        Args:
            argv       - command line arguments
        """

        self.argv = argv
        self.script_base = _getCallerPath()
        self.argsManifest = {}

        # add default arguments
        default_args = ['configfile', 'logfile', 'loglevel', 'logto', 'debug']

        for arg in default_args:
            self.argsManifest[arg] = dict(
                type=str, default=None, help='', required=False
            )
            if arg == 'configfile':
                self.argsManifest[arg]['default'] = self.script_base + '.cfg'
                self.argsManifest[arg][
                    'help'
                ] = "filename, config file for runtime service parameters"
            if arg == 'logfile':
                self.argsManifest[arg]['default'] = self.script_base + '.log'
                self.argsManifest[arg]['help'] = "filename, file to log to"

            if arg == 'loglevel':
                self.argsManifest[arg]['default'] = 'info'
                self.argsManifest[arg][
                    'help'
                ] = "string, what threshold of log messages to output"
            if arg == 'logto':
                self.argsManifest[arg]['default'] = 'file'
                self.argsManifest[arg][
                    'help'
                ] = "string,  where to log output to, usually console and/or file"
            if arg == 'debug':
                self.argsManifest[arg]['type'] = bool
                self.argsManifest[arg][
                    'help'
                ] = "boolean, run once as a test and then shut down"

    def addArgs(self, **kwargs):
        """
        Manifest arguments in dictionary.
        """

        for arg, values in kwargs.items():
            if any(param not in values for param in ('type', 'required', 'default')):
                raise RuntimeError(
                    "Please provide argument `type`, `required` and `default` values."
                )
            self.argsManifest[arg] = values

    def _missingArgsAlert(self, nameSpace):
        """
        Enforce the required args

        Agrs:
            nameSpace - arg_parser instance

        Raises:
            AttributeError - if required arguments are missing
        """

        missingArgs = [
            requiredArgs
            for requiredArgs in self.argsManifest
            if getattr(nameSpace, requiredArgs) is None
            and self.argsManifest[requiredArgs]['required']
        ]

        if missingArgs:
            raise AttributeError(
                "Required argument(s) '{}' not provided!\n".format(
                    ",".join(missingArgs)
                )
            )

    def handleCommandArgs(self):
        """
        Command Line argument handler.
`        """

        # handle command line args
        argParser = argparse.ArgumentParser(
            description='{0} script arguments'.format(
                os.path.basename(self.script_base)
            )
        )

        for key, value in self.argsManifest.items():
            argKey = '--' + key

            if value['type'] == bool:
                argParser.add_argument(
                    argKey, dest=key, action='store_true',
                )
            if value['type'] == int or value['type'] == str:
                argParser.add_argument(
                    argKey, dest=key, type=value['type'],
                )

        commandLineArgs = argParser.parse_args(self.argv)

        return commandLineArgs

    def handleArgs(self):
        """
        Config arguments handler.
        Config params takes precedence over manifested args.

        Args:
            argNameSpace - populated argparse instance of
                           arguments

        Returns:
            argNameSpace - populated argparse instance of
                           arguments and config values

        Raises:
            None
        """

        argNameSpace = self.handleCommandArgs()

        # default to a config file in local directory if no other specified
        if getattr(argNameSpace, 'configfile', None) is None:
            setattr(
                argNameSpace, 'configfile', self.argsManifest['configfile']['default']
            )

        # if there is a config file, use it...
        config = configparser.ConfigParser()
        config.optionxform = str

        if os.path.isfile(argNameSpace.configfile):
            config.read(argNameSpace.configfile)

            # take args value from config
            for key in config['DEFAULT_SETTINGS']:
                # ...looking for config entries for them...
                if getattr(argNameSpace, key, None) is None or isinstance(
                    getattr(argNameSpace, key), bool
                ):
                    if self.argsManifest[key]['type'] == bool:
                        if config.get('DEFAULT_SETTINGS', key).lower() == 'true':
                            setattr(argNameSpace, key, True)
                        else:
                            setattr(argNameSpace, key, False)
                    if self.argsManifest[key]['type'] == int:
                        setattr(
                            argNameSpace, key, config.getint('DEFAULT_SETTINGS', key,)
                        )
                    if self.argsManifest[key]['type'] == str:
                        setattr(argNameSpace, key, config.get('DEFAULT_SETTINGS', key,))

        # if there still isn't a value, fall back to the manifested defined default
        for key in self.argsManifest:
            if (getattr(argNameSpace, key, None) is None) and (
                self.argsManifest[key]['default'] is not None
            ):
                setattr(
                    argNameSpace, key, self.argsManifest[key]['default'],
                )

        # now check for missing required values and throw an error if any
        self._missingArgsAlert(argNameSpace)

        return argNameSpace

