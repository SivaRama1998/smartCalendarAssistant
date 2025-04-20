from quart import Quart, request, redirect, url_for, render_template_string
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv
import webbrowser
import threading
import asyncio
import signal
import time
import asyncio
import threading
from hypercorn.asyncio import serve
from hypercorn.config import Config
from datetime import datetime

load_dotenv()
app = Quart(__name__)

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH_KEY")
SESSION_FILE=os.getenv("SESSION_FILE")

sessions = {}

############################################################
#login
############################################################
@app.route("/", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        form = await request.form
        phone = form["phone"]

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)
        sessions[phone] = client

        return redirect(url_for("verify", phone=phone))

    return '''
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; background: #f2f2f2; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .container { background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                input[type="text"], input[type="submit"] {
                    padding: 10px;
                    margin-top: 10px;
                    width: 100%;
                    border-radius: 5px;
                    border: 1px solid #ccc;
                    font-size: 1rem;
                }
                input[type="submit"] {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    cursor: pointer;
                }
                input[type="submit"]:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Login with Telegram</h2>
                <form method="post">
                    <label>Phone (+91**********):</label><br>
                    <input type="text" name="phone" placeholder="+91XXXXXXXXXX" required>
                    <input type="submit" value="Send OTP">
                </form>
            </div>
        </body>
        </html>
    '''

@app.route("/verify/<phone>", methods=["GET", "POST"])
async def verify(phone):
    print("Starting OTP verification for phone:", phone)
    if request.method == "POST":
        form = await request.form
        code = form["otp"]

        client = sessions.get(phone)
        if client:
            try:
                await client.sign_in(phone, code)

                # Save session string to file
                session_string = client.session.save()
                print("OTP verification successful:")
                with open(SESSION_FILE, "w") as f:
                    f.write(session_string)

                # shutdown_app()
                return "✅ Logged in successfully! Session saved to file. You can close this window."
            except Exception as e:
                return f"❌ OTP incorrect or expired. Error: {e}"
    return f'''
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f2f2f2; display: flex; justify-content: center; align-items: center; height: 100vh; }}
                .container {{ background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                input[type="text"], input[type="submit"] {{
                    padding: 10px;
                    margin-top: 10px;
                    width: 100%;
                    border-radius: 5px;
                    border: 1px solid #ccc;
                    font-size: 1rem;
                }}
                input[type="submit"] {{
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    cursor: pointer;
                }}
                input[type="submit"]:hover {{
                    background-color: #0b7dda;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Verify OTP for {phone}</h2>
                <form method="post">
                    <label>Enter OTP:</label><br>
                    <input type="text" name="otp" placeholder="123456" required>
                    <input type="submit" value="Verify OTP">
                </form>
            </div>
        </body>
        </html>
    '''

##################################################################
# Shutdown function
##################################################################
async def shutdown_app(shutdown_event):
    await asyncio.sleep(60)
    print(datetime.now().timestamp(),"Shutting down after 60 seconds...")
    shutdown_event.set()

##################################################################
# Auth flow function
##################################################################
def start_auth_flow():
    shutdown_event = asyncio.Event()

    config = Config()
    config.bind = ["127.0.0.1:5000"]
    config.use_reloader = False
    config.use_signal_handlers = False  # ⛔ prevent signal setup
    #If the session file already exists, this will overwrite it.
    def open_browser():
        asyncio.run(async_browser())

    async def async_browser():
        await asyncio.sleep(1)
        asyncio.create_task(shutdown_app(shutdown_event))
        webbrowser.open("http://127.0.0.1:5000")

        #When shutdown_event.set() is called elsewhere in the code, it signals the server to stop
        await serve(app, config, shutdown_trigger=shutdown_event.wait)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(open_browser())
    except Exception as e:
        print("Exception:", e)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        print("Event loop closed.")

def caller_start_auth_flow():
    t = threading.Thread(target=start_auth_flow)
    t.start()
    t.join()

