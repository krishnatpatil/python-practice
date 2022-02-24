"""dbConnect.py

dbConnect - Wrapper for MySQL DBI

SYNOPSIS

    import Utils.dbConnect as dbConnect

    sql = '''
        SELECT id, name
        FROM master.customer
        ORDER BY name
    '''

    # can be defined to expect DB fields as dict or args (unpacked list),
    # extra callbackParams as dict or args (unpacked list)
    def callback (id, hostname, ip, extraArg):
        print("Host: %s" % hostname)
        print("ID: %d" % id)
        print("IP Address: %s" % ip)

        # callbackParams are dumped as args or keyword
        # args depending on whether defined as list or dict,
        # in this case list of single element
        print(extraArg)

        # stop when hostname starts with 'b'
        if (re.search(r'^b', hostname)):
            return False
        else:
            return True

    dbInstance = dbConnect.DBConnection(
        database = 'master',
        port = 3306,
        server = 'nprd1.test.com',
        user = 'youshouldknowthis',
        password = 'youshouldknowthis',
        callback = callback,
        callbackParams = [extraArg], # can be a list or dictionary
        sql = sql,
    )

    # sample use of fetchrows with callback
    dbInstance.fetchrows()

    sql2 = '''
        SELECT id, device, ip
        FROM master.device
        WHERE id = %s
        ORDER BY device
    '''

    dbInstance = dbConnect.DBConnection(
        database = 'master',
        port = 3306,
        server = 'nprd1.test.com',
        user = 'youshouldknowthis',
        password = 'youshouldknowthis',
        bindParams = [ 1234 ],
        sql = sql2,
    )

    # sample use of fetchrows with bind param and without callback
    dbInstance.fetchrows()
    print(dbInstance.fetchResults)

    dbInstance.callback = None
    dbInstance.sql(
        '''
        UPDATE master.device
        SET avail_proto = 2, avail_port = 0
        WHERE device = %s
        '''
    )

    dbInstance.bindParams = host;

    # sample use of execute for insert, update, delete use cases
    # with bind param and without callback
    try:
        dbInstance.execute()
        dbInstance.connection.commit()
    except:
        dbInstance.connection.rollback()

OVERVIEW

Module for handling MySQL DB interactions, abstracting some of the
technical details.

COMMENTS

Still a work in progress. 

METHODS

TBD
"""

import time
import socket
import threading
import re
import MySQLdb
import os.path
import configparser
import sys
import pprint
import json
import signal
import os
import atexit
import select
import fcntl


class DBConnection:
    """
    Required Parameters:
      database: database name
      server: database server
      user: database account user name
      password: database account user password
      port: database connection port

    Optional Parameters:
      configFile: config file pre-defining any of the required or optional
        parameters, explicitly passed parameters take precedence
      sql: SQL statement for fetchrows() or execute() method calls
      bindParams: bind params for fetchrows() or execute() method calls
      callback - function to call for each row fetched by fetchrows(),
        is passed each field returned by the query (as separate args if
        dictcursor not set, as a single dictionary if dictcursor set). 

        If not passed with fetchrows(), the fetch results from the cursor 
        are stored in the fetchResults attribute. 

        If used with execute(), is called once after execute but before 
        cursor close and is passed the cursor as the first parameter. 
      callbackParams - additional parameters to pass to the callback after
        the row values or cursor, used to provide external hooks the callback 
        might need like object instances, data handles, settings variables
      dictcursor - boolean, if true fetch results in fetchrows() as a 
          dictionary and pass results to callback or fetchResults
          attribute as a dictionary
      logger - logger instance
    """

    # default constructor, turn named parameters into attributes
    def __init__(self, **args):
        # initialization and runtime operations related attributes
        self.logger = None
        self.configFile = None
        self.connectionLock = threading.Lock()
        self.connection = None
        self.stalerollback = False
        self.dictcursor = False

        # connection related attributes
        self.database = None
        self.server = None
        self.port = 0

        # authentication related attributes
        self.user = None
        self.password = None

        # query/execute related attributes
        self.sql = None
        self.bindParams = None
        self.callback = None
        self.callbackParams = None
        self.fetchResults = None

        self.handleArgsAndConfigs(**args)
        self.mysqlConnect()

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
            if config.has_option('DEFAULT_SETTINGS', 'database'):
                setattr(self, 'database', config.get('DEFAULT_SETTINGS', 'database'))
            if config.has_option('DEFAULT_SETTINGS', 'server'):
                setattr(self, 'server', config.get('DEFAULT_SETTINGS', 'server'))
            if config.has_option('DEFAULT_SETTINGS', 'port'):
                setattr(self, 'port', config.getint('DEFAULT_SETTINGS', 'port'))
            if config.has_option('DEFAULT_SETTINGS', 'user'):
                setattr(self, 'user', config.get('DEFAULT_SETTINGS', 'user'))
            if config.has_option('DEFAULT_SETTINGS', 'password'):
                setattr(self, 'password', config.get('DEFAULT_SETTINGS', 'password'))
            if config.has_option('DEFAULT_SETTINGS', 'stalerollback'):
                setattr(
                    self,
                    'stalerollback',
                    config.get('DEFAULT_SETTINGS', 'stalerollback'),
                )
            if config.has_option('DEFAULT_SETTINGS', 'dictcursor'):
                setattr(
                    self,
                    'dictcursor',
                    config.getboolean('DEFAULT_SETTINGS', 'dictcursor'),
                )

        for attribute in (
            loopAttribute
            for loopAttribute in self.__dict__.keys()
            if loopAttribute in args
        ):
            setattr(self, attribute, args[attribute])

        missingAttributes = [
            requiredAttributes
            for requiredAttributes in ['database', 'server', 'port', 'user', 'password']
            if getattr(self, requiredAttributes) is None
        ]

        if missingAttributes:
            raise AttributeError(
                "Required attributes(s) '"
                + ",".join(missingAttributes)
                + "' not supplied!\n"
            )

    def mysqlConnect(self):
        attemptedServer = None
        try:
            if type(self.server) is list:
                for listServer in self.server:
                    attemptedServer = listServer
                    self.connection = MySQLdb.connect(
                        user=self.user,
                        passwd=self.password,
                        host=attemptedServer,
                        port=self.port,
                    )
                    return
            else:
                attemptedServer = self.server
                self.connection = MySQLdb.connect(
                    user=self.user,
                    passwd=self.password,
                    host=attemptedServer,
                    port=self.port,
                )
                return
        except Exception as e:
            connectError = "Silo Database Connection Exception for server %s: %s" % (
                attemptedServer,
                str(e),
            )
            if self.logger:
                self.logger.error(connectError)
            else:
                sys.stderr.write(connectError + "\n")

            raise e

    def updateConnectionCreds(self, user, password, server, port):
        with self.connectionLock:
            self.user = user
            self.password = password
            self.server = server
            self.port = port

    def mysqlCursor(self):
        try:
            cursor = self.connection.ping(True)
        except MySQLdb.Error as e:
            try:
                if e[0] == 2006:
                    self.mysqlConnect()
                else:
                    cursorError = "MySQL Connection Error: %s" % str(e)

                    if self.logger:
                        self.logger.error(cursorError)
                    else:
                        sys.stderr.write(cursorError + "\n")

                    raise e
            except Exception as e:
                cursorError = "MySQL Re-connection Error: %s" % str(e)

                if self.logger:
                    self.logger.error(cursorError)
                else:
                    sys.stderr.write(cursorError + "\n")

                raise e
        except Exception as e:
            cursorError = "Other Re-connection Error: %s" % str(e)

            if self.logger:
                self.logger.error(cursorError)
            else:
                sys.stderr.write(cursorError + "\n")

            raise e

        if self.connection and self.connection is not None:
            try:
                if self.dictcursor:
                    cursor = self.connection.cursor(
                        cursorclass=MySQLdb.cursors.DictCursor
                    )
                    return cursor
                else:
                    cursor = self.connection.cursor()
                    return cursor
            except MySQLdb.Error as e:
                cursorError = "MySQL Error: %s" % str(e)

                if self.logger:
                    self.logger.error(cursorError)
                else:
                    sys.stderr.write(cursorError + "\n")

                raise e
            except Exception as e:
                cursorError = "Other Cursor Error: %s" % str(e)

                if self.logger:
                    self.logger.error(cursorError)
                else:
                    sys.stderr.write(cursorError + "\n")

                raise e
        else:
            cursorError = "MySQL Connection Invalid Error"

            if self.logger:
                self.logger.error(cursorError)
            else:
                sys.stderr.write(cursorError + "\n")

            # cursor failed, throw exception
            raise RuntimeError(cursorError)

    def fetchrows(self):
        # set to true if anything found while using callback,
        # easy way to determine if null fetch
        fetchReturn = False

        if not self.sql:
            fetchrowsError = 'SQL statement required'

            if self.logger:
                self.logger.error(fetchrowsError)
            else:
                sys.stderr.write(fetchrowsError + "\n")

            raise AttributeError(fetchrowsError)

        # sadly only one transaction allowed at a time, threading is
        # weak in Python mysql
        with self.connectionLock:
            # stupid hack to prevent query results from being stale,
            # but don't much care if it succeeds
            if self.stalerollback:
                try:
                    self.connection.rollback()
                except:
                    pass

            dbCursor = self.mysqlCursor()
            if dbCursor:
                try:
                    if self.bindParams:
                        if type(self.bindParams) is list:
                            dbCursor.execute(self.sql, self.bindParams)
                        elif type(self.bindParams) is tuple:
                            dbCursor.execute(self.sql, self.bindParams)
                        else:
                            dbCursor.execute(self.sql, (self.bindParams))
                    else:
                        dbCursor.execute(self.sql)

                    if self.callback:
                        for row in dbCursor.fetchall():
                            fetchReturn = True
                            continueLoop = True
                            if self.callbackParams:
                                if self.dictcursor:
                                    if type(self.callbackParams) is list:
                                        continueLoop = self.callback(
                                            row, *self.callbackParams
                                        )
                                    else:
                                        continueLoop = self.callback(
                                            row, **self.callbackParams
                                        )
                                else:
                                    if type(self.callbackParams) is list:
                                        continueLoop = self.callback(
                                            *(list(row) + self.callbackParams)
                                        )
                                    else:
                                        continueLoop = self.callback(
                                            *list(row), **self.callbackParams
                                        )
                            else:
                                if self.dictcursor:
                                    continueLoop = self.callback(row)
                                else:
                                    continueLoop = self.callback(*list(row))
                            if not continueLoop:
                                break
                    else:
                        self.fetchResults = dbCursor.fetchall()
                except MySQLdb.Error as e:
                    fetchrowsError = "fetchrows MySQL Error: %s" % str(e)

                    if self.logger:
                        self.logger.error(fetchrowsError)
                    else:
                        sys.stderr.write(fetchrowsError + "\n")

                    raise e
                except Exception as e:
                    fetchrowsError = 'fetchrows Other Error: %s' % str(e)

                    if self.logger:
                        self.logger.error(fetchrowsError)
                    else:
                        sys.stderr.write(fetchrowsError + "\n")

                    raise e
                finally:
                    dbCursor.close()
            else:
                fetchrowsError = 'Invalid cursor'

                if self.logger:
                    self.logger.error(fetchrowsError)
                else:
                    sys.stderr.write(fetchrowsError + "\n")

                raise RuntimeError(fetchrowsError)

            return fetchReturn

    def execute(self):
        if not self.sql:
            executeError = 'SQL statement required'

            if self.logger:
                self.logger.error(executeError)
            else:
                sys.stderr.write(executeError + "\n")

            raise AttributeError(executeError)

        with self.connectionLock:
            dbCursor = self.mysqlCursor()
            if dbCursor:
                try:
                    if self.bindParams:
                        if type(self.bindParams) is list:
                            dbCursor.execute(self.sql, self.bindParams)
                        elif type(self.bindParams) is tuple:
                            dbCursor.execute(self.sql, self.bindParams)
                        else:
                            dbCursor.execute(self.sql, (self.bindParams))
                    else:
                        dbCursor.execute(self.sql)

                    if self.callback:
                        if self.callbackParams:
                            if type(self.callbackParams) is list:
                                self.callback(dbCursor, *self.callbackParams)
                            else:
                                self.callback(dbCursor, **self.callbackParams)
                except MySQLdb.Error as e:
                    executeError = "execute MySQL Error: %s" % str(e)

                    if self.logger:
                        self.logger.error(executeError)
                    else:
                        sys.stderr.write(executeError + "\n")

                    raise e
                except Exception as e:
                    executeError = 'execute Other Error: %s' % str(e)

                    if self.logger:
                        self.logger.error(executeError)
                    else:
                        sys.stderr.write(executeError + "\n")

                    raise e
                finally:
                    dbCursor.close()
            else:
                executeError = 'Invalid cursor'

                if self.logger:
                    self.logger.error(executeError)
                else:
                    sys.stderr.write(executeError + "\n")

                raise RuntimeError(executeError)

