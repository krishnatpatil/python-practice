"""
SSHAutomation will create a SSH connection with the target hostname
and execute the given command on the host target.

The module will be used as part of Runbook Action's Run snippets and
the input for the script will be provided by global credential
object - EM7_ACTION_CRED.
"""

import sys
import StringIO
import time
import paramiko


class CustomException(Exception):
    """
    Specific exception class inheriting Exception class
    """

    def __init__(self, message, response=None):
        self.response = response
        super(CustomException, self).__init__(message)


class ConnectionError(CustomException):
    """
    Custom exception class inherting CustomException class
    """

    pass


class SSHAutomation(object):
    """
    Required Parameters:
        cred_host    : Target hostname for creating SSH connection
        cred_user    : User name to authenticate with
        cred_pwd     : User password to authenticate with
        cred_port    : Port number on which SSH connection will be made.
                       Default: 22
        cred_timeout : Connection timeout period. Default: 1000
        cred_type    : Credential can be either password or private key

    Optional Parameters:
        logger       : logger instance

    Usage:
        # The module can be used in scripts as below
        from sample-paramiko.SSHAutomation import SSHAutomation

        commands = ["df -h /var/log"]
        password = '''PASSWORD_OR_PRIVATE_KEY_HERE'''

        params = {
            'cred_host': 'HOSTNAME_HERE',
            'cred_user': 'USERNAME_HERE',
            'cred_pwd': password,
            'cred_port': 22,
            'cred_timeout': 1000
        }

        result = SSHAutomation.executeCommand(commands, **params)

        # This module can also be used in the Runbook actions as below
        import sys

        # Mention the path of the path file deployed in SLD
        sys.path.insert(0,"/opt/lib/remediation/sample-paramiko-0.0.1-py2.7.egg")

        from sample-paramiko.SSHAutomation import SSHAutomation

        COMMANDS = ["df -h /var/log"]

        EM7_RESULT = {"command_list_out": SSHAutomation.executeCommand(COMMANDS,
                                                             **EM7_ACTION_CRED)}

    """

    def __init__(self, logger=None, **kwargs):
        self.cred_host = None  # pylint: disable=invalid-name
        self.cred_user = None  # pylint: disable=invalid-name
        self.cred_pwd = None  # pylint: disable=invalid-name
        self.cred_type = 'password'  # pylint: disable=invalid-name
        self.cred_port = None  # pylint: disable=invalid-name
        self.cred_timeout = None  # pylint: disable=invalid-name
        self.logger = logger
        self.client = None

        self.handleArgs(**kwargs)

    def handleArgs(self, **kwargs):
        """
        Process constructor args into instance attributes. Enforce
        required attributes are set.

        Required Parameters:
            **kwargs: attribute name-value pairs

        Optional Parameters:
            None

        Outputs:
            None

        Sets:
            sets instance attributes by args passed

        Returns:
            None

        Raises:
            AttributeError
        """

        for attribute in (
            loopAttribute
            for loopAttribute in self.__dict__.iterkeys()  # pylint: disable=bad-continuation
            if loopAttribute in kwargs
        ):
            setattr(self, attribute, kwargs[attribute])

        self.cred_port = self.cred_port or 22
        self.cred_timeout = self.cred_timeout or 1000

        if 'ssh_key_data' in kwargs and kwargs['ssh_key_data']:
            self.cred_pwd = kwargs['ssh_key_data']
            self.cred_type = 'sshkey'

        requiredAttributes = [
            'cred_host',
            'cred_user',
            'cred_pwd',
            'cred_port',
            'cred_timeout',
            'cred_type',
        ]
        missingAttributes = [
            attributes
            for attributes in requiredAttributes  # pylint: disable=bad-continuation
            if getattr(self, attributes) is None
        ]  # pylint: disable=bad-continuation

        if missingAttributes:
            errorString = (
                "Required attributes(s) '"
                + ",".join(missingAttributes)
                + "' not supplied!"
            )

            self._logMessage('critical', errorString)

            raise AttributeError(errorString)

    def setupSSHConnection(self):
        """
        Sets up  SSH connection with the target host using either private key if available
        or username and password from the credential object.

        Args:
            None

        Returns:
           client - SSH connect client

        Raises:
            ConnectionError - Custom general SSH connection error
        """

        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()

            try:
                self._connectSSHClient(client)
            # try again without local host keys
            except paramiko.BadHostKeyException:
                self._logMessage(
                    'warning', 'Retrying connection without local host keys.'
                )

                client = paramiko.SSHClient()
                self._connectSSHClient(client)
        except Exception as err:  # pylint: disable=broad-except
            self._logMessage('error', 'SSH Connection Failed !')
            raise ConnectionError(err)
        else:
            self.client = client

    def _connectSSHClient(self, client):
        """
        Connects with the target host using either private key if available
        or username and password.

        Args:
            client - Paramiko SSH client object

        Returns:
            None

        Raises:
            None
        """

        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if self.cred_type == 'sshkey':
            self._logMessage('info', 'Connecting to host using private key.')

            client.connect(
                self.cred_host,
                username=self.cred_user,
                timeout=self.cred_timeout,
                port=self.cred_port,
                pkey=paramiko.RSAKey.from_private_key(StringIO.StringIO(self.cred_pwd)),
            )  # pylint: disable=bad-continuation
        else:
            self._logMessage('info', 'Connecting to host using username and password.')

            client.connect(
                self.cred_host,
                username=self.cred_user,
                password=self.cred_pwd,
                timeout=self.cred_timeout,
                port=self.cred_port,
            )

    def callSSHCommand(self, commands):
        """
        List all the log files in the given path and modification time
        using the command 'df -h /var/log;'

        Args:
            commands - List of commands to be executed on the target host for log cleanup.

        Returns:
            response - List of tuples containing status, stdout, stderr, exception

        Raises:
            None
        """

        response = []

        for command in commands:
            self._logMessage('info', "Executing command: {}".format(command))
            (
                isSuccess,
                stdoutLines,
                stderrLines,
                exceptionList,
            ) = self._executeSSHCommand(command)

            if isSuccess:
                self._logMessage('info', "Command output: \n{}".format(stdoutLines))
            if stderrLines:
                self._logMessage(
                    'error', "Command Error output: \n{}".format(stderrLines)
                )

            cmdString = "Command: {}\n".format(command)

            response.append(
                (isSuccess, cmdString, stdoutLines, stderrLines, exceptionList)
            )
        return response

    def closeConnection(self):
        """
        Close SSH connection client

        Args:
            None

        Returns:
            None

        Raises:
            None
        """

        try:
            if self.client is not None:
                self._logMessage('info', "Closing SSH connection!")
                # Close client connection.
                self.client.close()
        except Exception:  # pylint: disable=broad-except
            self._logMessage('warning', "Failed to close SSH connection!")

    def _executeSSHCommand(self, command):
        """
        Executes the given command on the SSH connection client

        Args:
            command - command to be executed on the target host

        Returns:
            status       - status of the command execution
            stdoutString - std output of the command
            stderrString - std error if the command failed
            stdException - command Exception

        Raises:
            None
        """

        try:
            # Send the command (non-blocking)
            stdin, stdout, stderr = self.client.exec_command(
                command
            )  # pylint: disable=unused-variable

            # Wait for the command to terminate
            while (
                not stdout.channel.exit_status_ready()
                and not stdout.channel.recv_ready()
            ):
                time.sleep(1)

            stdoutLines, stderrLines = stdout.readlines(), stderr.readlines()

            status = True
            if stderrLines:
                status = False
                stderrLines.extend('\n')

            if stdoutLines:
                stdoutLines.extend('\n')

            return status, stdoutLines, stderrLines, []
        except Exception as err:  # pylint: disable=broad-except
            self._logMessage(
                'error', "Command execution Failed with error: {}".format(str(err))
            )
            return False, None, None, [str(err), '\n']

    def _parseResult(self, result, response):
        """
        Parse command results and updates the dictionary

        Args:
            result    - List of tuples containing the result of command execution
            response  - response dictionary will be populated with the response from
                        callSSHCommand method

        Returns:
            None

        Sets:
            Updates the result dictionary with the result from command execution

        Raises:
            None
        """

        if not response:
            response = {'status': 'Success', 'result': []}

        self._logMessage('info', "Commands executed, building response.")
        for (
            cmdSuccess,
            command,
            listLogStdout,
            listLogStderr,
            listLogException,
        ) in result:
            response['result'].append(command)

            if cmdSuccess:
                response['status'] = (
                    'Success' if response['status'] == 'Success' else 'Failure'
                )
                response['result'].extend([str(x) for x in listLogStdout])
            elif listLogStderr:
                response['status'] = 'Failure'
                response['result'].extend([str(x) for x in listLogStderr])
            else:
                response['status'] = 'Failure'
                response['result'].extend([str(x) for x in listLogException])

    def _logMessage(self, level='info', message=''):
        """
        Writes log messages to either logfile or standard output

        Args:
            level    - Log message level
            message  - Log message to be written in logfile or sys.stderr

        Returns:
            None

        Raises:
            None
        """

        self.__class__.logMessage(self.logger, level, message)

    @classmethod
    def logMessage(cls, logger, level='info', message=''):
        """
        Writes log messages to either logfile or standard output

        Args:
            level    - Log message level
            message  - Log message to be written in logfile or sys.stderr

        Returns:
            None

        Raises:
            None
        """

        if logger:
            if level == 'info':
                logger.info(message)
            elif level == 'error':
                logger.error(message)
            elif level == 'critical':
                logger.critical(message)
            elif level == 'warning':
                logger.warning(message)
            else:
                logger.error(message)
        else:
            sys.stderr.write(message + '\n')

    @classmethod
    def executeCommand(cls, commands=None, logger=None, **kwargs):
        """
        Class method to instantiate SSHAutomation and call 'callSSHCommand' method
        which will execute the given command list on the SSH connection client

        Args:
            commands  - list of commands to be executed on the target host
            logger    - Optional parameter - logger instance
            kwargs    - Required Parameters:
                            cred_host    : Target hostname for creating SSH connection
                            cred_user    : User name to authenticate with
                            cred_pwd     : User password to authenticate with
                            cred_port    : Port number on which SSH connection will be made.
                                           Default: 22
                            cred_timeout : Connection timeout period. Default: 1000
                            cred_type    : Credential can be either password or private key

                        Optional Parameters:
                            logger       : logger instance

        Returns:
            response - Dictionary
                    {
                        'status': Boolean,
                        'result': List of command result
                    }

        Raises:
            None
        """

        if commands is None:
            commands = []

        response = {'status': 'Success', 'result': []}

        sshConnection = None
        try:
            sshConnection = cls(logger, **kwargs)
            sshConnection.setupSSHConnection()
            result = sshConnection.callSSHCommand(commands)
            sshConnection._parseResult(result, response)
        except Exception as err:  # pylint: disable=broad-except
            response['status'] = 'Failure'
            response['result'].append(str(err))
        finally:
            level = 'info'
            if response['status'] == 'Failure':
                level = 'error'

            cls.logMessage(logger, level, "{}".format(response))
            if sshConnection:
                sshConnection.closeConnection()

        return response

