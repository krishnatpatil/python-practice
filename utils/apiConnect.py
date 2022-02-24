"""apiConnect.py

APIConnect - API transaction helper class.

SYNOPSIS

    import Utils.APIConnect as APIConnect

    # create the instance, authentication method, credentials
    connectionInstance = APIConnect.APIConnection(
        user = 'usernamehere',
        password = 'passwordthere',
        portal = 'apiservernamehere'
    )

    # assign the REST URL
    connectionInstance.uri = '/api/organization'

    # set connection type
    connectionInstance.requestType = 'GET'

    # make the request
    connectionInstance.httpRequest()

    # do something with the results
    print("JSON %s" % str(connectionInstance.responseJSON))
    print("CODE %d" % connectionInstance.responseCode)
    print("REASON %s" % connectionInstance.responseReason)
    print("CONTENT %s" % connectionInstance.responseContent)
    print("HEADERS %s" % str(connectionInstance.responseHeaders))

    # do the same, except keep looping in batches of 100, skipping
    # the first 200
    connectionInstance.limit = 100
    connectionInstance.offset = 200
    connectionInstance.loop = True

    # make the request
    connectionInstance.httpRequest()

    # do something with the results - note the JSON will be an array of
    # results of batch (limit) size, with array of codes for each batch
    print("JSON %s" % str(connectionInstance.responseJSON))
    print("CODE %d" % str(connectionInstance.responseCode))


    # POST some application monitoring data attributes
    connectionInstance.uri = '/api/device'
    connectionInstance.instance = 101011 # this can just be appended to uri instead
    connectionInstance.requestType = 'POST'
    connectionInstance.requestContent = {"c-app_protocol" : "http-service", "c-app_port" : 80, "c-app_timeout" : 20, "c-app_server" : "dws-rtp-phhedric-l.test.com"}

    # make the request
    connectionInstance.httpRequest()

    # do something with the results
    print("JSON %s" % str(connectionInstance.responseJSON))
    print("CODE %d" % connectionInstance.responseCode)

    # TBD example for DELETE

OVERVIEW

Module designed to handle the usual HTTP(S) transaction work, with some
specific header handling options, for API interactions with Application API.

FILE FORMAT

COMMENTS

Work in progress. Not all code paths may be tested. EM7 mode not verified yet.

METHODS

TBD
"""

import sys
import time
import os.path
import getopt
import json
import requests
import configparser
import re
import base64
import xmltodict
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from hashlib import md5


class APIConnection:
    """
    Required Parameters:
      user: user name to authenticate with
      password: user password to authenticate with
      portal: name of API server to talk to

    Optional Parameters:
      uri: URL of API to call (appended to portal)
      contentType: json (default), text, or xml - method of API communication
      requestType: GET (default), POST, PUT, DELETE, PATCH
      requestContent: if requestType not GET, the payload to send
      retry500: if set, retry 500 family HTTP errors, up to passed integer
          attempts
      offset: for query REST calls, offset to start query from
      limit: for query REST calls, maximum number of items to fetch, required
          if loop is set
      instance: id instance to append to URL, if set
      loop: keep calling REST call, incrementing internal offset until all
          values are fetched, store results in object attributes as arrays
          of references instead of just references
      retryExceptions: if set, retry any request exception, up to passed
          integer attempts, multiplicative with retry500
      useSessions - boolean to use sessions on API calls
      noUserAgent - boolean to not include auto generated User-Agent header
      logger - logger instance
    """

    # default constructor, turn named parameters into attributes
    def __init__(self, **args):
        # initialization related attributes
        self.portal = None
        self.retry500 = 0
        self.retryExceptions = 0
        self.offset = None
        self.limit = None
        self.instance = None
        self.loop = False
        self.logger = None
        self.configFile = None

        # request related attributes
        self.uri = None
        self.contentType = 'JSON'
        self.requestType = 'GET'
        self.requestContent = ''
        self.requestError = None
        self.noUserAgent = False

        # authentication related attributes
        self.user = None
        self.password = None

        # response related attributes
        self.responseContent = None
        self.responseXML = None
        self.responseJSON = None
        self.responseCode = None
        self.responseReason = None
        self.responseHeaders = None
        self.responseError = None

        # session related attributes
        self.useSessions = False
        self.sessions = {}

        self.handleArgsAndConfigs(**args)

    # general template for accessor/mutator, still TBD to us
    def placeholderAccessor(self, *attribute):
        if attribute:
            self.attribute = attribute[0]
        return self.attribute

    def handleArgsAndConfigs(self, **args):
        if ('configFile' in args) and (args['configFile']):
            setattr(self, 'configFile', args['configFile'])

        if not self.configFile:
            try:
                modulePath = __file__
                if modulePath.find('/') < 0:
                    modulePath = (
                        os.path.dirname(os.path.abspath(__file__)) + '/' + __file__
                    )
                modulePath = re.sub(r'\.py[c]?', '.cfg', modulePath)
                setattr(self, 'configFile', modulePath)
            except:
                pass

        # if there is a config file, use it, but passed args take precedence
        if os.path.isfile(self.configFile):
            config = configparser.ConfigParser()
            config.read(self.configFile)

            # get default settings
            if config.has_option('DEFAULT_SETTINGS', 'portal'):
                setattr(self, 'portal', config.get('DEFAULT_SETTINGS', 'portal'))
            if config.has_option('DEFAULT_SETTINGS', 'uri'):
                setattr(self, 'uri', config.get('DEFAULT_SETTINGS', 'uri'))
            if config.has_option('DEFAULT_SETTINGS', 'contentType'):
                setattr(
                    self, 'contentType', config.get('DEFAULT_SETTINGS', 'contentType')
                )
            if config.has_option('DEFAULT_SETTINGS', 'requestType'):
                setattr(
                    self, 'requestType', config.get('DEFAULT_SETTINGS', 'requestType')
                )
            if config.has_option('DEFAULT_SETTINGS', 'requestContent'):
                setattr(
                    self,
                    'requestContent',
                    config.get('DEFAULT_SETTINGS', 'requestContent'),
                )
            if config.has_option('DEFAULT_SETTINGS', 'retry500'):
                setattr(self, 'retry500', config.getint('DEFAULT_SETTINGS', 'retry500'))
            if config.has_option('DEFAULT_SETTINGS', 'retryExceptions'):
                setattr(
                    self,
                    'retryExceptions',
                    config.getint('DEFAULT_SETTINGS', 'retryExceptions'),
                )
            if config.has_option('DEFAULT_SETTINGS', 'user'):
                setattr(self, 'user', config.get('DEFAULT_SETTINGS', 'user'))
            if config.has_option('DEFAULT_SETTINGS', 'password'):
                setattr(self, 'password', config.get('DEFAULT_SETTINGS', 'password'))
            if config.has_option('DEFAULT_SETTINGS', 'noUserAgent'):
                setattr(
                    self,
                    'noUserAgent',
                    config.getboolean('DEFAULT_SETTINGS', 'noUserAgent'),
                )
            if config.has_option('DEFAULT_SETTINGS', 'useSessions'):
                setattr(
                    self,
                    'useSessions',
                    config.getboolean('DEFAULT_SETTINGS', 'useSessions'),
                )

        for attribute in (
            loopAttribute
            for loopAttribute in self.__dict__.keys()
            if loopAttribute in args
        ):
            setattr(self, attribute, args[attribute])

        missingAttributes = [
            requiredAttributes
            for requiredAttributes in ['portal', 'user', 'password']
            if getattr(self, requiredAttributes) is None
        ]

        if missingAttributes:
            raise AttributeError(
                "Required attributes(s) '"
                + ",".join(missingAttributes)
                + "' not supplied!\n"
            )

    def httpRequest(self):
        """
        Description:
          Helper method to handle basic HTTP transactions for the REST call,
          and whatever request/response content handling for the various
          transaction payload types.

        Required Parameters:
          From object instance, nearly every attribute.

        Optional Parameters:
          None

        Outputs:
          Sets object instance response payload attributes
        """

        requestHeaders = {}
        requestArgs = {}
        agentArgs = {}

        if self.user and self.password:
            agentArgs['user'] = self.user
            agentArgs['password'] = self.password

        if self.contentType.lower() == 'json':
            requestHeaders['Content-Type'] = 'application/json'
            requestHeaders['Accept'] = 'application/json'

            if self.requestContent and self.requestType in [
                'PUT',
                'POST',
                'PATCH',
                'DELETE',
            ]:
                requestArgs['jsonPayload'] = self.requestContent
        elif self.contentType.lower() == 'text':
            requestHeaders['Content-Type'] = 'text/plain'
            requestHeaders['Accept'] = 'text/plain'

            if self.requestContent and self.requestType in [
                'PUT',
                'POST',
                'PATCH',
                'DELETE',
            ]:
                requestArgs['dataPayload'] = self.requestContent
        elif self.contentType.lower() == 'xml':
            requestHeaders['Content-Type'] = 'application/xml'
            requestHeaders['Accept'] = 'application/xml'

            if self.requestContent and self.requestType.lower() in [
                'put',
                'post',
                'patch',
                'delete',
            ]:
                requestArgs['dataPayload'] = self.requestContent
        elif self.contentType.lower() == 'em7':
            requestHeaders['Content-Type'] = 'application/em7-resource-uri'
            requestHeaders['X-em7-beautify-response'] = '1'

            if self.requestContent and self.requestType.lower() in [
                'put',
                'post',
                'patch',
                'delete',
            ]:
                requestArgs['dataPayload'] = self.requestContent
        else:
            raise ValueError("Unsupported content type '" + self.contentType + "'!\n")

        if not self.noUserAgent:
            requestHeaders['User-Agent'] = (
                os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[1]
                + ':'
                + os.path.split(os.path.abspath(__file__))[1]
            )

        agentArgs['headers'] = requestHeaders
        agentArgs['timeout'] = 300
        agentArgs['useSessions'] = self.useSessions
        agentArgs['sessions'] = self.sessions

        offset = 0
        endLoop = False

        if self.loop:
            self.responseContent = []
            self.responseCode = []
            self.responseReason = []
            self.responseHeaders = []

            self.responseError = []
            self.requestError = []
            self.responseJSON = []
            self.responseXML = []
        else:
            self.responseContent = None
            self.responseCode = None
            self.responseReason = None
            self.responseHeaders = None

            self.responseError = None
            self.requestError = None
            self.responseJSON = None
            self.responseXML = None

        while not endLoop:
            totalReturned = 0

            attemptLimit = 1
            if self.retry500:
                attemptLimit = self.retry500

            url = 'https://' + self.portal

            logUrl = url

            if not re.search(r'^\/', self.uri):
                url += '/'
                logUrl += '/'
            url += self.uri
            logUrl += self.uri

            if self.instance is not None:
                url += '/' + str(self.instance)
                logUrl += '/' + str(self.instance)

            if (self.offset is not None) or (offset != 0):
                tempOffset = 0
                if self.offset is not None:
                    tempOffset = self.offset

                if (tempOffset != 0) or (offset != 0):
                    if re.search(r'\?', url):
                        url += '&'
                        logUrl += '&'
                    else:
                        url += '?'
                        logUrl += '?'

                    url += 'offset='
                    url += str(tempOffset + offset)
                    logUrl += 'offset='
                    logUrl += str(tempOffset + offset)

            if self.limit is not None:
                if re.search(r'\?', url):
                    url += '&'
                    logUrl += '&'
                else:
                    url += '?'
                    logUrl += '?'

                url += 'limit='
                url += str(self.limit)
                logUrl += 'limit='
                logUrl += str(self.limit)

            userAgent = basicRESTAPI(**agentArgs)

            if self.logger:
                self.logger.debug(
                    'Making HTTP request ' + logUrl + '(' + self.requestType + ')'
                )
                if self.requestContent:
                    self.logger.debug(
                        'Request data payload ' + str(self.requestContent)
                    )

            while attemptLimit:
                response = None

                if self.requestType.lower() == 'put':
                    response = userAgent.put(url, **requestArgs)
                elif self.requestType.lower() == 'post':
                    response = userAgent.post(url, **requestArgs)
                elif self.requestType.lower() == 'patch':
                    response = userAgent.patch(url, **requestArgs)
                elif self.requestType.lower() == 'delete':
                    response = userAgent.delete(url, **requestArgs)
                elif self.requestType.lower() == 'get':
                    response = userAgent.get(url, **requestArgs)
                else:
                    requestError = (
                        "Unsupported HTTP request type '" + self.requestType + "'!"
                    )
                    self.requestError = requestError

                    if self.logger:
                        self.logger.error(requestError)
                    else:
                        sys.stderr.write(requestError + "\n")

                    return

                if self.retry500 and (
                    (response.status_code > 499) and (response.status_code < 600)
                ):
                    attemptLimit -= 1

                    nextStep = 'aborting'
                    if attemptLimit:
                        nextStep = 'retrying'

                    if self.logger:
                        self.logger.error(
                            'HTTP request '
                            + logUrl
                            + '('
                            + self.requestType
                            + ') attempt '
                            + str(self.retry500 - attemptLimit)
                            + ' failed - return code '
                            + str(response.status_code)
                            + ', '
                            + nextStep
                        )
                    else:
                        sys.stderr.write(
                            'HTTP request '
                            + logUrl
                            + '('
                            + self.requestType
                            + ') attempt '
                            + str(self.retry500 - attemptLimit)
                            + ' failed - return code '
                            + str(response.status_code)
                            + ', '
                            + nextStep
                            + "\n"
                        )

                    if attemptLimit:
                        time.sleep(5)
                else:
                    attemptLimit = 0

                if attemptLimit == 0:
                    if self.loop:
                        self.responseContent.append(response.text)
                        self.responseCode.append(response.status_code)
                        self.responseReason.append(response.reason)
                        self.responseHeaders.append(response.headers)
                    else:
                        self.responseContent = response.text
                        self.responseCode = response.status_code
                        self.responseReason = response.reason
                        self.responseHeaders = response.headers

                    if response:
                        if self.contentType.lower() == 'json':
                            tempJSON = None
                            try:
                                tempJSON = response.json()
                            except Exception as error:
                                # can ignore no JSON for delete
                                if self.requestType.lower() != 'delete':
                                    raise error

                            if self.loop:
                                self.responseJSON.append(tempJSON)
                            else:
                                self.responseJSON = tempJSON

                            if isinstance(tempJSON, dict):
                                if 'total_returned' in tempJSON:
                                    totalReturned = int(tempJSON['total_returned'])
                                else:
                                    totalReturned = 1
                            elif isinstance(tempJSON, list):
                                totalReturned = len(tempJSON)

                        elif self.contentType.lower() == 'xml':
                            if self.loop:
                                self.responseXML.append(xmltodict.parse(response.text))
                            else:
                                self.responseXML = xmltodict.parse(response.text)
                    else:
                        requestError = (
                            'HTTP request '
                            + logUrl
                            + ' ('
                            + self.requestType
                            + ') failed - return code '
                            + str(response.status_code)
                        )
                        self.requestError = requestError
                        if self.logger:
                            self.logger.error(requestError)
                        else:
                            sys.stderr.write(requestError + "\n")
                        return

            if (
                (self.loop is not None)
                and (self.limit is not None)
                and (self.limit > 0)
            ):
                if totalReturned < self.limit:
                    endLoop = True
                offset += self.limit
            else:
                endLoop = True

    def tryAPIRequest(self):
        """
        Description:
          Exception retry wrapper, as they seem to be fairly common with
          Application API calls

        Required Parameters:
          From object instance

        Optional Parameters:
          None

        Outputs:
          None

        Raises:
          passes along httpRequest exceptions
        """

        retryLimit = 1
        if self.retryExceptions and isinstance(self.retryExceptions, int):
            retryLimit = self.retryExceptions

        while retryLimit:
            try:
                self.httpRequest()
                return
            except Exception as error:
                retryLimit -= 1

                retryError = 'HTTP request raised exception - %s' % (str(error))
                if self.logger:
                    self.logger.error(retryError)
                else:
                    sys.stderr.write(retryError + "\n")

                if not retryLimit:
                    raise error


class basicRESTAPI:
    def __init__(self, **args):
        self.headers = None
        self.httpauth = None
        self.user = None
        self.password = None
        self.timeout = None
        self.useSessions = False
        self.sessions = {}

        requests.packages.urllib3.disable_warnings()

        for attribute in (
            loopAttribute
            for loopAttribute in self.__dict__.keys()
            if loopAttribute in args
        ):
            setattr(self, attribute, args[attribute])

        if self.user and self.password:
            self.httpauth = HTTPBasicAuth(self.user, self.password)

    def getSession(self, uri):
        sessionInstance = None

        if self.useSessions:
            parsedUri = urlparse.urlparse(uri)
            protocol = parsedUri.scheme
            host = parsedUri.netloc

            port = None

            authIndex = host.find('@')
            if authIndex >= 0:
                host = host[authIndex + 1 :]

            portIndex = host.find(':')
            if portIndex >= 0:
                port = host[portIndex + 1 :]
                host = host[:portIndex]

            if not port:
                if protocol and protocol == 'https':
                    port = str(443)
                else:
                    port = str(80)

            sessionKey = host + ':' + port

            if sessionKey in self.sessions:
                sessionInstance = self.sessions[sessionKey]
            else:
                sessionInstance = self.sessions[sessionKey] = requests.Session()

        return sessionInstance

    def get(self, uri, jsonPayload=None, dataPayload=None):
        sessionInstance = self.getSession(uri)

        if sessionInstance:
            return sessionInstance.get(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )
        else:
            return requests.get(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )

    def put(self, uri, jsonPayload=None, dataPayload=None):
        sessionInstance = self.getSession(uri)

        if sessionInstance:
            return sessionInstance.put(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )
        else:
            return requests.put(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )

    def post(self, uri, jsonPayload=None, dataPayload=None):
        sessionInstance = self.getSession(uri)

        if sessionInstance:
            return sessionInstance.post(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )
        else:
            return requests.post(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )

    def delete(self, uri, jsonPayload=None, dataPayload=None):
        sessionInstance = self.getSession(uri)

        if sessionInstance:
            return sessionInstance.delete(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )
        else:
            return requests.delete(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )

    def head(self, uri, jsonPayload=None, dataPayload=None):
        sessionInstance = self.getSession(uri)

        if sessionInstance:
            return sessionInstance.head(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )
        else:
            return requests.head(
                uri,
                headers=self.headers,
                auth=self.httpauth,
                json=jsonPayload,
                data=dataPayload,
                verify=False,
                timeout=self.timeout,
            )

