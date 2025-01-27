from bot_config import *
import re

class Utils:
    def __init__(self, bot_config, bot_messages):
        self.BOT_CONFIG = bot_config
        self.DEFAULT_BOT_MESSAGES = bot_messages
    
    def format_message(self, message_template, **kwargs):
        """Format message with configuration values"""
        try:
            if isinstance(self.BOT_CONFIG, dict):
                course_info = self.BOT_CONFIG.get("DEFAULT_BOT_CONFIG", {}).get("course_info", {})
            else:
                course_info = self.BOT_CONFIG.DEFAULT_BOT_CONFIG.get("course_info", {})
            
            # Format the message first
            formatted_msg = message_template.format(**{**course_info, **kwargs})
            
            # Clean any invalid HTML tags
            cleaned_msg = self.clean_html(formatted_msg)
            return cleaned_msg
            
        except Exception as e:
            # إذا حدث خطأ، نرجع الرسالة كما هي
            return message_template

    def clean_html(self, text):
        """Clean invalid HTML tags while preserving valid ones"""
        # First, explicitly remove br tags
        unsupported_tags = ['br', 'center', 'u', 'font', 'sup', 'sub', 'p', 'li', 'ul', 'ol']

        for element in unsupported_tags:
            text = text.replace(f'<{element}>', '').replace(f'</{element}>', '')

        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
        # تغيير تنسيق النقاط إلى نجمة مع مراعاة المسافات في البداية
        text = re.sub(r"^(\s*)\* (.*?)$", r"\1• \2", text, flags=re.MULTILINE)

        return text

    def clear_html(self, text):
        """Remove all HTML tags from text"""
        return re.sub(r'<[^>]+>', '', text)

    def get_message(self, message_key):
        """Get a system message from the database"""
        return self.DEFAULT_BOT_MESSAGES['system_messages'].get(message_key, "Message not found")
