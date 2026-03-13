import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import subprocess
import tempfile

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة (من Railway)
TOKEN = os.environ.get('TOKEN')
PORT = int(os.environ.get('PORT', 8080))

# الصيغ المدعومة للتحويل
SUPPORTED_FORMATS = {
    'document': {
        'pdf': ['docx', 'txt', 'html', 'odt'],
        'docx': ['pdf', 'txt', 'html', 'odt'],
        'txt': ['pdf', 'docx', 'html'],
    },
    'image': {
        'jpg': ['png', 'webp', 'gif', 'ico'],
        'png': ['jpg', 'webp', 'gif', 'ico'],
        'webp': ['jpg', 'png', 'gif'],
    },
    'video': {
        'mp4': ['avi', 'mkv', 'mov', 'gif'],
        'avi': ['mp4', 'mkv', 'mov'],
        'mkv': ['mp4', 'avi', 'mov'],
    },
    'audio': {
        'mp3': ['wav', 'ogg', 'm4a', 'flac'],
        'wav': ['mp3', 'ogg', 'flac'],
        'ogg': ['mp3', 'wav', 'flac'],
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    welcome_text = """
🌟 مرحباً بك في بوت تحويل الملفات! 🌟

📁 أرسل لي أي ملف وسأقوم بتحويله للصيغة التي تريدها!

✨ الصيغ المدعومة:
• المستندات: PDF, DOCX, TXT, HTML
• الصور: JPG, PNG, WEBP, GIF
• الفيديو: MP4, AVI, MKV, MOV
• الصوت: MP3, WAV, OGG, FLAC

🔄 فقط أرسل الملف واختر الصيغة المطلوبة!
    """
    await update.message.reply_text(welcome_text)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملفات المرسلة"""
    try:
        # تخزين معلومات الملف
        if update.message.document:
            file = update.message.document
            file_type = 'document'
            file_name = file.file_name
            file_ext = file_name.split('.')[-1].lower()
        elif update.message.photo:
            file = update.message.photo[-1]
            file_type = 'image'
            file_name = 'photo.jpg'
            file_ext = 'jpg'
        elif update.message.video:
            file = update.message.video
            file_type = 'video'
            file_name = file.file_name if file.file_name else 'video.mp4'
            file_ext = file_name.split('.')[-1].lower()
        elif update.message.audio:
            file = update.message.audio
            file_type = 'audio'
            file_name = file.file_name if file.file_name else 'audio.mp3'
            file_ext = file_name.split('.')[-1].lower()
        elif update.message.voice:
            file = update.message.voice
            file_type = 'audio'
            file_name = 'voice.ogg'
            file_ext = 'ogg'
        else:
            await update.message.reply_text("❌ هذا النوع من الملفات غير مدعوم!")
            return
        
        # تحميل الملف
        await update.message.reply_text("📥 جاري تحميل الملف...")
        file_obj = await file.get_file()
        
        # حفظ مؤقت للملف
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp_file:
            await file_obj.download_to_drive(tmp_file.name)
            context.user_data['input_file'] = tmp_file.name
            context.user_data['file_type'] = file_type
            context.user_data['original_ext'] = file_ext
            context.user_data['file_name'] = file_name
        
        # عرض خيارات التحويل
        await show_conversion_options(update, context)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ حدث خطأ في معالجة الملف!")

async def show_conversion_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض أزرار الصيغ المتاحة للتحويل"""
    file_type = context.user_data.get('file_type')
    original_ext = context.user_data.get('original_ext')
    
    if file_type and original_ext in SUPPORTED_FORMATS.get(file_type, {}):
        formats = SUPPORTED_FORMATS[file_type][original_ext]
        keyboard = []
        
        # تقسيم الأزرار إلى صفين
        for i in range(0, len(formats), 2):
            row = []
            for fmt in formats[i:i+2]:
                row.append(InlineKeyboardButton(fmt.upper(), callback_data=f"convert_{fmt}"))
            keyboard.append(row)
        
        # زر إلغاء
        keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"🔽 اختر الصيغة المطلوبة للتحويل من {original_ext.upper()}:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ هذه الصيغة غير مدعومة للتحويل!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("✅ تم إلغاء العملية")
        return
    
    if query.data.startswith("convert_"):
        target_format = query.data.replace("convert_", "")
        await query.edit_message_text(f"🔄 جاري التحويل إلى {target_format.upper()}...")
        
        try:
            # تنفيذ التحويل
            input_file = context.user_data.get('input_file')
            original_ext = context.user_data.get('original_ext')
            file_type = context.user_data.get('file_type')
            
            # اسم الملف الناتج
            output_file = f"{input_file}.{target_format}"
            
            # التحويل حسب نوع الملف
            if file_type in ['video', 'audio']:
                # استخدام FFmpeg
                cmd = ['ffmpeg', '-i', input_file, '-y', output_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"FFmpeg error: {result.stderr}")
                    
            elif file_type == 'image':
                # تحويل الصور
                from PIL import Image
                img = Image.open(input_file)
                
                # معالجة خاصة لبعض الصيغ
                if target_format == 'ico':
                    img.save(output_file, format='ICO', sizes=[(256, 256)])
                elif target_format == 'webp':
                    img.save(output_file, format='WEBP', quality=80)
                else:
                    img.save(output_file, format=target_format.upper())
                    
            elif file_type == 'document':
                # تحويل المستندات
                if original_ext == 'txt' and target_format == 'pdf':
                    # تحويل TXT إلى PDF باستخدام fpdf
                    from fpdf import FPDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    
                    with open(input_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            pdf.cell(200, 10, txt=line, ln=True)
                    
                    pdf.output(output_file)
                else:
                    # استخدام LibreOffice للمستندات الأخرى
                    cmd = ['libreoffice', '--headless', '--convert-to', target_format, '--outdir', os.path.dirname(output_file), input_file]
                    subprocess.run(cmd, check=True, capture_output=True)
            
            # إرسال الملف المحول
            await query.message.reply_document(
                document=open(output_file, 'rb'),
                caption=f"✅ تم التحويل بنجاح من {original_ext.upper()} إلى {target_format.upper()}!"
            )
            
            # تنظيف الملفات المؤقتة
            os.unlink(input_file)
            os.unlink(output_file)
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            await query.message.reply_text(f"❌ فشل التحويل! {str(e)[:100]}")

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_document))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # تشغيل البوت (لـ Railway)
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/{TOKEN}"
    )

if __name__ == '__main__':
    main()