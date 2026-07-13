import os
import logging
from flask import Flask, Response
from threading import Thread

# Initialize Flask app with a clean naming context
app = Flask('LobbyBotKeepAlive')

# This stops Flask from outputting a line for every single cron-job request it handles,
# which prevents Render's log buffer and your cron terminal from blowing up.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    # Returns HTTP 204 No Content (exactly 0 bytes)
    # This completely eliminates "output too large" errors from web-cron pingers.
    return Response(status=204)

def run():
    port = int(os.getenv('PORT', 8080))
    # Run the server in production-ready silent mode
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    """Starts the Flask server in a background thread."""
    t = Thread(target=run)
    t.daemon = True
    t.start()
