from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def main():
    return "Bot is running!"

def run():
    # port 8080 is standard for Replit/web runners
    app.run(host="0.0.0.0", port=8080)

# This function name MUST match the import in main.py
def keep_alive():
    server = Thread(target=run)
    server.start()
