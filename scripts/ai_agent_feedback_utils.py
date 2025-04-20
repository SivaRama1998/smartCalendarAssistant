import json
from datetime import datetime

FEEDBACK_LOG = "feedback_log.jsonl"

def verify_event_in_calendar(event_title, start_time, calendar_text):
    return event_title.lower() in calendar_text.lower() and start_time[:10] in calendar_text

def log_feedback(action, result, user_input=None, context=""):
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "result": result,
        "user_feedback": user_input,
        "context": context
    }
    with open(FEEDBACK_LOG, "a") as f:
        f.write(json.dumps(feedback_entry) + "\n")

def summarize_feedback_log():
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    try:
        with open(FEEDBACK_LOG) as f:
            for line in f:
                entry = json.loads(line)
                fb = entry.get("user_feedback")
                if isinstance(fb, str):
                    fb = fb.lower()
                else:
                    fb = ""

                if fb in ["yes", "y", "ok", "sure", "yep", "👍 yes"]:
                    counts["positive"] += 1
                elif fb in ["no", "nah", "nope", "👎 no"]:
                    counts["negative"] += 1
                elif fb:
                    counts["neutral"] += 1  # anything else, including suggestions
    except FileNotFoundError:
        pass
    return counts
