import os
import threading
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "The lobby is open. Grab a drink and don't blow into your mic! 🎙️"

def run_web_server():
    # Render automatically assigns a port value to the PORT variable dynamically
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Spins up a lightweight background web thread to handle external ping pokes."""
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()
