from flask import Flask, request
from telegram import Update
from Codro import CodroBot
import os

app = Flask(__name__)
bot = CodroBot()

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running!'

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(), bot.application.bot)
        await bot.application.update_queue.put(update)
        return 'OK'

if __name__ == '__main__':
    # Set webhook URL
    WEBHOOK_URL = 'https://test-bot.up.railway.app/webhook'
    PORT = int(os.environ.get('PORT', 5000))
    
    # Set the webhook
    bot.application.bot.set_webhook(WEBHOOK_URL)
    
    # Start Flask app
    app.run(host='0.0.0.0', port=PORT)
