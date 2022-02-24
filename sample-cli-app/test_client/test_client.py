#!/usr/bin/env python

from __future__ import print_function
import sys
import configparser
import logging
import logging.handlers
import requests
import six
from pathlib import Path

if sys.version_info.major == 2:
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus


class TestClient:
    """
    CyberArk Conjur Client
    """

    def __init__(self, **args):
        """
        Initialize the parameters
        """

        self.url = "http://test.example.com"
        self.namespace = "it/app"
        self.account = "test"
        self.username = "host/it/app/apikey"
        self.api_key = None
        self.path = None
        self.configfile = None
        self.logto = "console"
        self.loglevel = "info"
        self.logfile = None

        self.logger = None
        self.token = None
        self.secrets = dict()

        self.script_path = Path(__file__).resolve()

        self._handle_args(**args)
        self._set_logger()
        self._get_token()
        self._list_credentials()

    def _handle_args(self, **args):
        """
        Ingest arguments and set internal state
        """

        if 'configfile' in args and args['configfile']:
            setattr(self, 'configfile', args['configfile'])

        if not self.configfile:
            self.configfile = (
                str(self.script_path.parent.joinpath(self.script_path.stem)) + '.cfg'
            )

        # if there is a config file, use it, but passed args take precedence
        config = configparser.ConfigParser()
        if Path(self.configfile).is_file():
            config.read(self.configfile)

            # get default settings
            if config.has_option('DEFAULT_SETTINGS', 'url'):
                setattr(self, 'url', config.get('DEFAULT_SETTINGS', 'url'))
            if config.has_option('DEFAULT_SETTINGS', 'namespace'):
                setattr(self, 'namespace', config.get('DEFAULT_SETTINGS', 'namespace'))
            if config.has_option('DEFAULT_SETTINGS', 'api_key'):
                setattr(self, 'api_key', config.get('DEFAULT_SETTINGS', 'api_key'))
            if config.has_option('DEFAULT_SETTINGS', 'account'):
                setattr(self, 'account', config.get('DEFAULT_SETTINGS', 'account'))
            if config.has_option('DEFAULT_SETTINGS', 'username'):
                setattr(self, 'username', config.get('DEFAULT_SETTINGS', 'username'))
            if config.has_option('DEFAULT_SETTINGS', 'path'):
                setattr(self, 'path', config.get('DEFAULT_SETTINGS', 'path'))
            if config.has_option('DEFAULT_SETTINGS', 'logto'):
                setattr(self, 'logto', config.get('DEFAULT_SETTINGS', 'logto'))
            if config.has_option('DEFAULT_SETTINGS', 'loglevel'):
                setattr(self, 'loglevel', config.get('DEFAULT_SETTINGS', 'loglevel'))
            if config.has_option('DEFAULT_SETTINGS', 'logfile'):
                setattr(self, 'logfile', config.get('DEFAULT_SETTINGS', 'logfile'))

        for attribute in (
            loopAttribute for loopAttribute in self.__dict__ if loopAttribute in args
        ):
            setattr(self, attribute, args[attribute])

        missingAttributes = [
            requiredAttributes
            for requiredAttributes in ['api_key']
            if getattr(self, requiredAttributes) is None
        ]

        if missingAttributes:
            raise AttributeError(
                "Required attributes(s) '"
                + ",".join(missingAttributes)
                + "' not supplied!\n"
            )

    def _set_logger(self):
        """
        Create logger object. Currently shunts to file and/or console.
        """

        message_level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL,
        }

        log_format = '%(levelname)s [%(asctime)s %(module)s:%(funcName)s (line %(lineno)d)] - %(message)s'

        self.logger = logging.getLogger(__file__)

        self.logger.setLevel(message_level_map[self.loglevel.lower()])

        # create formatter
        formatter = logging.Formatter(log_format)

        if self.logto.lower() == 'console':
            # create console handler and set level to debug
            console_handler = logging.StreamHandler()
            console_handler.setLevel(message_level_map[self.loglevel.lower()])

            # add formatter to console handler
            console_handler.setFormatter(formatter)

            # then add it to the logger
            self.logger.addHandler(console_handler)

        if self.logto.lower() == 'file':
            if not self.logfile or self.logfile.lower() == 'none' or self.logfile == '':
                self.logfile = (
                    str(self.script_path.parent.joinpath(self.script_path.stem))
                    + '.log'
                )

            # create file handler and set level to debug
            file_handler = logging.handlers.TimedRotatingFileHandler(
                self.logfile, when='W6'
            )
            file_handler.setLevel(message_level_map[self.loglevel.lower()])

            # add formatter to file handler
            file_handler.setFormatter(formatter)

            # add file handler to logger
            self.logger.addHandler(file_handler)

    def _get_token(self):
        """
        Further documentation: https://docs.conjur.org/Latest/en/Content/Developer/Conjur_API_Authenticate.htm
        """

        self.logger.debug("Initiating Conjur Authentication to get the Token")

        account = quote_plus(self.account)
        username = quote_plus(self.username)
        url = "{url}/authn/{account}/{username}/authenticate".format(
            url=self.url, account=account, username=username
        )
        headers = {
            'Accept-Encoding': 'base64',
        }

        r = requests.post(url=url, data=self.api_key, headers=headers)

        if r.status_code == 200:
            self.logger.debug(
                "Conjur Authentication Successful - {}".format(r.status_code)
            )
            self.token = r.text
        else:
            error_string = "Conjur Authentication error - {}".format(r.status_code)
            self.logger.critical(error_string)
            raise RuntimeError(error_string)

    def _list_credentials(self):
        """
        List all available secret ids from the namespace
        """

        account = quote_plus(self.account)
        url = "{url}/resources/{account}?kind=variable".format(
            url=self.url, account=account
        )
        headers = {
            'Authorization': 'Token token=\"{token}\"'.format(token=self.token),
        }

        r = requests.get(url=url, headers=headers)

        if r.status_code == 200:
            for var in r.json():
                owner = var['owner'].split(':')[-1]
                var_id = var['id'].split(':')[-1]
                if owner not in self.secrets:
                    self.secrets[owner] = []
                self.secrets[owner].append(var_id)
        else:
            error_string = "Failed to extract secret id's from the namespace - {}. Please try again".format(
                r.status_code
            )
            self.logger.critical(error_string)
            raise RuntimeError(error_string)

    def get(self, path=None):
        """
        Get a secret from Conjur
        """

        secret = {}

        if not path:
            if not self.path:
                self.logger.error("Unable to get secret without a valid path")
                return secret
            path = self.path

        self.logger.debug("Getting secret at {}".format(path))

        username = Path(path).name
        account = quote_plus(self.account)
        variable = quote_plus(path)

        url = "{url}/secrets/{account}/variable/{variable}".format(
            url=self.url, account=account, variable=variable
        )
        headers = {
            'Authorization': 'Token token=\"{token}\"'.format(token=self.token),
        }

        r = requests.get(url=url, headers=headers)

        if r.status_code == 200:
            secret[username] = r.text
        else:
            self.logger.error("Secret retrieval error - {}".format(r.status_code))

        return secret

    def post(self, path=None, value=None):
        """
        Sets a secret value for the specified Variable.
        """

        if not path and value:
            self.logger.error("Unable to set a secret without a valid path and value")
            return

        self.logger.debug("Updating secret at {}".format(path))

        account = quote_plus(self.account)
        variable = quote_plus(path)

        url = "{url}/secrets/{account}/variable/{variable}".format(
            url=self.url, account=account, variable=variable
        )
        headers = {
            'Authorization': 'Token token=\"{token}\"'.format(token=self.token),
        }

        r = requests.post(url=url, data=value, headers=headers)

        if r.status_code == 201:
            self.logger.info("The secret value was set successfully")
        else:
            self.logger.error(
                "Failed to set the secret value - {}".format(r.status_code)
            )

    def get_credential(self, cred_name, keyed=False, environment='prod'):
        """
        Get the active credential of a credential set
        """

        secret = {}

        self.logger.debug('Getting credential "{}"'.format(cred_name))

        # This special secret holds the configuration of which credential is active as:
        # {secret_doc: active_user_key}
        # {generic-api.gen: generic-api2.gen} OR {generic-api.gen: generic-api.gen}
        base_url = 'it/app/credentials/'
        cred_path = base_url + '{}/{}'.format(environment, cred_name)
        active_cred_path = base_url + '{}/active_credentials/{}'.format(
            environment, cred_name
        )

        active_cred = None
        if (
            active_cred_path
            in self.secrets['it/app/credentials/prod/active_credentials']
        ):
            active_cred = self.get(active_cred_path)[cred_name]

        if cred_path in self.secrets:
            for cred in self.secrets[cred_path]:
                secret.update(self.get(cred))
        else:
            self.logger.error(
                'Credential Lookup Failure. Unable to find credential "{}" at {}{}'.format(
                    cred_name, base_url, environment
                )
            )
            return

        if active_cred and active_cred in secret:
            if keyed:
                return {active_cred: secret[active_cred]}
            return {'username': active_cred, 'password': secret[active_cred]}

        if (
            secret
            and active_cred_path
            not in self.secrets['it/app/credentials/prod/active_credentials']
        ):
            self.logger.warning(
                "Credential at {} has no active key specified".format(cred_path)
            )
            secret = next(six.iteritems(secret))
            if keyed:
                return {secret[0]: secret[1]}
            return {'username': secret[0], 'password': secret[1]}

    def get_credentials(self, cred_name, keyed=False, environment='prod'):
        """
        Get all credentials of a credential set
        """

        secrets = {}

        self.logger.debug('Getting credential "{}"'.format(cred_name))

        base_url = 'it/app/credentials/'
        cred_path = base_url + '{}/{}'.format(environment, cred_name)

        if cred_path in self.secrets:
            for cred in self.secrets[cred_path]:
                secrets.update(self.get(cred))
        else:
            self.logger.error(
                'Credential Lookup Failure. Unable to find credential "{}" at {}{}'.format(
                    cred_name, base_url, environment
                )
            )

        if secrets:
            if keyed:
                return [secrets]
            return [
                {'username': username, 'password': password}
                for username, password in six.iteritems(secrets)
            ]

