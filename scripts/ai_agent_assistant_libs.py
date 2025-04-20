import os
import json
import pickle
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from ai_agent_feedback_utils import verify_event_in_calendar, log_feedback, summarize_feedback_log
import gradio as gr

# Load environment variables
load_dotenv(override=True)

SCOPES = ['https://www.googleapis.com/auth/calendar']
last_refresh_time = {"timestamp": None}
auto_refresh_enabled = {"status": True}
current_system_message = {"content": ""}

# Directories
BASE_DIR = os.getenv('BASE_DIR') or os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.getenv('LOG_DIR') or os.path.join(BASE_DIR, 'logs')
BOT_LOG_FILE = os.getenv('BOT_LOG_FILE') or 'bot.log'
LOG_FILE = os.path.join(LOG_DIR, BOT_LOG_FILE)
LOG_LEVEL = os.getenv('BOT_LOG_LEVEL') or "INFO"

SECRETS_DIR = os.getenv('SECRETS_DIR') or BASE_DIR
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE') or os.path.join(SECRETS_DIR, 'credentials.json')
TOKEN_FILE = os.getenv('TOKEN_FILE') or os.path.join(SECRETS_DIR, 'token.pickle')

MODEL = os.getenv('LLM_MODEL') or 'gpt-4o'
openai = OpenAI()

########################################################################
# logger function
########################################################################
def logger(level, msg):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time} : {level} : {msg}\n")

###########################################################################
# ----------------------- Google Calendar Functions -----------------------
###########################################################################
def authenticate(api_type):
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    if api_type == 'GoogleCalendar':
        return build('calendar', 'v3', credentials=creds)
    raise ValueError("Unsupported API type")

########################################################################
# Get calendar events
########################################################################
def get_calendar_events():
    service = authenticate("GoogleCalendar")
    now = datetime.utcnow().isoformat() + 'Z'
    end = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=end, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    if not events:
        return "No upcoming events found."
    text = ""
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        end = e['end'].get('dateTime', e['end'].get('date'))
        text += f"Event: {e.get('summary', 'No title')}\nStart: {start}\nEnd: {end}\nLocation: {e.get('location', 'None')}\nDescription: {e.get('description', 'None')}\n---\n"
    return text

########################################################################
# Refresh system message
########################################################################
def refresh_system_message():
    calendar_events_str = get_calendar_events()

    data = "Here are the calendar event details:\n" + calendar_events_str

    current_time = datetime.now()
    formatted_time = current_time.strftime("%A, %B %d, %Y (%Y-%m-%dT%H:%M:%S%z)")
    system_time_context = "System Time Context: The current date and time is " + formatted_time + ".\n" 

    # Create System Prompt
    system_message = """
    When interpreting dates like “this month” or “next week,” use this as the current date.
    A "week" is defined as 7 days, and a "month" is defined as 30 days.
    "week" starts on Monday and ends on Sunday.
    "month" starts on the first day of the month and ends on the last day of the month.
    "year" starts on January 1st and ends on December 31st.
    "day" starts at 00:00 and ends at 23:59.
    """
    system_message += """
    You are a personal assistant who can read and understand the user's Google Calendar events, which are provided below in this prompt.
    You should use a friendly tone. Summarize events, detect duplicates, and let the user know if there are any conflicting events.
    Appointments are considered the same as calendar events.
    Use the data below to answer any questions about appointments or calendar events.
    ❗ Only answer questions based on the calendar data provided below — you do not have live access to Google Calendar, but this prompt contains all necessary information.
    Do not respond to any questions outside of Google Calendar.
    """ 

    system_message += """
    If the user asks to create an appointment or meeting, ask for attendees email addresses, agenda, and any other details.
    Before creating the appointment, summarize the appointment details and ask for confirmation.
    If the user confirms, create the appointment.
    """

    system_message += """You can also:
    - Cancel events by calling `cancel_calendar_event` with title and optional start date.
    - Accept or reject invites with `respond_to_event`.
    - Modify title, time, location or description with `modify_calendar_event`.
    Always use the appropriate tool call.
    Ask for user confirmation before creating, modifying, canceling or 
    responding with Accept or Reject for an event.
    """

    system_message += """
    For any meeting invites received, ask the user if they want to accept, decline, or tentatively respond. 
    When a user expresses an intent to accept, decline, or tentatively respond to an event, 
    normalize their response to one of the following: "accept", "decline", or "maybe".

    Examples:
    - If the user says "yes", "approve", or "okay" → treat as "accept"
    - If the user says "no", "rejected", or "not coming" → treat as "decline"
    - If the user says "unsure", "might", or "thinking about it" → treat as "maybe"

    When calling a function to respond to an event, always pass only the normalized value ("accept", "decline", or "maybe") as the `response`.
    """
    
    if summarize_feedback_log()["negative"] > summarize_feedback_log()["positive"]:
        system_message += "\n⚠️ Note: Users have reported some issues recently. Double-check confirmations!"

    system_message_with_data = system_time_context + system_message + data

    current_system_message["content"] = system_message_with_data
    logger('DEBUG', current_system_message["content"])

    last_refresh_time["timestamp"] = datetime.now()

    logger('INFO', "System message updated.")
#end

########################################################################
# Create calendar event
########################################################################
def create_calendar_event(title, start_time, end_time, description="", location="", attendees=None):
    service = authenticate("GoogleCalendar")
    attendee_list = [{"email": email} for email in attendees] if attendees else []
    event = {
        'summary': title,
        'location': location,
        'description': description,
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        'attendees': attendee_list,
    }
    created = service.events().insert(calendarId='primary', body=event).execute()
    return f"✅ Event '{title}' created from {start_time} to {end_time}."

########################################################################
# Cancel calendar event
########################################################################
def cancel_calendar_event(event_title, start_time=None):
    service = authenticate("GoogleCalendar")
    now = datetime.utcnow().isoformat() + 'Z'
    end = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
    events = service.events().list(calendarId='primary', timeMin=now, timeMax=end, q=event_title, singleEvents=True).execute().get('items', [])
    if not events:
        return f"⚠️ No event found with title '{event_title}'."
    for e in events:
        event_start = e['start'].get('dateTime', e['start'].get('date'))
        if not start_time or event_start.startswith(start_time[:10]):
            service.events().delete(calendarId='primary', eventId=e['id']).execute()
            return f"❌ Event '{event_title}' on {event_start} canceled."
    return f"⚠️ No exact match found for '{event_title}' on '{start_time}'."

########################################################################
# Modify calendar event
########################################################################
def modify_calendar_event(event_title, new_title=None, new_start=None, new_end=None, new_description=None, new_location=None):
    service = authenticate("GoogleCalendar")
    now = datetime.utcnow().isoformat() + 'Z'
    end = (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z'
    events = service.events().list(calendarId='primary', timeMin=now, timeMax=end, q=event_title, singleEvents=True).execute().get('items', [])
    if not events:
        return f"⚠️ No event found for '{event_title}'."
    event = events[0]
    if new_title: event['summary'] = new_title
    if new_start: event['start']['dateTime'] = new_start
    if new_end: event['end']['dateTime'] = new_end
    if new_description: event['description'] = new_description
    if new_location: event['location'] = new_location
    service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
    return f"🔁 Event '{event_title}' updated."

########################################################################
# respond to event function
########################################################################
def respond_to_event(event_title, response):
    service = authenticate("GoogleCalendar")
    now = datetime.utcnow().isoformat() + "Z"
    future = (datetime.utcnow() + timedelta(days=90)).isoformat() + "Z"
    events = service.events().list(calendarId='primary', timeMin=now, timeMax=future).execute().get('items', [])
    for event in events:
        if event_title.lower() in event.get("summary", "").lower():
            if "attendees" not in event: return "⚠️ No attendees to respond to."
            for attendee in event["attendees"]:
                if attendee.get("self", False):
                    attendee["responseStatus"] = response
                    break
            service.events().patch(calendarId='primary', eventId=event["id"], body={"attendees": event["attendees"]}).execute()
            return f"✅ Responded '{response}' to '{event['summary']}'"
    return f"⚠️ Event '{event_title}' not found."

########################################################################
# ----------------------- Chat + Feedback + Tools -----------------------
########################################################################
def handle_event_result(function_name, args):
    result = globals()[function_name](**args)
    calendar_text = get_calendar_events()
    title = args.get('title') or args.get('event_title', 'Untitled')
    start_time = args.get('start_time') or args.get('new_start', '')
    verified = verify_event_in_calendar(title, start_time, calendar_text)
    result += "\n✅ Verified on calendar." if verified else "\n⚠️ Could not verify calendar change."
    log_feedback(function_name, "verified" if verified else "not_verified", context=str(args))
    result += "\n\nDid that work as expected? (yes / no / suggestion)"
    return result, function_name, str(args)

########################################################################
# Chat function
########################################################################
def chat(message, history, feedback_state):
    if feedback_state["awaiting"]:
        log_feedback(
            action=feedback_state["last_action"],
            result="user_feedback",
            user_input=message,
            context=feedback_state["context"]
        )
        feedback_state["awaiting"] = False
        # return [["Thanks for your feedback! 😊", ""]], feedback_state
        # Append feedback message properly
        history.append([message, "Thanks for your feedback! 😊"])
        return history, feedback_state        

    now = datetime.now()
    if auto_refresh_enabled["status"] and (last_refresh_time["timestamp"] is None or (now - last_refresh_time["timestamp"]) > timedelta(minutes=10)):
        refresh_system_message()

    formatted_time = now.strftime("%A, %B %d, %Y (%Y-%m-%dT%H:%M:%S%z)")
    openai_messages = [
        {"role": "system", "content": current_system_message["content"]},
        {"role": "system", "content": f"The current date and time is {formatted_time}."}
    ]

    for pair in history:
        user, assistant = pair
        openai_messages.append({"role": "user", "content": user})
        openai_messages.append({"role": "assistant", "content": assistant})

    openai_messages.append({"role": "user", "content": message})

    tools = [
        {
            "type": "function",
            "function": {
                "name": "create_calendar_event",
                "description": "Create a new calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "description": "Start time in ISO format"},
                        "end_time": {"type": "string", "description": "End time in ISO format"},
                        "description": {"type": "string"},
                        "location": {"type": "string"},
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of names or emails"
                        }
                    },
                    "required": ["title", "start_time", "end_time"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_calendar_event",
                "description": "Cancel an existing calendar event by title and optional date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_title": {"type": "string"},
                        "start_time": {"type": "string"}
                    },
                    "required": ["event_title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "modify_calendar_event",
                "description": "Modify an existing event's title, time, description or location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_title": {"type": "string"},
                        "new_title": {"type": "string"},
                        "new_start": {"type": "string"},
                        "new_end": {"type": "string"},
                        "new_description": {"type": "string"},
                        "new_location": {"type": "string"}
                    },
                    "required": ["event_title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "respond_to_event",
                "description": "Accept or reject an invitation to a calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_title": {"type": "string"},
                        "response": {
                            "type": "string",
                            "enum": ["accepted", "rejected"]
                        }
                    },
                    "required": ["event_title", "response"]
                }
            }
        }
    ]

    response = openai.chat.completions.create(
        model=MODEL,
        messages=openai_messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    # Handle function calls
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            fn = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result, last_action, context = handle_event_result(fn, args)
            feedback_state.update({
                "awaiting": True,
                "last_action": last_action,
                "context": context
            })
            history.append([message, result])
            return history, feedback_state

    # Fallback streaming or plain message
    response_text = response_message.content or "🤖 (No response)"
    # return history + [[message, response_text]], feedback_state

    # ✅ Proper format: append [user_msg, assistant_msg]
    history.append([message, response_text])
    return history, feedback_state

########################################################################
# ----------------------- Gradio Button Handlers -----------------------
########################################################################
def handle_feedback(feedback_choice, feedback_state, history):
    if history is None:
        history = []
    
    if feedback_state["awaiting"]:
        log_feedback(
            action=feedback_state["last_action"],
            result="user_feedback",
            user_input=feedback_choice,
            context=feedback_state["context"]
        )
        feedback_state["awaiting"] = False

        # ✅ Append system response in Gradio-compatible format
        history.append(["", "Thanks for your feedback! 😊"])
        return history, feedback_state, gr.update(visible=False)

    return history, feedback_state, gr.update(visible=False)

def handle_refresh(history):
    refresh_system_message()
    history.append(["", "✅ Calendar successfully refreshed."])
    return history

def handle_send(message, history):
    response = f"You said: {message}"
    history.append([message, response])
    return history, ""  # "" clears the textbox

def stop_chatbot(history):
    def delayed_exit():
        import time
        time.sleep(1)
        os._exit(0)
    import threading
    threading.Thread(target=delayed_exit).start()
    history.append(["", "🛑 Shutting down. See you next time!"])
    return history
