import os
from dotenv import load_dotenv
from openai import OpenAI
import ollama
import json
import re
from datetime import datetime, timedelta
import time
import asyncio
from telegram_get_chats import telegram_get_chats
from google_email_calendar_libs import google_calendar_event_creater, gmail_with_attachments_reader, logger

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

#get data source details
INCLUDE_GMAIL = os.getenv('INCLUDE_GMAIL')
if not INCLUDE_GMAIL:
    # If INCLUDE_GMAIL is not set, use the default value
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    INCLUDE_GMAIL = "True"
    print("INCLUDE_GMAIL not defined in the environment file. Using default value.")

INCLUDE_TELEGRAM = os.getenv('INCLUDE_TELEGRAM')
if not INCLUDE_TELEGRAM:
    # If INCLUDE_TELEGRAM is not set, use the default value
    # This is useful for testing in a local environment
    # or if the environment variable is not set
    INCLUDE_TELEGRAM = "True"
    print("INCLUDE_TELEGRAM not defined in the environment file. Using default value.")

###########################################################
# Function to get the time window for fetching emails and telegram messages
# ###########################################################
def get_time_window():
        # Check if the timestamp file exists
    if os.path.exists(TS_FILE):
        with open(TS_FILE, "r") as f:
            lines = f.readlines()
        if lines:
            last_read_time_str = lines[0].strip().split(":", 1)[1]
            last_read_time = datetime.strptime(last_read_time_str, "%Y-%m-%d %H:%M:%S.%f")
            logger('INFO',f"Last read time: {last_read_time}")
        else:
            # Empty file, use default
            last_read_time = (datetime.now() - timedelta(days=NO_OF_DAYS_TO_LOOK_BACK))
            logger('INFO',f"Timestamp file is empty. Defaulting last read time to: {last_read_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    else:
        # File not found, use default
        last_read_time = (datetime.now() - timedelta(days=NO_OF_DAYS_TO_LOOK_BACK))
        logger('INFO',f"Timestamp file not found. Defaulting last read time to: {last_read_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")              
    
    # for gmail api the start time and end time should be in epoch format
    after_ts = int(time.mktime(last_read_time.timetuple()))
    before_ts = int(time.mktime(datetime.now().timetuple()))

    # Convert epoch time to human-readable format for debugging
    after_ts_human_readable = datetime.fromtimestamp(after_ts).strftime('%Y-%m-%d %H:%M:%S')
    before_ts_human_readable = datetime.fromtimestamp(before_ts).strftime('%Y-%m-%d %H:%M:%S')
    logger('INFO', f"Fetching emails from {after_ts_human_readable} to {before_ts_human_readable}")

    # Create or overwrite the timestamp file
    with open(TS_FILE, "w") as f: 
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        f.write(f"LAST_READ_TIME:{timestamp}")

    return after_ts, before_ts
#end

###########################################################
# Function to check Gmail and create calendar events
# ###########################################################
def ai_agent_create_calendar_event():

  # Load environment variables
  load_dotenv(override=True)
  MODEL = os.getenv('LLM_MODEL')
  if not MODEL:
      logger('INFO', "LLM_MODEL not defined in the environment file. Using default model.")
      MODEL = 'gpt-4o-mini'  # Default model if not defined in the environment file
  else:
      logger('INFO',f"LLM_MODEL used is {MODEL}")

  api_key = os.getenv('OPENAI_API_KEY')

  if api_key and api_key.startswith('sk-proj-') and len(api_key)>10:
      logger('INFO', "API key looks good so far")
  else:
      logger('INFO', "There might be a problem with your API key? Please visit the troubleshooting notebook!")


  # Get the time window for fetching emails and telegram messages
  after_ts, before_ts = get_time_window()

  current_time = datetime.now()
  formatted_time = current_time.strftime("%A, %B %d, %Y (%Y-%m-%dT%H:%M:%S%z)")

  user_prompt = ""
  system_prompt = ""

  system_prompt += """
  System Time Context: Today is """ + formatted_time + """ 
  When interpreting dates like “this month” or “next week,” use this as the current date.
  A "week" is defined as 7 days, and a "month" is defined as 30 days.
  "week" starts on Monday and ends on Sunday.
  "month" starts on the first day of the month and ends on the last day of the month.
  "year" starts on January 1st and ends on December 31st.
  "day" starts at 00:00 and ends at 23:59.
  """

  #if email data to be included
  if INCLUDE_GMAIL == "True":    
    system_prompt += """
    You are a personal assistant who can check my emails, identify any appointments and create them in my google calendar.
    """
    #if email data to be included
    user_prompt += """
    Pls identify appointments based on the email data and email attachements given below.
    """
  
  #if telegram data to be included
  if INCLUDE_TELEGRAM == "True":
    system_prompt += """
    You are a personal assistant who can check my telegram messages, identify any appointments and create them in my google calendar.
    Attendees is not required for Telegram messages.
    """
    user_prompt += """
    Pls identify appointments based on the telegram chat messages data given below.
    """

  user_prompt += """
  Consider 12:30 PM as my lunch time and 7:00 PM as my dinner time.
  Give my appointment details in the format that is needed to create event in my google calendar.
  Use the below JSON format and create a list of dictionaries.
  Only output the JSON content, and make sure it's valid.
  {
    "summary": "Appointment Title",
    "location": "Location",
    "description": "Description of the appointment",
    "start": {
      "dateTime": "2025-04-02T12:30:00+05:30",
      "timeZone": "Asia/Kolkata"
    },
    "end": {
      "dateTime": "2025-04-02T13:30:00+05:30",
      "timeZone": "Asia/Kolkata"
    },
    "attendees": [
      {'email': "example@example.com"},
      ],
    "reminders": {
      "useDefault": false,
      "overrides": [
        {"method": "email", "minutes": 1440},
        {"method": "popup", "minutes": 10}
      ]
    }
  }
  The appointment details should be in the above format.
  """

  #if email data to be included
  if INCLUDE_GMAIL == "True":
    user_prompt += """
    For any attachments, parse the attachment and consider if there are any appointments in the attachment image or any other format.
    If the attachment contains a flight, train, or bus ticket, extract the relevant travel details and convert them into a 
    calendar appointment. Use the departure and arrival dates and times from the ticket to set the appointment duration. 
    Include the origin and destination in the appointment title or description. Add the list of passengers (if available) 
    to the appointment body.
    If there are any appointments in the attachment, include them in the above format.
    Here are my emails and email attachement details: \n
    """ 
    user_prompt += gmail_with_attachments_reader(after_ts, before_ts)

  #if telegram data to be included
  if INCLUDE_TELEGRAM == "True":
    user_prompt += """
    Here are my messages details from Telegram: \n
    """
    user_prompt += asyncio.run(telegram_get_chats(after_ts, before_ts))


  openai = OpenAI()

  # Verson without streaming results
  response = openai.chat.completions.create(
          model=MODEL,
          messages=[
              {"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt},
            ]
      )
  result = response.choices[0].message.content
  logger('DEBUG', result)

  if not result.strip():
    logger('INFO', "The result is empty. No events to process.")
    return
  
  else:
  
    # Extract all JSON blocks from the result
    events = re.findall(r"```json(.*?)```", result, re.DOTALL)

    # Check if events list is empty
    if not events:
        logger('INFO', "No JSON-formatted events found in the email content.")
        return  # Exit the function gracefully

    # Extract the actual JSON string (since it's inside a list)
    try:
        json_string = events[0]  # Get the first element, which is the JSON string
        logger('DEBUG',f"Extracted JSON string: {json_string}")
        json_events = json.loads(json_string)  # Convert the string into a Python list of dictionaries
    except (IndexError, json.JSONDecodeError) as e:
        logger('INFO', f"Error processing events: {e}")
        return  # Exit the function gracefully

    # Process the events
    for i, event in enumerate(json_events, start=1):
        try:
            # Invoke Google Calendar API to create event
            logger('DEBUG',f"Creating event {i}: {event}")
            google_calendar_event_creater(event)
        except Exception as e:
            logger('INFO', f"Error creating event {i}: {e}")
#end