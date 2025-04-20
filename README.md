
# SmartSched

Introducing our state-of-the-art scheduling app, SmartSched—your intelligent assistant that operates behind the scenes to streamline your life. Harnessing the power of AI, this app seamlessly integrates with your Gmail and Telegram chats, expertly scanning for upcoming appointments and effortlessly booking them directly into your Google Calendar—all without you lifting a finger.

But there's more. Our app features an AI-driven interactive Chat Assistant that can summarize your upcoming events, create, modify, or cancel appointments, and ensure your calendar is always organized and up-to-date in real time. It's the perfect companion for busy professionals eager to maintain control over their schedules with ease.

## Key Features

1. **AI-Driven Automatic Appointment Detection:**
   - Our app utilizes AI to intelligently read your Gmail and Telegram accounts, pinpointing any time-sensitive information and seamlessly logging it into your calendar.

2. **AI-Enabled Seamless Background Processing:**
   - The app quietly operates in the background, using AI to periodically gather details and automatically schedule appointments in your Google Calendar at configurable intervals.

3. **AI-Powered Personal Assistant:**
   - Engage with a smart chat bot that responds to queries about your Google Calendar events and handles tasks such as:
     - Creating new events
     - Modifying existing ones
     - Cancelling appointments
     - Accepting or declining meeting invites

4. **Real-Time Calendar Updates:**
   - Enjoy peace of mind as the bot checks for the latest calendar events every 10 minutes. For urgent updates, simply prompt the bot to instantly refresh your schedule.

5. **Continuous Learning and Improvement:**
   - Provide feedback on every action, empowering the bot to refine its performance using AI and deliver continually enhanced service.

6. **User Control and Flexibility:**
   - Gain the power to stop the Chat Bot at any time, giving you complete control over your scheduling needs.

Our AI-driven app is the ultimate solution for professionals who value their time and desire a streamlined, hands-free scheduling experience. Embrace the future of time management and let our app take care of your scheduling so you can focus on what truly matters.


# SmartSched: Deployment and Setup Instructions

## Overview

SmartSched is an AI-driven app that helps automate scheduling tasks by integrating with Gmail, Google Calendar, and Telegram. This document provides step-by-step instructions for deploying and setting up the application.

## Deployment Instructions

### 1. Create a Project Folder

- Create a folder named `SmartSched` in a location of your choice.

### 2. Download the App Code

- Fetch the app code from the Git repository and place it in the `SmartSched` folder.
- Your folder structure should look like this:

```plaintext
SmartSched/
├── .env
├── .gitignore
├── README.md
├── attachments/
├── daemon/
├── logs/
├── scripts/
├── secrets/
└── sessions/
```

### 3. Install Required Python Packages

- Open a command prompt and run the following command to install all necessary packages:
```bash
pip install python-dotenv openai google-api-python-client google-auth google-auth-oauthlib gradio asyncio python-daemon
```
## Initial Setup

### Google Gmail and Calendar API

#### 1. Set Up a Google Cloud Project

- Visit the [Google Cloud Console](https://console.cloud.google.com/).
- Create a new project or select an existing one.
- Navigate to `APIs & Services > Library`.
- Enable the following APIs:
  - Google Calendar API
  - Gmail API

#### 2. Create OAuth Credentials

- Go to `APIs & Services > Credentials`.
- Configure the consent screen with the following details:
  - Provide an app name and support email.
  - Select "External" for the audience.
  - Enter your email in the contact information.
  - Agree to the terms and conditions and click "Create".
- Create credentials by choosing either:
  - OAuth client ID for user data access (recommended).
  - API Key for public data access (not recommended for sensitive operations).
- Choose "Desktop App" and name your app, then click "Create".
- Download the credentials JSON file, rename it to `credentials.json`, and save it in the `<project_base_folder>/secrets` directory.

#### 3. Add Test Gmail User

- Navigate to Google Auth Platform > Audience.
- Scroll to "Test users" and add the Gmail ID used by SmartSched.

#### 4. Add API Scopes

- Navigate to Google Auth Platform > Data access.
- Click "Add or Remove scopes" and manually add the following scopes:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/calendar.events`

### Telegram API

#### 1. Register Your Telegram Application

- Visit [Telegram’s API Development Page](https://my.telegram.org).
- Log in using your Telegram phone number.
- Click "API Development Tools" and fill out the form:
  - App title and short name.
  - URL (use https://example.com if not applicable).
  - Platform (e.g., Desktop).
- Click "Create application".

#### 2. Retrieve API ID and Hash

- After creating the application, save the `api_id` and `api_hash` securely for your `.env` file.

### Telegram BOT API

#### 1. Create a Bot with Bot Father

- Open Telegram and search for @botfather.
- Start a conversation and enter `/newbot`.
- Set up your bot's name and username (ending with "_bot").
- Save the HTTP API key provided for your `.env` file.

## SmartSched App Setup

### Configure the .env File

- Set `BASE_DIR` to your SmartSched folder's full path.
- Replace placeholders with your keys and IDs:
```ini
BASE_DIR = /full/path/to/SmartSched
OPENAI_API_KEY = your-api-key
LLM_MODEL = gpt-4o
TELEGRAM_API_HASH_KEY = your-telegram-api-key
TELEGRAM_API_ID = your-telegram-api-id
TELEGRAM_BOT_KEY = your-telegram-bot-key
INCLUDE_GMAIL = True
INCLUDE_TELEGRAM = True
```

## Running the App

### Start the Background Process

- Navigate to the `scripts` folder in the command prompt.
- Run the command:
```bash
python daemon_google_calendar_event_creater.py start
```

- Commands:
  - `start` - to start the process
  - `stop` - to stop the process
  - `restart` - to restart the process

### Launch the Smart Chat Bot

- In the `scripts` folder, run:
```bash
python ai_agent_assistant_app.py
```

- This will open the chat bot app in your browser.

## Technical Notes

- **Scripts**: Contains Python scripts for the application.
- **Secrets**: Stores the `credentials.json` file.
- **Sessions**: Stores session files for Telegram and Google.
- **Logs**: Contains log files for both the daemon and bot processes.
- **Daemon**: Contains files for the background process.
- **Python Version**: Developed and tested in Python 3.11.11.

---

Please ensure to replace placeholders with actual values specific to your setup. This README serves as a comprehensive guide to deploy and run the SmartSched application.

