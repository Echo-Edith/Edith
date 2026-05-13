from flask import Flask
from threading import Thread
import logging

# Disable extra logging to keep the console clean for bot logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    # This is the "Health Check" Render looks for
    return "E.D.I.T.H. Mainframe Status: OPERATIONAL"

def run():
    # Render requires 0.0.0.0 and usually port 8080 or 10000
    try:
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"⚠️ Web Server Error: {e}")

def keep_alive():
    """Starts the Flask server in a separate thread so it doesn't block the bot."""
    t = Thread(target=run)
    t.daemon = True # Ensures the thread dies if the main bot process stops
    t.start()
    print("🌐 Web Server Thread Initialized: Listening on Port 8080")
