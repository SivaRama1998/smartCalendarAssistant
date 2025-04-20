##########################################################
# Modules
##########################################################
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import base64
from email import message_from_bytes
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
 
# Define the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly','https://www.googleapis.com/auth/calendar.events']

################################
#LOAD ENVIRONMENT VARIABLES
################################
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

#get attachments directory
ATTACHMENTS_DIR = os.getenv('ATTACHMENTS_DIR')

#get secrets directory
SECRETS_DIR = os.getenv('SECRETS_DIR')

#get secrets directory
SECRETS_DIR = os.getenv('SECRETS_DIR')
if not SECRETS_DIR:
    # If SECRETS_DIR is not set, use the current directory
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    SECRETS_DIR = os.path.dirname(os.path.abspath(__file__))
    print("SECRETS_DIR not defined in the environment file. Using default directory.")

#get credentials file
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
if not CREDENTIALS_FILE:
    # If CREDENTIALS_FILE is not set, use the default file name
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    CREDENTIALS_FILE = os.path.join(SECRETS_DIR, 'credentials.json')
    print("CREDENTIALS_FILE not defined in the environment file. Using default file name.")

#get token file
TOKEN_FILE = os.getenv('TOKEN_FILE')
if not TOKEN_FILE:
    # If TOKEN_FILE is not set, use the default file name
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    TOKEN_FILE = os.path.join(SECRETS_DIR, 'token.pickle')
    print("TOKEN_FILE not defined in the environment file. Using default file name.")
    
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

#get ts file name
ts_file_name = os.getenv('DAEMON_TS_FILE')
if not ts_file_name:
    # If DAEMON_TS_FILE is not set, use the default file name
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    ts_file_name = "daemon_google_calendar_event_creater.ts"
    print("DAEMON_TS_FILE not defined in the environment file. Using default file name.")
TS_FILE = os.path.join(DAEMON_DIR, ts_file_name)

#get number of days to look back for emails
# Number of days to look back for emails
# This is used to set the default last read time if the timestamp file is not found or is empty
# or if the timestamp file is not found or is empty
NO_OF_DAYS_TO_LOOK_BACK = os.getenv('NO_OF_DAYS_TO_LOOK_BACK')
# Convert NO_OF_DAYS_TO_LOOK_BACK to an integer
try:
    NO_OF_DAYS_TO_LOOK_BACK = int(NO_OF_DAYS_TO_LOOK_BACK)
except (ValueError, TypeError):
    print("Invalid value for NO_OF_DAYS_TO_LOOK_BACK. Defaulting to 7 days.")
    NO_OF_DAYS_TO_LOOK_BACK = 7

#####################################################
# Log writing function
#####################################################
def logger(log_level, msg):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if log_level == "INFO" and LOG_LEVEL in ["INFO", "DEBUG"]:
            f.write(current_time + ' : ' + log_level + ' : ' + msg + '\n')
        elif log_level == "DEBUG" and LOG_LEVEL == "DEBUG":
            f.write(current_time + ' : ' + log_level + ' : ' + msg)
        elif log_level == "WARNING" and LOG_LEVEL in ["WARNING", "ERROR", "CRITICAL"]:
            f.write(current_time + ' : ' + log_level + ' : ' + msg)
        elif log_level == "ERROR" and LOG_LEVEL in ["ERROR", "CRITICAL"]:
            f.write(current_time + ' : ' + log_level + ' : ' + msg)
        elif log_level == "CRITICAL":
            f.write(current_time + ' : ' + log_level + ' : ' + msg)
#end

############################################################
# Authenticate Gmail and Google Calendar
############################################################
def authenticate(api_type):

    logger('INFO', f"Authenticating for {api_type} API...")
    creds = None

    # Check if token.pickle exists (stores user credentials)
    # credentials_file_name = os.path.join(SECRETS_DIR, CREDENTIALS_FILE)

    # Check if token.pickle exists (stores user credentials)
    # token_file_name = os.path.join(SECRETS_DIR, TOKEN_FILE)

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate the user
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    if (api_type == 'Gmail'):
        # Build the Gmail API service
        service = build('gmail', 'v1', credentials=creds)
    elif (api_type == 'GoogleCalendar'):
        # Build the Google Calendar API service
        service = build('calendar', 'v3', credentials=creds)
    else:
        raise ValueError("Invalid API type specified. Use 'Gmail' or 'GoogleCalendar'.")
    return service


############################################################
# Fetch emails
############################################################
def get_emails(service):

    # Check if the timestamp file exists
    if os.path.exists(TS_FILE):
        with open(TS_FILE, "r") as f:
            lines = f.readlines()
        if lines:
            last_read_time_str = lines[0].strip().split(":", 1)[1]
            last_read_time = datetime.strptime(last_read_time_str, "%Y-%m-%d %H:%M:%S.%f")
            logger('INFO', f"Last read time: {last_read_time}")
        else:
            # Empty file, use default
            last_read_time = (datetime.now() - timedelta(days=NO_OF_DAYS_TO_LOOK_BACK))
            logger('INFO', f"Timestamp file is empty. Defaulting last read time to: {last_read_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    else:
        # File not found, use default
        last_read_time = (datetime.now() - timedelta(days=NO_OF_DAYS_TO_LOOK_BACK))
        logger('INFO', f"Timestamp file not found. Defaulting last read time to: {last_read_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")              
    

    # for gmail api the start time and end time should be in epoch format
    after_ts = int(time.mktime(last_read_time.timetuple()))
    before_ts = int(time.mktime(datetime.now().timetuple()))

    # Convert epoch time to human-readable format for debugging
    after_ts_human_readable = datetime.fromtimestamp(after_ts).strftime('%Y-%m-%d %H:%M:%S')
    before_ts_human_readable = datetime.fromtimestamp(before_ts).strftime('%Y-%m-%d %H:%M:%S')
    logger('INFO',f"Fetching emails from {after_ts_human_readable} to {before_ts_human_readable}")

    # Create or overwrite the timestamp file
    with open(TS_FILE, "w") as f: 
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        f.write(f"LAST_READ_TIME:{timestamp}")

    query = f'after:{after_ts} before:{before_ts}'

    # query = f'after:{last_read_time} before:{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}'  # Query for emails from the specific timestamp to now
    #query = f'after:2025-03-23 before:2025-03-25'  # Query for emails on the specific date
    logger('DEBUG',f"Query: {query}")

    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    logger('INFO',f"Total emails found: {len(messages)} \n")
   
    emails = ""
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        payload = msg['payload']
        headers = payload.get('headers', [])
       
        # Extract subject and sender
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), None)
        sender = next((header['value'] for header in headers if header['name'] == 'From'), None)
        logger('DEBUG',f"Subject: {subject}")
        logger('DEBUG',f"From: {sender}")
        emails += f"Subject: {subject}\n"
        emails += f"From: {sender}\n"
       
        # Extract email body
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode()
                    logger('DEBUG',f"Body: {body}")
                    emails += f"Body: {body}\n"
                    break
        else:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode()
            logger('DEBUG',f"Body: {body}")
            emails += f"Body: {body}\n"
    return emails

############################################################
# gmail_reader function
############################################################
def gmail_reader():
    # Authenticate and get the Gmail API service
    logger('INFO', "Authenticating...")
    service = authenticate("Gmail")
    logger('INFO', "Authenticated successfully.")
   
    # Fetch and print emails for the specified date
    emails = get_emails(service)

    if not emails.strip():
        logger('INFO', "No emails found.")
        return "No emails found."
    return emails

    # Note: The script will save the user's credentials in token.pickle for future use.
    # This file should be kept secure and not shared.
    # You can delete token.pickle to force re-authentication.
    # Ensure you have the credentials.json file in the same directory as this script.
    # The credentials.json file can be obtained from the Google Cloud Console.
    # Make sure to enable the Gmail API for your project in the Google Cloud Console.
    # The script will open a web browser for authentication if needed.
    # Follow the instructions to grant access to your Gmail account.
    # After authentication, the script will fetch and print emails for the specified date.
    # The script will print the subject, sender, and body of each email.


############################################################
# Google Calendar Event Creator
############################################################
def google_calendar_event_creater(event):
    logger('INFO', "Authenticating...")
    service = authenticate("GoogleCalendar")
    logger('INFO', "Authenticated successfully.")

    # Extract relevant details from the event
    summary = event.get("summary")
    start_time = event["start"]["dateTime"]
    end_time = event["end"]["dateTime"]

    # Convert to datetime objects (assuming ISO format)
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)

    # Search for existing events that overlap with this one
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    existing_events = events_result.get('items', [])

    for existing_event in existing_events:
        if existing_event.get('summary') == summary:
            logger('INFO', "Duplicate event found. Skipping creation.")
            return  # Don't create the event again

    # If no duplicate found, insert the event
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    logger('INFO', f"Event created: {created_event.get('htmlLink')}")
    logger('INFO', "Event created successfully.\n\n")

#end

##################################################################
# Get emails with attachments
##################################################################
def get_emails_with_attachments(service, after_ts, before_ts):

    query = f'after:{after_ts} before:{before_ts}'

    logger('INFO', f"Query: {query}")
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    logger('INFO', f"Total emails found: {len(messages)} \n")

    emails = ""
    all_attachments = []

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        payload = msg['payload']
        headers = payload.get('headers', [])
       
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), None)
        sender = next((header['value'] for header in headers if header['name'] == 'From'), None)

        emails += f"Subject: {subject}\n"
        emails += f"From: {sender}\n"

        parts = payload.get('parts', [])
        email_body_found = False

        for part in parts:
            filename = part.get("filename")
            mime_type = part.get("mimeType")
            body = part.get("body", {})
            data = body.get("data")
            attachment_id = body.get("attachmentId")

            # Get email body
            if mime_type == "text/plain" and data and not email_body_found:
                decoded_body = base64.urlsafe_b64decode(data).decode()
                emails += f"Body: {decoded_body}\n"
                email_body_found = True

            # Download attachment
            if filename and attachment_id:
                attachment = service.users().messages().attachments().get(
                    userId='me',
                    messageId=message['id'],
                    id=attachment_id
                ).execute()

                file_data = base64.urlsafe_b64decode(attachment['data'])

                filepath = os.path.join(ATTACHMENTS_DIR, filename)
                print(f"Saving attachment to {filepath}")
                with open(filepath, 'wb') as f:
                    f.write(file_data)

                emails += f"Attachment saved: {filepath}\n"
                all_attachments.append(filepath)

        # If no plain/text part found, fallback
        if not email_body_found and 'body' in payload and 'data' in payload['body']:
            decoded_body = base64.urlsafe_b64decode(payload['body']['data']).decode()
            emails += f"Body: {decoded_body}\n"

    return emails, all_attachments


############################################################
# Gmail Reader with attachments
############################################################
def gmail_with_attachments_reader(after_ts, before_ts):
    # Authenticate and get the Gmail API service
    logger('INFO', "Authenticating...")
    service = authenticate("Gmail")
    logger('INFO', "Authenticated successfully.")
      
    # Fetch and print emails for the specified date
    emails, attachments = get_emails_with_attachments(service,after_ts,before_ts)
    logger('DEBUG', emails)
    emails += "\n\nAttachments:\n"

    for attachment in attachments:
        emails += f"{attachment}\n"
        logger('DEBUG', attachment)
    
    # Print the email content
    logger('DEBUG', "Email content:\n")
    logger('DEBUG', emails)
    return emails