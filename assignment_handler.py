import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import asyncio
import logging
import google.generativeai as genai
from bot_config import Data
from utils import Utils

class AssignmentHandler:
    def __init__(self, bot_config, bot_messages, format_message_func, get_message_func, db_handler=None):
        self.bot_config = Data().DEFAULT_BOT_CONFIG
        self.DEFAULT_BOT_MESSAGES = bot_messages
        self.format_message = format_message_func
        self.get_message = get_message_func
        self.db_handler = db_handler
        self.current_assignments = {}
        self.utils = Utils(bot_config, bot_messages)
        self.lesson_ids = {}  # قاموس لتخزين معرفات الدروس

        # تهيئة Gemini
        genai.configure(api_key="AIzaSyAAhhHq792UUWT-e_6Ft0uYpkcBJ6FK5bs")
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-thinking-exp-01-21",
            generation_config={
                "temperature": 0.9,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
        )
        
        # تعريف كورس Python فقط
        self.courses = {
            'python': 'Python البرمجة بلغة'
        }
        
        self.difficulties = ['سهل', 'متوسط', 'صعب']

    def shorten_lesson_title(self, title):
        """اختصار عنوان الدرس للأزرار"""
        # قاموس الاختصارات
        shortcuts = {
            "مقدمة إلى بايثون وإعداد البيئة": "مقدمة بايثون",
            "المتغيرات وأنواع البيانات": "المتغيرات",
            "الجمل الشرطية والمنطقية": "الجمل الشرطية",
            "الحلقات التكرارية": "الحلقات",
            "القوائم والعمليات عليها": "القوائم",
            "الدوال وتمريرها": "الدوال",
            "التعامل مع الملفات": "الملفات",
            "القواميس والمجموعات": "القواميس",
            "معالجة الأخطاء": "الأخطاء",
            "البرمجة كائنية التوجه": "OOP"
        }
        return shortcuts.get(title, title)

    def get_lesson_id(self, title):
        """الحصول على معرف الدرس من العنوان"""
        if title not in self.lesson_ids:
            self.lesson_ids[title] = str(len(self.lesson_ids) + 1)
        return self.lesson_ids[title]

    def get_lesson_title(self, lesson_id):
        """الحصول على عنوان الدرس من المعرف"""
        for title, id_ in self.lesson_ids.items():
            if id_ == lesson_id:
                return title
        return None

    async def start_assignment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start assignment creation using inline keyboards"""
        keyboard = []
        for course_id, course_name in self.courses.items():
            keyboard.append([InlineKeyboardButton(course_name, callback_data=f"assign_course_{course_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👨‍🏫 اختر الكورس الذي تريد الحصول على واجب فيه:",
            reply_markup=reply_markup
        )

    async def generate_assignment(self, course, difficulty, lessons, user_id=None):
        """توليد واجب باستخدام Gemini"""
        self.user_id = user_id  # حفظ user_id
        # الحصول على وصف الدروس المختارة
        lessons_info = {}
        course_info = self.bot_config.get("course_info", {})
        if "lessons" in course_info:
            for lesson_key, lesson_data in course_info["lessons"].items():
                if lesson_data["title"] in lessons:
                    lessons_info[lesson_data["title"]] = lesson_data["description"].strip()

        # تجهيز الprompt مع معلومات الدروس
        prompt = f"""
قم بإنشاء واجب برمجي قصير ومركز باللغة العربية يغطي الدروس التالية:

الدروس المختارة:
{', '.join(lessons)}

محتوى الدروس:
{chr(10).join([f'• {title}:\n{desc}' for title, desc in lessons_info.items()])}

قيود مهمة:
- مستوى الصعوبة: {difficulty}
- استخدم فقط المفاهيم التي تم شرحها في محتوى الدروس أعلاه
- اجعل الواجب عملياً ومفيداً
- قم بتنسيق الرد باستخدام HTML الخاص بتليجرام البسيط فقط:
  * استخدم <b> للنص العريض
  * استخدم <code> للكود
  * لا تستخدم أي وسوم HTML أخرى

المطلوب:
1. ✍️ وصف سريع للمشروع (سطرين)
2. 📋 النقاط المطلوب تنفيذها (3-4 نقاط)
3. 💡 مثال بسيط للمخرجات المتوقعة

اجعل الرد مختصر ومباشر مع استخدام النقاط والإيموجي للتوضيح.
"""

        try:
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(prompt).text
            )
            
            # تنظيف وتنسيق HTML
            cleaned_response = self.utils.clean_html(response)
            
            # التأكد من أن النص يحتوي على وسوم HTML صحيحة فقط
            allowed_tags = ['<b>', '</b>', '<code>', '</code>', '<br>']
            for tag in allowed_tags:
                if tag not in cleaned_response:
                    # إضافة التنسيق الأساسي إذا لم يكن موجوداً
                    cleaned_response = cleaned_response.replace('✍️', '<b>✍️</b>')
                    cleaned_response = cleaned_response.replace('📋', '<b>📋</b>')
                    cleaned_response = cleaned_response.replace('💡', '<b>💡</b>')
                    break
            
            # حفظ الرد في سجل المحادثة
            if self.db_handler:
                chat_history = [
                    {"role": "user", "parts": [prompt]},
                    {"role": "model", "parts": [cleaned_response]}
                ]
                await self.db_handler.save_chat_history(int(self.user_id), chat_history)
            
            return cleaned_response
        except Exception as e:
            logging.error(f"Error generating assignment: {str(e)}")
            return None

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if user_id not in self.current_assignments:
            self.current_assignments[user_id] = {}
        
        try:
            await query.answer()
            
            if query.data.startswith('assign_course_'):
                course = query.data.replace('assign_course_', '')
                self.current_assignments[user_id]['course'] = course
                
                keyboard = []
                for diff in self.difficulties:
                    keyboard.append([InlineKeyboardButton(diff, callback_data=f"assign_diff_{diff}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📊 اختر مستوى صعوبة الواجب:",
                    reply_markup=reply_markup
                )
                
            elif query.data.startswith('assign_diff_'):
                difficulty = query.data.replace('assign_diff_', '')
                self.current_assignments[user_id]['difficulty'] = difficulty
                
                course = self.current_assignments[user_id]['course']
                keyboard = []
                row = []
                
                course_info = self.bot_config.get("course_info", {})
                if "lessons" in course_info:
                    lessons = []
                    for lesson_key, lesson_data in course_info["lessons"].items():
                        if lesson_data["title"] != "مقدمة إلى بايثون وإعداد البيئة":
                            short_title = self.shorten_lesson_title(lesson_data["title"])
                            lessons.append((short_title, lesson_data["title"]))
                    
                    for i, (short_title, full_title) in enumerate(lessons):
                        lesson_id = self.get_lesson_id(full_title)
                        row.append(InlineKeyboardButton(short_title, callback_data=f"assign_lesson_{lesson_id}"))
                        if len(row) == 2 or i == len(lessons) - 1:
                            keyboard.append(row)
                            row = []
                
                keyboard.append([InlineKeyboardButton("✅ تم الاختيار", callback_data='assign_lessons_done')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📚 اختر الدروس التي تريد الواجب فيها (يمكنك اختيار أكثر من درس):",
                    reply_markup=reply_markup
                )
                
            elif query.data.startswith('assign_lesson_'):
                lesson_id = query.data.replace('assign_lesson_', '')
                lesson_title = self.get_lesson_title(lesson_id)
                
                if 'selected_lessons' not in self.current_assignments[user_id]:
                    self.current_assignments[user_id]['selected_lessons'] = []
                
                # إضافة أو إزالة الدرس من القائمة
                if lesson_title:
                    if lesson_title in self.current_assignments[user_id]['selected_lessons']:
                        self.current_assignments[user_id]['selected_lessons'].remove(lesson_title)
                    else:
                        self.current_assignments[user_id]['selected_lessons'].append(lesson_title)
                
                course = self.current_assignments[user_id]['course']
                keyboard = []
                row = []
                
                course_info = self.bot_config.get("course_info", {})
                if "lessons" in course_info:
                    lessons = []
                    for lesson_key, lesson_data in course_info["lessons"].items():
                        if lesson_data["title"] != "مقدمة إلى بايثون وإعداد البيئة":
                            short_title = self.shorten_lesson_title(lesson_data["title"])
                            lessons.append((short_title, lesson_data["title"]))
                    
                    for i, (short_title, full_title) in enumerate(lessons):
                        lesson_id = self.get_lesson_id(full_title)
                        is_selected = full_title in self.current_assignments[user_id]['selected_lessons']
                        lesson_text = f"✅ {short_title}" if is_selected else short_title
                        row.append(InlineKeyboardButton(lesson_text, callback_data=f"assign_lesson_{lesson_id}"))
                        if len(row) == 2 or i == len(lessons) - 1:
                            keyboard.append(row)
                            row = []
                
                keyboard.append([InlineKeyboardButton("✅ تم الاختيار", callback_data='assign_lessons_done')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # تحديث الرسالة فقط إذا تغيرت القائمة
                message_text = "📚 اختر الدروس التي تريد الواجب فيها:\n"
                if self.current_assignments[user_id]['selected_lessons']:
                    selected_titles = [self.shorten_lesson_title(title) for title in self.current_assignments[user_id]['selected_lessons']]
                    message_text += f"\nالدروس المختارة: {', '.join(selected_titles)}"
                
                try:
                    await query.edit_message_text(
                        text=message_text,
                        reply_markup=reply_markup
                    )
                except telegram.error.BadRequest as e:
                    if "Message is not modified" not in str(e):
                        raise e
                
            elif query.data == 'assign_lessons_done':
                if 'selected_lessons' not in self.current_assignments[user_id] or \
                   not self.current_assignments[user_id]['selected_lessons']:
                    await query.answer("الرجاء اختيار درس واحد على الأقل!")
                    return

                state = self.current_assignments[user_id]
                
                await query.edit_message_text("⏳ جاري إنشاء الواجب... برجاء الانتظار")
                
                assignment_content = await self.generate_assignment(
                    self.courses[state['course']],
                    state['difficulty'],
                    state['selected_lessons'],
                    user_id=user_id
                )
                
                if assignment_content:
                    selected_titles = [self.shorten_lesson_title(title) for title in state['selected_lessons']]
                    assignment_text = f"""
📝 تفاصيل الواجب:
🎯 الكورس: {self.courses[state['course']]}
📊 المستوى: {state['difficulty']}
📚 الدروس المختارة: {', '.join(selected_titles)}

{assignment_content}"""
                else:
                    assignment_text = "⚠️ عذراً، حدث خطأ أثناء إنشاء الواجب. يرجى المحاولة مرة أخرى."

                try:
                    await query.edit_message_text(text=assignment_text, parse_mode='HTML')
                except telegram.error.BadRequest as e:
                    if "Can't parse entities" in str(e):
                        # إذا فشل تنسيق HTML، نرسل بدون تنسيق
                        await query.edit_message_text(text=assignment_text)
                
                del self.current_assignments[user_id]
                
        except Exception as e:
            logging.error(f"Error in assignment callback: {str(e)}")
            await query.edit_message_text("عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.")
