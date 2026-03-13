import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import tempfile
from PIL import Image

# إعدادات التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# متغيرات البيئة
TOKEN = os.environ.get('TOKEN')
PORT = int(os.environ.get('PORT', 8080))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    welcome_text = "🌟 مرحباً! أرسل لي أي صورة لتحويلها إلى PNG"
    await update.message.reply_text(welcome_text)
    logger.info(f"User {update.effective_user.id} started the bot")

async def convert_to_png(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحويل الصور إلى PNG"""
    try:
        photo = update.message.photo[-1]
        await update.message.reply_text("📥 جاري التحميل...")
        
        # تحميل الصورة
        file = await photo.get_file()
        
        # ملفات مؤقتة
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as input_file:
            await file.download_to_drive(input_file.name)
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as output_file:
            output_path = output_file.name
        
        # تحويل الصورة
        img = Image.open(input_path)
        img.save(output_path, 'PNG')
        
        # إرسال الصورة المحولة
        await update.message.reply_document(
            document=open(output_path, 'rb'),
            caption="✅ تم التحويل إلى PNG!"
        )
        
        # تنظيف الملفات المؤقتة
        os.unlink(input_path)
        os.unlink(output_path)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ حدث خطأ في التحويل")

def main():
    """تشغيل البوت"""
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, convert_to_png))
    
    # تشغيل webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/{TOKEN}"
    )

if __name__ == '__main__':
    main()
