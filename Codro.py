import asyncio
import time
import random
import os
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from bot_config import *
from bot_default_defs import replys
from utils import Utils
from quiz_handler import QuizHandler
from db_handler import DatabaseHandler
from assignment_handler import AssignmentHandler

# Environment variables
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://test-bot.up.railway.app')
PORT = int(os.getenv('PORT', 8443))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')  # تغيير القيمة الافتراضية إلى production
SECRET_TOKEN = os.getenv('SECRET_TOKEN', 'a8b9c33eb985d69287fa975afacc4ad4d35070c5ccc11dfa925da279e55f2d3e')

class CodroBot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # Configuration and database structure
        self.bot_config = Data().DEFAULT_BOT_CONFIG
        self.bot_messages = Data().DEFAULT_BOT_MESSAGES

        # Initialize database handlers
        self.db_handler = DatabaseHandler()

        # Create instances
        self.utils = Utils(self.bot_config['system_prompt'], self.bot_messages)
        self.bot_replys = replys(
            self.bot_config['system_prompt'], 
            self.bot_messages, 
            self.utils.format_message, 
            self.utils.get_message,
            self.db_handler
        )
        self.quiz_handler = QuizHandler(
            self.bot_config['system_prompt'], 
            self.bot_messages, 
            self.utils.format_message, 
            self.utils.get_message,
        )
        self.assignment_handler = AssignmentHandler(
            self.bot_config['system_prompt'],
            self.bot_messages,
            self.utils.format_message,
            self.utils.get_message,
            self.db_handler
        )

        # State variables
        self.chat_history = []
        self.user_id = None

        # Initialize application
        self.token = '7820673343:AAE3ISuGzoS_xVKdYo7ZSnXtRYtV3wsOep8'
        self.application = Application.builder().token(self.token).connect_timeout(60.0).read_timeout(60.0).build()
        self._setup_handlers()
        self._initialized = True

    async def gemini_response(self, message_t, system_prompt=None):
        if not self.user_id:
            print("خطأ: user_id غير محدد")
            return "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى."
            
        # استرجاع سجل المحادثة من قاعدة البيانات
        self.chat_history = await self.db_handler.get_chat_history(int(self.user_id))

        try:
            # Configure Gemini API
            genai.configure(api_key=get_gemini_api())
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                generation_config={
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                    "response_mime_type": "text/plain",
                },
                system_instruction=system_prompt
            )

            chat = model.start_chat(history=self.chat_history)
            response = chat.send_message(message_t)
            
            # تنظيف الرد من HTML tags غير صالحة
            cleaned_response = self.utils.clean_html(response.text)

            # تحديث سجل المحادثة وحفظه في قاعدة البيانات
            new_messages = [
                {"role": "user", "parts": [message_t]},
                {"role": "model", "parts": [cleaned_response]}
            ]
            self.chat_history.extend(new_messages)
            await self.db_handler.save_chat_history(int(self.user_id), self.chat_history)
            
            print(cleaned_response)
            return cleaned_response
        except Exception as e:
            print(f"Error in chat session: {str(e)}")
            return "عذراً، حدث خطأ في المحادثة. يرجى المحاولة مرة أخرى."

    def _setup_handlers(self):
        """إعداد معالجات الأوامر والرسائل"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("info", self.bot_replys.info))
        self.application.add_handler(CommandHandler("quiz", self.quiz_handler.start_quiz))
        self.application.add_handler(CommandHandler("ask", self.bot_replys.ask))
        self.application.add_handler(CommandHandler("courses", self.bot_replys.courses))
        self.application.add_handler(CommandHandler("schedule", self.bot_replys.schedule))
        self.application.add_handler(CommandHandler("contact", self.bot_replys.contact))
        self.application.add_handler(CommandHandler("assignment", self.assignment_handler.start_assignment))
        
        # Add handlers for callbacks
        self.application.add_handler(CallbackQueryHandler(self.quiz_handler.handle_callback, pattern="^(course_|count_|lesson_|finish_)"))
        self.application.add_handler(CallbackQueryHandler(self.quiz_handler.handle_button_callback, pattern="^ans_"))
        self.application.add_handler(CallbackQueryHandler(self.assignment_handler.handle_callback, pattern="^assign_"))
        self.application.add_handler(CallbackQueryHandler(self.bot_replys.button_callback, pattern="^python_"))  
        
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = self.utils.get_message('start')
        await update.message.reply_text(welcome_message, parse_mode="HTML")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        if update.message is None:
            return

        message = update.message.text
        self.user_id = update.message.chat_id

        print(f"تم استلام الرسالة من المستخدم: {self.user_id}")

        # إرسال رسالة التحميل
        loading_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏳",
            parse_mode="HTML"
        )

        try:
            # الحصول على الرد من جيميني
            response = await self.gemini_response(message_t=message, system_prompt=self.bot_config['system_prompt'])
            print(f"تم الحصول على الرد من جيميني: {response}")

            # تحديث رسالة التحميل بالرد
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=loading_message.message_id,
                    text=response,
                    parse_mode="HTML"
                )
            except Exception as format_error:
                # إذا فشل التنسيق، نرسل الرسالة بدون أي علامات HTML
                print(f"فشل التنسيق: {format_error}")
                clean_text = self.utils.clear_html(response)
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=loading_message.message_id,
                    text=clean_text,
                    parse_mode=None
                )
        except Exception as e:
            print(f"حدث خطأ: {e}")
            error_message = "عذراً، حدث خطأ أثناء معالجة طلبك. الرجاء المحاولة مرة أخرى."
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=loading_message.message_id,
                text=error_message
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == '1':
            await query.message.reply_text("تم اختيار كورس Python Basics! سيتم التواصل معك قريباً.", parse_mode="HTML")

    def run(self):
        """Start the bot with webhook or polling based on environment"""
        if ENVIRONMENT == 'production':
            print(f"Starting bot in production mode with webhook URL: {WEBHOOK_URL}")
            self.application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=f"{WEBHOOK_URL}/{self.token}",
                secret_token=SECRET_TOKEN
            )
        else:
            print("Starting bot in development mode with polling")
            self.application.run_polling(drop_pending_updates=True)  # إضافة drop_pending_updates

# Create bot instance
bot = CodroBot()

if __name__ == '__main__':
    try:
        print("Starting the bot...")
        if ENVIRONMENT == 'production':
            # Set up the webhook
            print(f"Setting webhook to {WEBHOOK_URL}")
            bot.application.run_webhook(
                listen="0.0.0.0",
                port=int(PORT),
                secret_token=SECRET_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{bot.token}"
            )
        else:
            # Run in development mode with polling
            print("Running in development mode with polling")
            print("Bot token:", bot.token)
            print("Initializing application...")
            asyncio.run(bot.application.run_polling(drop_pending_updates=True))
    except Exception as e:
        print(f"Error starting bot: {str(e)}")
        raise e