import mysql.connector
import logging
import json
from typing import Optional, List, Dict, Any

class DatabaseHandler:
    def __init__(self):
        """Initialize MySQL connection"""
        try:
            self.connection = mysql.connector.connect(
                host='codro0-0-codro.c.aivencloud.com',
                port=23589,
                database='defaultdb',
                user='avnadmin',
                password='AVNS_ho02-brH04n6oeORpCL'
            )
            self.cursor = self.connection.cursor(dictionary=True)
            
            # إنشاء جدول سجل المحادثة إذا لم يكن موجوداً
            self._create_chat_history_table()
            logging.info("✅ تم الاتصال بنجاح بقاعدة البيانات MySQL")
        except Exception as e:
            logging.error(f"❌ خطأ في الاتصال بقاعدة البيانات MySQL: {str(e)}")
            self.connection = None
            self.cursor = None
    
    def _create_chat_history_table(self):
        """إنشاء جدول سجل المحادثة إذا لم يكن موجوداً"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            chat_history TEXT,
            INDEX idx_telegram_id (telegram_id)
        )
        """
        self.cursor.execute(create_table_query)
        self.connection.commit()

    async def save_chat_history(self, telegram_id: int, chat_history: List[Dict[str, Any]]) -> bool:
        """حفظ سجل المحادثة في قاعدة البيانات
        
        Args:
            telegram_id: معرف المستخدم في تيليجرام
            chat_history: قائمة المحادثات
            
        Returns:
            bool: True إذا تم الحفظ بنجاح، False في حالة الخطأ
        """
        if not self.connection or not self.cursor:
            logging.error("❌ لم يتم الاتصال بقاعدة البيانات")
            return False
            
        try:
            # تحويل قائمة المحادثات إلى JSON
            chat_history_json = json.dumps(chat_history)
            
            # التحقق من وجود سجل للمستخدم
            check_query = "SELECT id FROM chat_history WHERE telegram_id = %s"
            self.cursor.execute(check_query, (telegram_id,))
            existing_record = self.cursor.fetchone()
            
            if existing_record:
                # تحديث السجل الموجود
                update_query = """
                UPDATE chat_history 
                SET chat_history = %s
                WHERE telegram_id = %s
                """
                self.cursor.execute(update_query, (chat_history_json, telegram_id))
            else:
                # إنشاء سجل جديد
                insert_query = """
                INSERT INTO chat_history (telegram_id, chat_history)
                VALUES (%s, %s)
                """
                self.cursor.execute(insert_query, (telegram_id, chat_history_json))
            
            self.connection.commit()
            logging.info(f"✅ تم حفظ سجل المحادثة بنجاح لـ telegram_id={telegram_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ خطأ في حفظ سجل المحادثة لـ telegram_id={telegram_id}: {str(e)}")
            return False

    async def get_chat_history(self, telegram_id: int) -> List[Dict[str, Any]]:
        """استرجاع سجل المحادثة من قاعدة البيانات
        
        Args:
            telegram_id: معرف المستخدم في تيليجرام
            
        Returns:
            List[Dict]: قائمة المحادثات أو قائمة فارغة في حالة الخطأ
        """
        if not self.connection or not self.cursor:
            logging.error("❌ لم يتم الاتصال بقاعدة البيانات")
            return []
            
        try:
            query = """
            SELECT chat_history 
            FROM chat_history 
            WHERE telegram_id = %s
            """
            self.cursor.execute(query, (telegram_id,))
            result = self.cursor.fetchone()
            
            if result and result['chat_history']:
                chat_history = json.loads(result['chat_history'])
                logging.info(f"✅ تم استرجاع سجل المحادثة بنجاح لـ telegram_id={telegram_id}")
                return chat_history
            
            return []
            
        except Exception as e:
            logging.error(f"❌ خطأ في استرجاع سجل المحادثة لـ telegram_id={telegram_id}: {str(e)}")
            return []
    
    def __del__(self):
        """إغلاق الاتصال عند حذف الكائن"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'connection') and self.connection:
            self.connection.close()
