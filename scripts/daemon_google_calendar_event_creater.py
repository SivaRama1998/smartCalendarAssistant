# This script creates a daemon that runs in the background and logs its activity.
# It can be started, stopped, or restarted using command-line arguments.
import time
import os
import sys
import signal
import platform
import threading
import subprocess

from datetime import datetime
from dotenv import load_dotenv
from ai_agent_google_calendar_event_creater import ai_agent_create_calendar_event

IS_WINDOWS = platform.system() == "Windows"

#LOAD ENVIRONMENT VARIABLES
load_dotenv(override=True)

#get base directory
base_dir_name = os.getenv('BASE_DIR')
if base_dir_name:
    BASE_DIR = os.path.join(base_dir_name)
else:
    # If BASE_DIR is not set, use the current directory
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

#get log directory
LOG_DIR = os.getenv('LOG_DIR')
if not LOG_DIR:
    # If LOG_DIR is not set, use the default directory
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    print("LOG_DIR not defined in the environment file. Using default directory.")

log_file_name = os.getenv('DAEMON_LOG_FILE')
if not log_file_name:
    # If DAEMON_LOG_FILE is not set, use the default file name
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    log_file_name = "daemon_google_calendar_event_creater.log"
    print("DAEMON_LOG_FILE not defined in the environment file. Using default file name.")
LOG_FILE = os.path.join(LOG_DIR, log_file_name)

#get logging level
LOG_LEVEL = os.getenv('DAEMON_LOG_LEVEL')
if not LOG_LEVEL:
    # If DAEMON_LOG_LEVEL is not set, use the default level
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    LOG_LEVEL = "INFO"
    print("DAEMON_LOG_LEVEL not defined in the environment file. Using default level.")

#get daemon directory
DAEMON_DIR = os.getenv('DAEMON_DIR')
if not DAEMON_DIR:
    # If DAEMON_DIR is not set, use the default directory
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    DAEMON_DIR = os.path.join(BASE_DIR, 'daemon')
    print("DAEMON_DIR not defined in the environment file. Using default directory.")

#get pid file name
pid_file_name = os.getenv('DAEMON_PID_FILE')
if not pid_file_name:
    # If DAEMON_PID_FILE is not set, use the default file name
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    pid_file_name = "daemon_google_calendar_event_creater.pid"
    print("DAEMON_PID_FILE not defined in the environment file. Using default file name.")
PID_FILE = os.path.join(DAEMON_DIR, pid_file_name)

#get ts file name
ts_file_name = os.getenv('DAEMON_TS_FILE')
if not ts_file_name:
    # If DAEMON_TS_FILE is not set, use the default file name
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    ts_file_name = "daemon_google_calendar_event_creater.ts"
    print("DAEMON_TS_FILE not defined in the environment file. Using default file name.")
TS_FILE = os.path.join(DAEMON_DIR, ts_file_name)

#get sleep time
SLEEP_TIME = os.getenv('DAEMON_SLEEP_TIME')
if not SLEEP_TIME:
    # If DAEMON_SLEEP_TIME is not set, use the default time
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    SLEEP_TIME = 3600  # Default sleep time in seconds (1 hour)
    print("DAEMON_SLEEP_TIME not defined in the environment file. Using default time.")
else:
    try:
        SLEEP_TIME = int(SLEEP_TIME)
    except ValueError:
        print("Invalid sleep time value. Using default time.")
        SLEEP_TIME = 3600
        # Default sleep time in seconds (1 hour)
        print("DAEMON_SLEEP_TIME not defined in the environment file. Using default time.")


#####################################################
# Log writing function
# ###################################################
def write_log(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.ctime()} - {message}\n")

#####################################################
# Daemon Run function.
# ###################################################
def run():
    while True:
        write_log("Daemon is running")

        ## Call the function to check Gmail and create calendar events
        write_log("Calling ai_agent_create_calendar_event()")
        ai_agent_create_calendar_event()
        write_log("ai_agent_create_calendar_event() completed")

        write_log("Sleeping for " + str(SLEEP_TIME) + " seconds...")
        # Sleep for a specified time
        time.sleep(SLEEP_TIME)  

#####################################################
# Start function
# ###################################################
def start():
    print("Starting daemon in start()...")
    if os.path.exists(PID_FILE):
        print("Daemon is already running.")
        return

    if IS_WINDOWS:
        print("Starting background process on Windows...")
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)

        # Start a new subprocess in the background
        subprocess.Popen(
            [python_exe, script_path, "run"],
            creationflags=subprocess.CREATE_NEW_CONSOLE,  # Optional: launch in new terminal window
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("Daemon started in background.")
    else:
        import daemon

        pid = os.getpid()
        with open(PID_FILE, "w") as f:
            f.write(str(pid))

        context = daemon.DaemonContext(
            working_directory=os.getcwd(),
            umask=0o002,
            stdout=open(LOG_FILE, 'a+'),
            stderr=open(LOG_FILE, 'a+')
        )
        with context:
            run()

#####################################################
# Stop function
# ###################################################
def stop():
    if not os.path.exists(PID_FILE):
        print("Daemon is not running.")
        return

    with open(PID_FILE) as f:
        pid = int(f.read())

    try:
        os.kill(pid, signal.SIGTERM)
        print("Daemon stopped.")
        write_log("Daemon stopped successfully.")
    except ProcessLookupError:
        print("Process not found.")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

#####################################################
# Restart function
# ###################################################
def restart():
    stop()
    time.sleep(1)
    start()

#####################################################
# Main function
# ###################################################
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: daemon_google_calendar_event_creater.py start|stop|restart")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "start":
        print("Starting daemon...")
        start()
    elif action == "stop":
        print("Stopping daemon...")
        stop()
    elif action == "restart":
        print("Restarting daemon...")
        restart()
    elif action == "run":
        # This is used by subprocess for Windows
        sys.stdout = open(LOG_FILE, 'a')
        sys.stderr = open(LOG_FILE, 'a')
        pid = os.getpid()
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
        try:
            run()
        finally:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    else:
        print("Unknown command.")
