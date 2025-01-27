from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import html


class replys:
    def __init__(self, system_prompt, BOT_CONFIG, format_message, get_message, db_handler):
        self.system_prompt = system_prompt
        self.BOT_CONFIG = BOT_CONFIG
        self.format_message = format_message
        self.get_message = get_message
        self.db_handler = db_handler

    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send course information"""
        try:
            if isinstance(self.BOT_CONFIG, dict):
                course = self.BOT_CONFIG.get("DEFAULT_BOT_CONFIG", {}).get("course_info", {})
            else:
                course = self.BOT_CONFIG.DEFAULT_BOT_CONFIG.get("course_info", {})

            info_message = f"""
📚 <strong>معلومات عن كورس {course.get('name', 'Python')}</strong>

⏱️ <strong>معلومات عامة:</strong>
• المدة: {course.get('duration_weeks', 16)} أسبوع
• عدد الحصص: {course.get('lessons_per_week', 1)} حصة أسبوعياً
• مدة الحصة: {course.get('lesson_duration_hours', 2)} ساعات
• المستوى: {course.get('level', 'مبتدئ')}

📖 <strong>محتوى الكورس:</strong>

"""
            # إضافة محتوى الدروس
            lessons = course.get('lessons', {})
            for lesson_key, lesson_data in lessons.items():
                info_message += f"""
<strong>{lesson_key}: {lesson_data['title']}</strong>
{lesson_data['description']}
"""

            info_message += f"""
🔗 <strong>للانضمام للكورس:</strong>
• رابط المجموعة: <a href="{course.get('group_link', 'https://t.me/+gVcWKBI6ZeY1ZGY0')}">اضغط هنا</a>
"""

            await update.message.reply_text(
                info_message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            # استرجاع المحادثة الحالية وإضافة الرسالة الجديدة
            current_chat_history = await self.db_handler.get_chat_history(update.effective_user.id)
            new_messages = [
                {"role": "user", "parts": ["/info"]},
                {"role": "model", "parts": [info_message]}
            ]
            current_chat_history.extend(new_messages)
            await self.db_handler.save_chat_history(update.effective_user.id, current_chat_history)

        except Exception as e:
            await update.message.reply_text("عذراً، حدث خطأ في عرض معلومات الكورس. برجاء المحاولة مرة أخرى.")
            print(e)

    async def advice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        advice_message = """💡 <strong>نصائح تعليمية لتحسين مستواك:</strong>

• تدرب بشكل يومي ولو لمدة 30 دقيقة
• اكتب الكود بنفسك ولا تكتفي بالنسخ واللصق
• حل التمارين المطلوبة بعد كل درس
• شارك في مجموعة الدعم وناقش مع زملائك
• راجع الدروس السابقة باستمرار

للمزيد من النصائح، تواصل مع المدربين 👨‍🏫"""

        await update.message.reply_text(advice_message, parse_mode="HTML")
        
        # استرجاع المحادثة الحالية وإضافة الرسالة الجديدة
        current_chat_history = await self.db_handler.get_chat_history(update.effective_user.id)
        new_messages = [
            {"role": "user", "parts": ["/advice"]},
            {"role": "model", "parts": [advice_message]}
        ]
        current_chat_history.extend(new_messages)
        await self.db_handler.save_chat_history(update.effective_user.id, current_chat_history)

    async def ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        ask_message = """🗨️ <strong>كيف يمكنني مساعدتك؟</strong>

يمكنك السؤال عن:
• محتوى الكورس
• المواعيد والجدول
• المتطلبات التقنية
• طرق الدفع والتسجيل
• أي استفسار آخر

ما هو سؤالك؟ 🤔"""

        await update.message.reply_text(ask_message, parse_mode="HTML")
        
        # استرجاع المحادثة الحالية وإضافة الرسالة الجديدة
        current_chat_history = await self.db_handler.get_chat_history(update.effective_user.id)
        new_messages = [
            {"role": "user", "parts": ["/ask"]},
            {"role": "model", "parts": [ask_message]}
        ]
        current_chat_history.extend(new_messages)
        await self.db_handler.save_chat_history(update.effective_user.id, current_chat_history)

    async def courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = """🎓 <strong>الكورسات المتاحة حالياً:</strong>

• Python Basics - كورس البرمجة للمبتدئين
• المزيد من الكورسات قريباً!

اختر الكورس الذي تريد معرفة المزيد عنه:"""

        keyboard = [
            [InlineKeyboardButton("Python Basics", callback_data='python_basics')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
        
        # استرجاع المحادثة الحالية وإضافة الرسالة الجديدة
        current_chat_history = await self.db_handler.get_chat_history(update.effective_user.id)
        new_messages = [
            {"role": "user", "parts": ["/courses"]},
            {"role": "model", "parts": [message]}
        ]
        current_chat_history.extend(new_messages)
        await self.db_handler.save_chat_history(update.effective_user.id, current_chat_history)

    async def schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if isinstance(self.BOT_CONFIG, dict):
                schedule = self.BOT_CONFIG.get("DEFAULT_BOT_CONFIG", {}).get("schedule", {})
            else:
                schedule = self.BOT_CONFIG.DEFAULT_BOT_CONFIG.get("schedule", {})

            schedule_message = f"""📅 <b>جدول الكورس:</b>

<b>الحصص الافتراضية</b>
• 🕒 <b>المدة:</b> ساعة ونصف إلى ساعتين
• 🌐 <b>المكان:</b> أونلاين عبر Zoom
• 📚 <b>عدد الحصص:</b> 16
• حصة واحدة أسبوعياً

<b>الحصص الفعلية</b>
• 🕒 <b>المدة:</b> ساعتين إلى ساعتين ونصف
• 📌 <b>المكان:</b> شارع عزيز نسيم أمام مستشفى الرمد
(لمعرفة المزيد من التفاصيل يرجى التواصل مع المشرف)
• 📚 <b>عدد الحصص:</b> 4
• حصة واحدة شهرياً

💡 <b>ملاحظات:</b>
• يمكنك <a href="https://t.me/+gVcWKBI6ZeY1ZGY0">الانضمام إلى المجموعة</a> لمتابعة أي تحديثات في المواعيد.
• للتواصل مع <a href="https://t.me/CodroCourse">المشرف</a>.
"""

            await update.message.reply_text(schedule_message, parse_mode="HTML")
            
            # استرجاع المحادثة الحالية وإضافة الرسالة الجديدة
            current_chat_history = await self.db_handler.get_chat_history(update.effective_user.id)
            new_messages = [
                {"role": "user", "parts": ["/schedule"]},
                {"role": "model", "parts": [schedule_message]}
            ]
            current_chat_history.extend(new_messages)
            await self.db_handler.save_chat_history(update.effective_user.id, current_chat_history)

        except Exception as e:
            await update.message.reply_text("عذراً، حدث خطأ في عرض جدول الكورس. برجاء المحاولة مرة أخرى.")

    async def contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if isinstance(self.BOT_CONFIG, dict):
                instructors = self.BOT_CONFIG.get("DEFAULT_BOT_CONFIG", {}).get("instructors", [])
            else:
                instructors = self.BOT_CONFIG.DEFAULT_BOT_CONFIG.get("instructors", [])

            contact_message = f"""👨‍🏫 <strong>للتواصل مع المدربين:</strong>

• عثمان مصطفى النحراوي
  رقم التواصل: 01062385475
  تليجرام: @CodroCourse

• يوسف فتحي غالي
  رقم التواصل: 01023592779
  تليجرام: @yousefghaly

• 🔗 رابط المجموعة: <a href="https://t.me/+gVcWKBI6ZeY1ZGY0">اضغط هنا</a>"""

            await update.message.reply_text(contact_message, parse_mode="HTML", disable_web_page_preview=True)
            
            # استرجاع المحادثة الحالية وإضافة الرسالة الجديدة
            current_chat_history = await self.db_handler.get_chat_history(update.effective_user.id)
            new_messages = [
                {"role": "user", "parts": ["/contact"]},
                {"role": "model", "parts": [contact_message]}
            ]
            current_chat_history.extend(new_messages)
            await self.db_handler.save_chat_history(update.effective_user.id, current_chat_history)

        except Exception as e:
            await update.message.reply_text("عذراً، حدث خطأ في عرض معلومات التواصل. برجاء المحاولة مرة أخرى.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        await query.answer()

        if query.data == 'python_basics':
            course_info = """📚 <b>Python Basics</b>

🌟 <b>وصف الكورس:</b>
تعلم أساسيات البرمجة باستخدام Python، بدءًا من المفاهيم الأساسية وحتى التعامل مع الملفات والفئات.

📝 <b>المواضيع التي ستتعلمها:</b>
1. مقدمة إلى بايثون وإعداد البيئة
2. فهم المتغيرات وأنواع البيانات
3. الجمل الشرطية - If Statement
4. الحلقات - While و For
5. التعامل مع الملفات، القواميس، والمجموعات
6. التعامل مع الأخطاء - Try، Except، وFinally
7. مقدمة إلى الفئات والكائنات

⏳ <b>مدة الكورس:</b> 16 أسبوع (حصة واحدة أسبوعيًا)

🔗 <b>للتواصل:</b>
• @CodroCourse
• @yousefghaly

🔗 <b>للإنضمام للمجتمع:</b> <a href="https://t.me/+gVcWKBI6ZeY1ZGY0">أنضم الآن</a>"""

            await query.message.reply_text(course_info, parse_mode="HTML", disable_web_page_preview=True)