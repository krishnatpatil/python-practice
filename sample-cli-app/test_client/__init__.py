"""
This module implements the CLI interface for the Test Client

The CLI options are defined, consumed, and passed to the Client
"""
from __future__ import print_function
from pprint import pprint
import six
import click
from .test_client import TestClient


@click.group()
@click.version_option()
@click.pass_context
@click.option('--url', '-u', envvar='APP_URL', help="APP URL")
@click.option('--namespace', '-n', envvar='APP_NAMESPACE', help="APP Namespace")
@click.option('--account', '-a', help="APP Account")
@click.option('--username', '-U', envvar='APP_USER', help="APP User Name")
@click.option('--api-key', '-A', envvar='APP_API_KEY', help="APP API Key")
@click.option('--configfile', '-c', help="APP configuration file")
@click.option('--logto', '-t', help="Logs location, usually console and/or file")
@click.option('--loglevel', '-l', help="Change logging level printed to STDOUT or file")
@click.option('--logfile', '-f', help="Log file name")
def cli(ctx, **kwargs):
    """\b
    NAME:
      um-APP

    \b
    SYNOPSIS:
      um-APP OPTIONS COMMAND DATA

    \b
    DESCRIPTION:
      The um-APP utility provides command line access to the CyberArk APP
      secrets engine. It provides a user friendly way to get data out of APP.

    \b
      The following options are available:

    \b
      -u, --url
          This is the APP address to use.  By default it points to production
          APP. "APP_URL" environment variable will override the
          default, which will be overriden by a command line option.
      -n, --namespace
          This parameter sets the APP namespace to use. By default the UM
          namespace is used, and will be overridden by the APP_NAMESPACE
          environment variable, which will be overridden by a command line option.
      -a, --account
          This is the internal APP user. We will always use lowercase "app".
      -U  --username
          This parameter is constructed by concatenating the prefix "host/" (with the slash)
          and the full host ID you defined in the policy. "APP_USER" environment variable
          will override the default, which will be overriden by a command line option.
      -A, --api-key
          It is the secure random key. It is used to authenticate APP.
          The environment variable APP_API_KEY will be used if this is not specified.
      -c, --configfile
          The config file path. It will provide a way to map a python script to
          a secret for configuration.
      -t, --logto
          Where to log output to, usually console and/or file.
      -l, --loglevel
          What threshold of log messages to output.
      -f, --logfile
          File to log to.

    \b
      The following commands are available:

    \b
      get               : Retrieve a secret. Need to provide full path from the namespace
      get-credential    : Get the active credential of a credential set
      get-credentials   : Get all credentials of a credential set

    """

    remove_keys = []
    for key, value in six.iteritems(kwargs):
        if value is None:
            remove_keys.append(key)

    for key in remove_keys:
        del kwargs[key]

    ctx.obj = TestClient(**kwargs)


@cli.command()
@click.argument('path')
@click.pass_obj
def get(client, path):
    """
    Get a secret at PATH
    """

    pprint(client.get(path))


@cli.command('get-credential')
@click.argument('credential')
@click.option(
    '--keyed',
    '-k',
    default=False,
    is_flag=True,
    help="Key the credential with the username",
)
@click.option('--env', '-e', default='prod', help="AD Forrest / Environment")
@click.pass_obj
def get_credential(client, credential, keyed, env):
    """
    Get an active credential
    """

    pprint(client.get_credential(credential, keyed, env))


@cli.command('get-credentials')
@click.argument('credential')
@click.option(
    '--keyed',
    '-k',
    default=False,
    is_flag=True,
    help="Key the credential with the username",
)
@click.option('--env', '-e', default='prod', help="AD Forrest / Environment")
@click.pass_obj
def get_credentials(client, credential, keyed, env):
    """
    Get the credential set
    """

    pprint(client.get_credentials(credential, keyed, env))
