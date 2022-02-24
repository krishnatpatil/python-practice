#!/usr/local/bin/python

"""sampleMaintenanceJobs.py

Task to delete schedules older than 60 days. 

Normally run on demand by cron, can also be run on demand.

Conditional logging to file and/or console.

"""

import sys
import os
import threading
import datetime
import Queue
import time
import signal
import re
from pathlib import Path

import utils.argument_parser as Parser
import Utils.Logger as Logger


# class to indicate process terminated by testing related signals
class TestTriggeredExit(object):
    def __init__(self):
        self.exit_status = False

    def signal_catch(self, signum, frame):  # pylint: disable=unused-argument
        self.exit_status = True


def main(argv):
    """
    Standard main. Gets command line args, proceses config file,
    invokes primary task function.

    Args:
        argv - command line args

    Returns:
        None

    Raises:
        None
    """

    instance_test_triggered_exit = TestTriggeredExit()

    script_path = Path(__file__).resolve()
    script_name = script_path.name

    parameters = Parser.handle_args(script_path, script_name, argv)

    logger = Logger.Logger(
        parameters['LOGMAINTENANCE'], parameters['LOGLEVEL'], parameters['LOGTO']
    )

    # log the current execution PID
    pid = os.getpid()

    if (
        'SERVER' not in parameters
        or not parameters['SERVER']
        or parameters['SERVER'].lower() == 'none'
    ):
        logger.warning('No stack specified, exiting')
        sys.exit(0)
    else:
        logger.info(
            'Starting validation on stack {}. PID - {}'.format(
                parameters['SERVER'], pid
            )
        )

    if parameters['TEST']:
        signal.signal(signal.SIGALRM, instance_test_triggered_exit.signal_catch)

    (stack_server, api_user, api_password, dbuser, dbpassword, debug) = (
        parameters['SERVER'],
        parameters['APIUSER'],
        parameters['APIPASSWORD'],
        parameters['DBUSER'],
        parameters['DBPASSWORD'],
        parameters['DEBUG'],
    )

    (delete_queue_pool, delete_thread_pool) = create_delete_threads(
        logger, stack_server, api_user, api_password, debug
    )

    fetch_thread = create_fetch_thread(
        logger, stack_server, api_user, api_password, delete_queue_pool, debug
    )

    manage_threads(logger, fetch_thread, delete_queue_pool, delete_thread_pool)

    logger.info("Exiting")

    return instance_test_triggered_exit.exit_status


def fetch_schedule_ids(logger, stack_server, api_user, api_password):
    """
    Fetch Schedules id from app that have a start date older than 60
    days.

    Args:
        logger - logger instance
        stackserver - server to connect to
        api_user - API user
        api_password - API password

    Returns:
        schedules id as dictionary keys

    Raises:
        connection error
    """
    schedules = []

    # get date of the day 60 days old from now and convert to epoch.
    date_passed = datetime.datetime.now().replace(microsecond=0) - datetime.timedelta(
        days=60
    )
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch_time = int(time.mktime(time.strptime(str(date_passed), pattern)))
    connection_instance = None

    connection_instance = APIConnection(
        user=api_user,
        password=api_password,
        portal=stack_server,
        retry500=10,
        logger=logger,
    )

    # construct url of schedules with start date older than 60 days,
    # CHG in description and with No reccurance.
    connection_instance.uri = (
        '/api/schedule?limit=!&filter.0.dtstart.max={0}\
                                   &filter.0.recur_expr.eq=0\
                                   &filter.0.description.begins_with=CHG'
    ).format(epoch_time)
    connection_instance.requestType = 'GET'
    connection_instance.httpRequest()

    if (
        connection_instance.responseCode > 199
        and connection_instance.responseCode < 300
        and connection_instance.responseJSON['result_set']
    ):
        for result in connection_instance.responseJSON['result_set']:
            schedule_event = re.search(r'schedule[^\d]+([\d]+)', result['URI'])
            schedules.append(schedule_event.group(1))

    return schedules


def delete_task_and_schedules(
    logger,
    stack_server,
    api_user,
    api_password,
    schedules,
    delete_queue_pool,
    debug,  # pylint: disable=unused-argument
):
    """
    Fetch tasks id of schedules from app and then delete 
    tasks and schedules. 

    Args:
        logger - logger instance
        stackserver - server to connect to
        api_user - API user
        api_password - API password
        schedules - list of schedule IDs to fetch tasks for and delete both
        delete_queue_pool - task queue to post delete requests to
        debug - debug flag

    Returns:
        Tasks id as dictionaty values.

    Raises:
        connection error
    """
    connection_instance = None

    connection_instance = APIConnection(
        user=api_user,
        password=api_password,
        portal=stack_server,
        retry500=10,
        logger=logger,
    )

    for schedule_id in schedules:
        connection_instance.uri = '/api/schedule/{0}/task'.format(schedule_id)
        connection_instance.requestType = 'GET'
        connection_instance.httpRequest()
        if (
            connection_instance.responseCode > 199
            and connection_instance.responseCode < 300
            and connection_instance.responseJSON['result_set']
        ):
            for result in connection_instance.responseJSON['result_set']:
                schedule_task = re.search(r'\/task\/([\d]+)', result['URI'])
                delete_queue_pool['tasks'].put({'id': schedule_task.group(1)})
        delete_queue_pool['schedules'].put({'id': str(schedule_id)})


def create_fetch_thread(
    logger, stack_server, api_user, api_password, delete_queue_pool, debug
):
    """
    Do schedule and task fetch thread start

    Args:
        logger - logger instance
        stack_server -  server to connect to
        api_user - API user
        api_password - API password 
        delete_queue_pool - task queue to post delete IDs to
        debug - debug flag

    Returns:
        None

    Raises:
        None
    """
    logger.info('Creating fetch thread')

    fetch_thread_instance = threading.Thread(
        target=delete_task_and_schedules,
        args=(
            logger,
            stack_server,
            api_user,
            api_password,
            fetch_schedule_ids(logger, stack_server, api_user, api_password,),
            delete_queue_pool,
            debug,
        ),
    )
    fetch_thread_instance.start()

    return fetch_thread_instance


def create_delete_threads(logger, stack_server, api_user, api_password, debug):
    """
    Do schedule and task delete operation of app matched schedules

    Spawns threads to do the corrections, queue controlled

    Args:
        logger - logger instance
        stack_server - server to connect to
        api_user - API user
        api_password - API password 
        debug - debug flag

    Returns:
        None

    Raises:
        None
    """
    logger.info('Creating schedule and task delete threads')

    num_api_threads = 4

    thread_methods = {
        'schedules': delete_schedules,
        'tasks': delete_tasks,
    }
    thread_pool = {
        'schedules': [],
        'tasks': [],
    }
    queue_pool = {
        'schedules': Queue.Queue(),
        'tasks': Queue.Queue(),
    }

    for thread_name in thread_methods:
        for _ in range(num_api_threads):
            thread_instance = threading.Thread(
                target=thread_methods[thread_name],
                args=(
                    logger,
                    stack_server,
                    api_user,
                    api_password,
                    queue_pool[thread_name],
                    debug,
                ),
            )
            thread_instance.start()
            thread_pool[thread_name].append(thread_instance)

    return (queue_pool, thread_pool)


def manage_threads(
    logger, fetch_thread, delete_queue_pool, delete_thread_pool,
):
    """
    Do schedule and task delete operation of app matched schedules

    Spawns threads to do the corrections, queue controlled

    Args:
        logger - logger instance
        fetch_thread - thread instance of schedule and task fetcher
        delete_queue_pool - task queues of schedule and task delete threads
        delete_thread_pool - task instance pools of schedule and task delete threads

    Returns:
        None

    Raises:
        None
    """
    logger.info('Starting thread cleanup')

    num_api_threads = 4

    # TBD check fetch_thread terminate

    fetch_thread.join()

    for _, thread_queue in delete_queue_pool.items():
        for _ in range(num_api_threads):
            thread_queue.put({'id': 'done'})

    for _, thread_queue in delete_queue_pool.items():
        while not thread_queue.empty():
            time.sleep(0.2)

    for _, thread_instances in delete_thread_pool.items():
        for thread_instance in thread_instances:
            thread_instance.join()

    for _, thread_queue in delete_queue_pool.items():
        thread_queue.join()

    logger.info('Finished thread cleanup')


def delete_tasks(
    logger, stack_server, api_user, api_password, work_queue, debug,
):
    """
    Thread to delete tasks
    
    Does a API delete for the specified tasks 

    Args:
        logger - logger instance
        stack_server - server to connect to
        api_user - API user
        api_password - API password 
        debug - if set, don't do any actual updates
        work_queue - queue to read tasks from
        debug - debug flag

    Returns:
        None

    Raises:
        None
    """
    logger.info(
        'Starting delete tasks thread {}'.format(str(threading.current_thread().name))
    )

    connection_instance = None

    connection_instance = APIConnection(
        user=api_user,
        password=api_password,
        portal=stack_server,
        retry500=10,
        logger=logger,
        retryExceptions=5,
    )

    done = False

    while not done:
        id = None  # pylint: disable=redefined-builtin

        try:
            message = work_queue.get(True, 10)
            if message['id'] == 'done':
                done = True
            else:
                id = message['id']

            work_queue.task_done()
        except Queue.Empty:
            # ignore timeout
            pass
        except Exception:
            pass

        if id:
            logger.info('Deleting task {0}'.format(id))
            connection_instance.uri = '/api/task/{0}'.format(id)
            connection_instance.requestType = 'DELETE'
            if not debug:
                connection_instance.tryAPIRequest()
            connection_instance.requestType = 'GET'

    logger.info(
        'Exiting delete tasks thread {}'.format(str(threading.current_thread().name))
    )


def delete_schedules(
    logger, stack_server, api_user, api_password, work_queue, debug,
):
    """
    Thread to delete schedules
    
    Does a API delete for the specified schedules 

    Args:
        logger - logger instance
        stack_server - server to connect to
        api_user - API user
        api_password - API password 
        debug - if set, don't do any actual updates
        work_queue - queue to read tasks from
        debug - debug flag

    Returns:
        None

    Raises:
        None
    """
    logger.info(
        'Starting delete schedules thread {}'.format(
            str(threading.current_thread().name)
        )
    )

    connection_instance = None

    connection_instance = APIConnection(
        user=api_user,
        password=api_password,
        portal=stack_server,
        retry500=10,
        logger=logger,
        retryExceptions=5,
    )

    done = False

    while not done:
        id = None  # pylint: disable=redefined-builtin

        try:
            message = work_queue.get(True, 10)
            if message['id'] == 'done':
                done = True
            else:
                id = message['id']

            work_queue.task_done()
        except Queue.Empty:
            # ignore timeout
            pass
        except Exception:
            pass

        if id:
            logger.info('Deleting schedule {0}'.format(id))
            connection_instance.uri = '/api/schedule/{0}'.format(id)
            connection_instance.requestType = 'DELETE'
            if not debug:
                connection_instance.tryAPIRequest()
            connection_instance.requestType = 'GET'

    logger.info(
        'Exiting delete schedules thread {}'.format(
            str(threading.current_thread().name)
        )
    )


if __name__ == "__main__":
    main(sys.argv[1:])

