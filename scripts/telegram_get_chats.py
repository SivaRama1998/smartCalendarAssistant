################################################################################################
#Thsi script is used to connect to telegram and fetch the chats happened in last 24 hours.
################################################################################################
#    Version          Date              Description                            Author
#   ---------       ---------    ----------------------------------     -----------------------
#      0.1          27/03/2025        Initial version                        BASS TEAM
################################################################################################

import os
from telethon import TelegramClient
from datetime import datetime, timedelta
from telethon.tl.types import User,Channel,Chat,MessageService,MessageMediaPhoto
from telethon.sessions import StringSession
import asyncio
from dotenv import load_dotenv
from telegram_otp_auth import start_auth_flow
import subprocess


# Load environment variables
load_dotenv(override=True)

# Telegram API Credentials (Replace with your own)
api_id=int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH_KEY")
SESSION_FILE=os.getenv("SESSION_FILE")
#phone_number = os.getenv("TELEGRAM_NUMBER")

output_file=os.getenv("OUTPUT_FILE_NAME")
image_file_path=os.getenv("IMAGE_DOWNLOAD_PATH")


###############################################################
#fetch_required_messages
###############################################################
async def fetch_required_messages(client, after_ts, before_ts):

    # convert epoch time to datetime object
    local_tz = datetime.now().astimezone().tzinfo
    after_ts = datetime.fromtimestamp(after_ts, tz=local_tz)
    before_ts = datetime.fromtimestamp(before_ts, tz=local_tz)

    me = await client.get_me()

    self_name = me.first_name or me.last_name or me.username or "Unknown"
    # Fetch all chat dialogs
    dialogs = await client.get_dialogs()

    print(datetime.now(),"No of Telegram messages:", len(dialogs))
    print(datetime.now()," - Fetch all chat dialogs - Done")
    
    chat_str=""

    for dialog in dialogs:
        if not dialog.name:  # Skip dialogs without a name
            continue
        #End if

        #Ignoring telegram automated messages.
        if dialog.name=='Telegram':
            continue
        #End If

        #Checking if dialog has any messages and not processing them
        messages = await client.get_messages(dialog.id, limit=1)
        if not messages or isinstance(messages[0], MessageService):
            continue
        #End if

        print(messages[0].date)
        chat_ts = messages[0].date
        print(f"Chat time: {chat_ts}")

        # chat_date=datetime.strptime(str(messages[0].date.date()

        if chat_ts < after_ts:
            continue
        #End if

        # Fetch messages from the chat in the last 24 hours
        messages = await client.get_messages(dialog.id, limit=9999)  # Adjust limit as needed

        sorted_messages = sorted(messages, key=lambda msg: msg.date)
        #print(datetime.now()," - Sorted ",dialog.name ,"Messages - Done")

        for msg in sorted_messages:

            print("MSG:",msg.id," - ",msg.date," - ",msg.text)
            chat_ts=msg.date
            if chat_ts and chat_ts >= after_ts and chat_ts <= before_ts:

                #fetching sender details
                sender = await msg.get_sender()

                if isinstance(sender, User) and  sender.is_self:
                    sender_name = self_name
                elif isinstance(sender, User) and not sender.is_self:
                    sender_name = sender.first_name or sender.last_name or sender.username or "Unknown"
                elif isinstance(sender, (Channel, Chat)):  # If sender is a Channel or Group Chat
                    sender_name = dialog.name  # Use the group/channel name
                else:
                    sender_name = 'Unknown'
                #End if

                #Check if the msg is of media type and fetch the media details
                if msg.media and isinstance(msg.media, MessageMediaPhoto):
                    # Check if the message has an image
                    if msg.photo:
                        print(f"Downloading image from message {msg.id}...")
                        # Download the image
                        file_path = await client.download_media(msg, file=f"{image_file_path}/{sender_name}_image_{msg.id}.jpg")
                        print(f"Image saved at: {file_path}")
                    #End if
                #End If

                #Loading data into the file
                chat_str = chat_str + f"""
                    Chat with: {dialog.name}\n 
                    Message Type : {'sent' if msg.out else 'Received'}\n 
                    Sender : {sender_name}\n 
                    Message : {msg.text if msg.text else '[Media/Sticker]'}\n 
                    Time : {msg.date.strftime('%Y-%m-%d %I:%M:%S %p %Z')} \n
                """

                #Add media details
                chat_str += file_path if msg.media and isinstance(msg.media, MessageMediaPhoto) else ""
                #if images
            #End if
        #End for
    #End for
    await client.disconnect()

    return chat_str
    # with open(output_file, "w", encoding="utf-8") as file:
    #     file.write(chat_str)
    # #End With

##############################################################################
#Main
##############################################################################
async def telegram_get_chats(after_ts, before_ts):
    session_string = None

    if os.path.exists(SESSION_FILE):
        print("Session file exists. Loading session...")
        with open(SESSION_FILE, 'r') as session_file:
            session_string = session_file.read()
    
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print("Session is invalid or expired. Starting auth flow...")
        await client.disconnect()  # Clean up before launching UI

        # 🔁 Run auth flow in a subprocess (avoids event loop conflict)
        subprocess.run(["python", "telegram_invoke_auth.py"], check=True)

        return await telegram_get_chats(after_ts, before_ts)

    return await fetch_required_messages(client, after_ts, before_ts)
