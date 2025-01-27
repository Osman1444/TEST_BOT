import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import google.generativeai as genai
import json
import logging
import asyncio
from bot_config import Data
from utils import Utils

class QuizHandler:
    def __init__(self, bot_config, bot_messages, format_message_func, get_message_func, db_handler=None):
        self.BOT_CONFIG = bot_config
        self.DEFAULT_BOT_MESSAGES = bot_messages
        self.format_message = format_message_func
        self.get_message = get_message_func
        self.db_handler = db_handler
        self.current_quiz = {}
        self.utils = Utils(bot_config, bot_messages)
        self.courses = {
            'python': 'Python البرمجة بلغة',
        }
        self.questions_counts = [3, 5, 7, 10]
        self.lessons = {
            'python': [
                "مقدمة بايثون",
                "المتغيرات والبيانات",
                "الجمل الشرطية",
                "الحلقات التكرارية",
                "القوائم",
                "القوائم والحلقات",
                "الدوال والأساسيات",
                "التعامل مع الملفات",
                "القواميس والمجموعات",
                "إدارة الأخطاء",
                "الكائنات والفئات",
                "الوراثة والطرق"
            ]
        }

    async def start_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start quiz interaction using inline keyboards"""
        keyboard = []
        for course_id, course_name in self.courses.items():
            keyboard.append([InlineKeyboardButton(course_name, callback_data=f"course_{course_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 مرحباً! دعنا نبدأ الإختبار\n\n"
            "🎯 اختر الكورس الذي تريد الإختبار فيه:",
            reply_markup=reply_markup
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        print('qwertyuiop[;lkjhgfdsxcvb')
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        
        try:
            if data.startswith('course_'):
                course = data.replace('course_', '')
                if user_id not in self.current_quiz:
                    self.current_quiz[user_id] = {}
                self.current_quiz[user_id]['course'] = course
                
                # Show number of questions selection
                keyboard = []
                row = []
                for count in self.questions_counts:
                    row.append(InlineKeyboardButton(str(count), callback_data=f"count_{count}"))
                keyboard.append(row)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await query.edit_message_text(
                        "🔢 كم عدد الأسئلة التي تريدها؟",
                        reply_markup=reply_markup
                    )
                except telegram.error.BadRequest as e:
                    if "message is not modified" in str(e).lower():
                        pass  # تجاهل خطأ عدم تغيير الرسالة
                    else:
                        raise
                except telegram.error.NetworkError:
                    # محاولة إعادة الإرسال في حالة مشاكل الشبكة
                    await asyncio.sleep(1)  # انتظار ثانية
                    await query.edit_message_text(
                        "🔢 كم عدد الأسئلة التي تريدها؟",
                        reply_markup=reply_markup
                    )
                
            elif data.startswith('count_'):
                count = int(data.replace('count_', ''))
                self.current_quiz[user_id]['question_count'] = count
                
                # Show lessons selection for the chosen course
                course = self.current_quiz[user_id]['course']
                keyboard = []
                row = []
                for i, lesson in enumerate(self.lessons[course]):
                    # إضافة الدرس للصف الحالي
                    row.append(InlineKeyboardButton(lesson, callback_data=f"lesson_{lesson}"))
                    # كل درسين في صف
                    if len(row) == 2 or i == len(self.lessons[course]) - 1:
                        keyboard.append(row)
                        row = []
                
                # إضافة زر تم الاختيار في صف منفصل
                keyboard.append([InlineKeyboardButton("✅ تم الإختيار", callback_data="finish_selection")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                self.current_quiz[user_id]['selected_lessons'] = []
                try:
                    await query.edit_message_text(
                        "📚 اختر الدروس التي تريد الإختبار فيها\n"
                        "يمكنك اختيار أكثر من درس، وعند الانتهاء اضغط على 'تم الإختيار'\n"
                        "اضغط على الدرس مرة أخرى لإلغاء اختياره",
                        reply_markup=reply_markup
                    )
                except telegram.error.BadRequest as e:
                    if "message is not modified" in str(e).lower():
                        pass
                    else:
                        raise
                except telegram.error.NetworkError:
                    # محاولة إعادة الإرسال في حالة مشاكل الشبكة
                    await asyncio.sleep(1)  # انتظار ثانية
                    await query.edit_message_text(
                        "📚 اختر الدروس التي تريد الإختبار فيها\n"
                        "يمكنك اختيار أكثر من درس، وعند الانتهاء اضغط على 'تم الإختيار'\n"
                        "اضغط على الدرس مرة أخرى لإلغاء اختياره",
                        reply_markup=reply_markup
                    )
                
            elif data.startswith('lesson_'):
                lesson = data.replace('lesson_', '')
                if 'selected_lessons' not in self.current_quiz[user_id]:
                    self.current_quiz[user_id]['selected_lessons'] = []
                    
                # إضافة أو إزالة الدرس من القائمة المختارة
                if lesson in self.current_quiz[user_id]['selected_lessons']:
                    self.current_quiz[user_id]['selected_lessons'].remove(lesson)
                else:
                    self.current_quiz[user_id]['selected_lessons'].append(lesson)
                
                # Update the message to show selected lessons
                course = self.current_quiz[user_id]['course']
                keyboard = []
                row = []
                for i, l in enumerate(self.lessons[course]):
                    # إضافة علامة ✅ للدروس المختارة
                    text = f"✅ {l}" if l in self.current_quiz[user_id]['selected_lessons'] else l
                    row.append(InlineKeyboardButton(text, callback_data=f"lesson_{l}"))
                    # كل درسين في صف
                    if len(row) == 2 or i == len(self.lessons[course]) - 1:
                        keyboard.append(row)
                        row = []
                        
                keyboard.append([InlineKeyboardButton("✅ تم الإختيار", callback_data="finish_selection")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                selected_lessons_text = "\n".join([f"• {l}" for l in self.current_quiz[user_id]['selected_lessons']])
                try:
                    await query.edit_message_text(
                        "📚 اختر الدروس التي تريد الإختبار فيها\n"
                        "اضغط على الدرس مرة أخرى لإلغاء اختياره\n\n" +
                        ("الدروس المختارة:\n" + selected_lessons_text if selected_lessons_text else "لم يتم اختيار أي دروس بعد") +
                        "\n\nيمكنك اختيار المزيد أو الضغط على 'تم الإختيار' للبدء",
                        reply_markup=reply_markup
                    )
                except telegram.error.BadRequest as e:
                    if "message is not modified" in str(e).lower():
                        pass
                    else:
                        raise
                except telegram.error.NetworkError:
                    # محاولة إعادة الإرسال في حالة مشاكل الشبكة
                    await asyncio.sleep(1)  # انتظار ثانية
                    await query.edit_message_text(
                        "📚 اختر الدروس التي تريد الإختبار فيها\n"
                        "اضغط على الدرس مرة أخرى لإلغاء اختياره\n\n" +
                        ("الدروس المختارة:\n" + selected_lessons_text if selected_lessons_text else "لم يتم اختيار أي دروس بعد") +
                        "\n\nيمكنك اختيار المزيد أو الضغط على 'تم الإختيار' للبدء",
                        reply_markup=reply_markup
                    )
                
            elif data == "finish_selection":
                if len(self.current_quiz[user_id]['selected_lessons']) == 0:
                    await query.edit_message_text(
                        "⚠️ يجب اختيار درس واحد على الأقل! يرجى المحاولة مرة أخرى.",
                        reply_markup=None
                    )
                    return
                
                # Show message while generating quiz
                course_name = self.courses[self.current_quiz[user_id]['course']]
                await query.edit_message_text(
                    f"🎉 تم إعداد الإختبار!\n\n"
                    f"📚 الكورس: {course_name}\n"
                    f"🔢 عدد الأسئلة: {self.current_quiz[user_id]['question_count']}\n"
                    f"📝 الدروس المختارة:\n" +
                    "\n".join([f"• {l}" for l in self.current_quiz[user_id]['selected_lessons']]) +
                    "\n\n⏳ جاري إعداد الأسئلة..."
                )
                
                # Here you can add the logic to generate and start the actual quiz
                await self.generate_quiz(update, context)

        except Exception as e:
            logging.error(f"Error in handle_callback: {str(e)}")
            try:
                await query.message.reply_text(
                    "عذراً، حدث خطأ ما. الرجاء المحاولة مرة أخرى."
                )
            except:
                ...  # تجاهل أي أخطاء في إرسال رسالة الخطأ

    async def generate_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate quiz questions using GEMINI"""
        user_id = update.effective_user.id
        if user_id not in self.current_quiz:
            self.current_quiz[user_id] = {}
            
        quiz = self.current_quiz[user_id]
        course = quiz['course']
        selected_lessons = quiz['selected_lessons']
        
        # جمع شرح الدروس المختارة
        lessons_info = []
        config = Data()
        course_info = config.DEFAULT_BOT_CONFIG.get("course_info", {})
        
        # قاموس لتحويل الأسماء المختصرة إلى الأسماء الكاملة
        lesson_titles = {
            "مقدمة بايثون": "مقدمة إلى بايثون وإعداد البيئة",
            "المتغيرات والبيانات": "المتغيرات وأنواع البيانات",
            "الجمل الشرطية": "الجمل الشرطية",
            "الحلقات التكرارية": "الحلقات التكرارية",
            "القوائم": "القوائم - الجزء الأول",
            "القوائم والحلقات": "القوائم مع الحلقات",
            "الدوال والأساسيات": "الدوال",
            "التعامل مع الملفات": "التعامل مع الملفات",
            "القواميس والمجموعات": "القواميس والمجموعات",
            "إدارة الأخطاء": "معالجة الأخطاء",
            "الكائنات والفئات": "البرمجة كائنية التوجه - الجزء الأول",
            "الوراثة والطرق": "البرمجة كائنية التوجه - الجزء الثاني"
        }
        
        for lesson_name in selected_lessons:
            full_lesson_name = lesson_titles.get(lesson_name, lesson_name)
            for lesson_key, lesson_data in course_info.get('lessons', {}).items():
                if lesson_data['title'] == full_lesson_name:
                    lessons_info.append(f"{lesson_data['title']}:\n{lesson_data['description']}")
                    break
        
        lessons_details = "\n\n".join(lessons_info)
        
        system_prompt = """أنت مدرب برمجة متخصص في إنشاء أسئلة اختيار من متعدد لتقييم فهم الطلاب لمفاهيم البرمجة. مهمتك هي:

1. إنشاء أسئلة تختبر فهم المفاهيم البرمجية الأساسية
2. التركيز على التطبيق العملي للمفاهيم وليس مجرد الحفظ
3. تضمين أمثلة كود عند الحاجة
4. التأكد من أن الخيارات واضحة وذات صلة بالبرمجة
5. تغطية جميع المواضيع المذكورة في المحتوى المقدم

يجب أن يكون الرد في تنسيق JSON فقط، بالضبط كما يلي:
{
    "questions": [
        {
            "question": "نص السؤال",
            "options": ["الخيار 1", "الخيار 2", "الخيار 3", "الخيار 4"],
            "correct_answer": "الإجابة الصحيحة (يجب أن تكون واحدة من الخيارات بالضبط)"
        }
    ]
}

قواعد مهمة:
1. لا تضف أي نص أو تعليقات خارج تنسيق JSON
2. لا تستخدم أي علامات ترميز مثل ```json أو <code>
3. تأكد من أن الإجابة الصحيحة موجودة حرفياً في قائمة الخيارات
4. لا تضف أي حقول إضافية في JSON
5. ركز فقط على مواضيع البرمجة المذكورة في المحتوى المقدم

المحتوى المقدم:"""
        
        user_prompt = f"""أنشئ {quiz['question_count']} أسئلة اختيار من متعدد عن المواضيع التالية:

{lessons_details}"""
        
        # Configure Gemini
        genai.configure(api_key="AIzaSyAAhhHq792UUWT-e_6Ft0uYpkcBJ6FK5bs")
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-thinking-exp-01-21",
            generation_config={
                "temperature": 0.9,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
                "response_mime_type": "text/plain",
            },
            system_instruction=system_prompt
        )

        response = model.generate_content(user_prompt)
        print(response.text)
        try:
            # استخراج JSON من النص
            json_str = response.text
            # إزالة علامات code إذا وجدت
            if "<code>" in json_str:
                json_str = json_str.split("<code>")[1].split("</code>")[0]
            elif "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            json_str = json_str.strip()
            quiz_data = json.loads(json_str)
            print(quiz_data['questions'])
            self.current_quiz[user_id]['questions'] = quiz_data['questions']
            # تهيئة متغيرات الاختبار
            self.current_quiz[user_id].update({
                'current_question': 0,
                'score': 0,
                'question_count': len(quiz_data['questions'])
            })
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            self.current_quiz[user_id]['questions'] = []
            self.current_quiz[user_id].update({
                'current_question': 0,
                'score': 0,
                'question_count': 0
            })
        
        # Send the first question
        print('eslkkvbewh')
        await self.send_next_question(update, context)

    async def handle_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        print('lizedugn;oiweJvoiwjevoniنعع')
        """Handle quiz answer button callbacks"""
        query = update.callback_query
        print(query)
        
        if not query.data.startswith('ans_'):
            print('not ans')
            return
            
        user_id = query.from_user.id
        
        if user_id not in self.current_quiz:
            await query.answer("عذراً، انتهى الاختبار. يمكنك بدء اختبار جديد.")
            return

        # استخراج رقم السؤال والإجابة المختارة
        _, q_num, ans_index = query.data.split('_')
        q_num = int(q_num)
        current_q = self.current_quiz[user_id]['questions'][q_num - 1]
        selected_answer = current_q['options'][int(ans_index)]
        
        # تحديث النتيجة
        if 'score' not in self.current_quiz[user_id]:
            self.current_quiz[user_id]['score'] = 0
        
        # التحقق من صحة الإجابة
        is_correct = selected_answer == current_q['correct_answer']
        if is_correct:
            self.current_quiz[user_id]['score'] += 1
        
        # حفظ إجابة المستخدم
        if 'user_answers' not in self.current_quiz[user_id]:
            self.current_quiz[user_id]['user_answers'] = []
        self.current_quiz[user_id]['user_answers'].append(selected_answer)
        
        # تحديث أزرار الإجابات لإظهار الإجابة الصحيحة والخاطئة
        keyboard = []
        for i, option in enumerate(current_q['options']):
            if option == selected_answer:  # الإجابة المختارة
                text = f"{'✅' if is_correct else '❌'} {option}"
            elif option == current_q['correct_answer'] and not is_correct:  # الإجابة الصحيحة إذا كانت الإجابة خاطئة
                text = f"✅ {option}"
            else:
                text = option
            keyboard.append([InlineKeyboardButton(
                text,
                callback_data=f"ans_{q_num}_{i}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_reply_markup(reply_markup=reply_markup)
        except telegram.error.BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
        
        # إظهار رسالة التقييم
        feedback = "✅ إجابة صحيحة!" if is_correct else f"❌ إجابة خاطئة. الإجابة الصحيحة هي: {current_q['correct_answer']}"
        await query.answer(feedback)
        
        # الانتقال للسؤال التالي بعد ثانية
        await asyncio.sleep(1)
        self.current_quiz[user_id]['current_question'] += 1
        await self.send_next_question(update, context)

    async def send_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إرسال السؤال التالي أو إنهاء الاختبار"""
        if update.callback_query:
            user_id = update.callback_query.from_user.id
            message = update.callback_query.message
        else:
            user_id = update.effective_user.id
            message = update.message

        quiz = self.current_quiz[user_id]

        # التحقق من انتهاء الاختبار
        if quiz['current_question'] >= quiz['question_count']:
            # حساب النتيجة النهائية
            score_message = (
                f"🎯 النتيجة النهائية: {quiz['score']}/{quiz['question_count']}\n"
                f"النسبة المئوية: {(quiz['score']/quiz['question_count'])*100:.1f}%"
            )

            try:
                if update.callback_query:
                    await update.callback_query.message.reply_text(score_message, parse_mode="HTML")
                else:
                    await update.message.reply_text(score_message, parse_mode="HTML")

                # تقييم الأداء
                evaluation = await self.evaluate_performance(user_id)

                try:
                    if update.callback_query:
                        await update.callback_query.message.reply_text(evaluation, parse_mode="HTML")
                    else:
                        await update.message.reply_text(evaluation, parse_mode="HTML")
                except telegram.error.BadRequest:
                    # إذا فشل إرسال الرسالة بـ HTML، نحاول إرسالها كنص عادي
                    if update.callback_query:
                        await update.callback_query.message.reply_text(evaluation)
                    else:
                        await update.message.reply_text(evaluation)

                # حفظ نتائج الاختبار في قاعدة البيانات
                if self.db_handler:
                    await self.db_handler.save_message(
                        user_id=user_id,
                        message_type="quiz_result",
                        message_content=score_message + "\n\n" + evaluation,
                        course=quiz.get('course', 'Python'),
                        score=quiz['score'],
                        total=quiz['question_count']
                    )

                del self.current_quiz[user_id]
            except Exception as e:
                logging.error(f"Error sending final results: {str(e)}")
                await message.reply_text("عذراً، حدث خطأ في إرسال النتائج. يرجى المحاولة مرة أخرى.")
            return

        # إرسال السؤال التالي
        current_q = quiz['questions'][quiz['current_question']]
        keyboard = []
        for i, option in enumerate(current_q['options']):
            keyboard.append([InlineKeyboardButton(
                option,
                callback_data=f"ans_{quiz['current_question'] + 1}_{i}"
            )])
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            question_text = (
                f"السؤال {quiz['current_question'] + 1}/{quiz['question_count']}:\n\n"
                f"{current_q['question']}"
            )
            await message.reply_text(question_text, reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Error sending question: {str(e)}")
            await message.reply_text("عذراً، حدث خطأ في إرسال السؤال. يرجى المحاولة مرة أخرى.")

    async def evaluate_performance(self, user_id: int) -> str:
        """تقييم أداء المستخدم في الاختبار الحالي"""
        quiz = self.current_quiz.get(user_id)
        if not quiz:
            return "لم يتم العثور على اختبار نشط."

        total_questions = len(quiz['questions'])
        if total_questions == 0:
            return "لم يتم العثور على أسئلة في الاختبار."

        score = quiz.get('score', 0)
        percentage = (score / total_questions) * 100

        # تحضير تفاصيل الإجابات للتقييم
        answers_details = []
        for i, (q, user_ans) in enumerate(zip(quiz['questions'], quiz.get('user_answers', [])), 1):
            answers_details.append(
                f"<b>السؤال {i}:</b>\n"
                f"{q['question']}\n"
                f"<i>إجابتك:</i> {user_ans}\n"
                f"<i>الإجابة الصحيحة:</i> {q['correct_answer']}"
            )

        answers_summary = "\n\n".join(answers_details)

        system_prompt = """أنت مدرب برمجة. قيّم أداء الطالب في الاختبار بشكل مختصر. اتبع هذه القواعد:

1. اذكر النقاط المهمة فقط
2. ركز على المفاهيم الأساسية التي يجب تحسينها
3. قدم نصيحة واحدة أو اثنتين للتحسين
4. استخدم HTML للتنسيق (لا تستخدم Markdown)

يجب أن يكون التقييم في هذا الشكل:
<strong>النتيجة:</strong> X من Y

<strong>نقاط القوة:</strong>
• نقطة 1
• نقطة 2

<strong>نقاط تحتاج تحسين:</strong>
• نقطة 1
• نقطة 2

<strong>نصيحة للتحسين:</strong>
• نصيحة واحدة مختصرة"""

        evaluation_prompt = f"""<strong>النتيجة:</strong> {score}/{total_questions} ({percentage:.1f}%)\n\n{answers_summary}"""

        # Configure Gemini
        genai.configure(api_key="AIzaSyAAhhHq792UUWT-e_6Ft0uYpkcBJ6FK5bs")
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

        response = model.generate_content(evaluation_prompt)

        # تنظيف وتنسيق التقييم النهائي
        evaluation_text = self.utils.clean_html(response.text)
        final_evaluation = f"<b>نتيجة الاختبار:</b> {score}/{total_questions} ({percentage:.1f}%)\n\n{evaluation_text}"

        return final_evaluation
