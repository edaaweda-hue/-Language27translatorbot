import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translator with thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)

# Language codes for 27 languages
SUPPORTED_LANGUAGES = {
    'af': 'Afrikaans',
    'ar': 'Arabic',
    'zh-CN': 'Chinese (Simplified)',
    'zh-TW': 'Chinese (Traditional)',
    'nl': 'Dutch',
    'en': 'English',
    'fi': 'Finnish',
    'fr': 'French',
    'de': 'German',
    'el': 'Greek',
    'hi': 'Hindi',
    'it': 'Italian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ms': 'Malay',
    'mr': 'Marathi',
    'ne': 'Nepali',
    'fa': 'Persian',
    'pl': 'Polish',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'es': 'Spanish',
    'sw': 'Swahili',
    'sv': 'Swedish',
    'ta': 'Tamil',
    'te': 'Telugu',
    'th': 'Thai',
    'tr': 'Turkish',
    'uk': 'Ukrainian',
    'ur': 'Urdu',
    'vi': 'Vietnamese'
}

# User state storage
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    welcome_text = f"""
👋 Hello {user.first_name}! I'm Language27 Translator Bot.

I can translate between 27 languages. Here's how to use me:

📝 **How to use:**
1. Send me any text
2. I'll detect the language automatically
3. Use /setlang to choose your target language (default: English)
4. Use /help to see all commands

🌍 **Supported languages:** 27 languages available!
    """
    
    keyboard = [
        [InlineKeyboardButton("🌍 Set Target Language", callback_data='set_lang')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = """
🤖 **Available Commands:**

/start - Start the bot
/help - Show this help message
/setlang - Set your target translation language
/listlang - List all supported languages
/current - Show your current settings
/about - About this bot

**How to translate:**
1. Set your target language using /setlang
2. Send any text message
3. I'll translate it to your target language

**Default:** Target language is English
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_languages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all supported languages."""
    lang_list = "🌍 **Supported Languages:**\n\n"
    
    languages = list(SUPPORTED_LANGUAGES.items())
    for i in range(0, len(languages), 3):
        chunk = languages[i:i+3]
        line = " | ".join([f"`{code}` - {name}" for code, name in chunk])
        lang_list += line + "\n"
    
    await update.message.reply_text(lang_list, parse_mode='Markdown')

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the target language for translation."""
    user_id = update.effective_user.id
    
    keyboard = []
    row = []
    for i, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
        row.append(InlineKeyboardButton(name, callback_data=f'lang_{code}'))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌍 Select your target language for translation:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == 'set_lang':
        keyboard = []
        row = []
        for i, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
            row.append(InlineKeyboardButton(name, callback_data=f'lang_{code}'))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌍 Select your target language for translation:",
            reply_markup=reply_markup
        )
    
    elif data == 'help':
        help_text = """
🤖 **Help:**

I translate messages to your chosen target language.

**Quick start:**
1. Use /setlang to choose your target language
2. Send me text in any language
3. I'll translate it to your target language

**Default language:** English
        """
        await query.edit_message_text(help_text)
    
    elif data.startswith('lang_'):
        lang_code = data.replace('lang_', '')
        lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)
        
        user_states[user_id] = {'target_lang': lang_code}
        
        await query.edit_message_text(
            f"✅ Target language set to: **{lang_name}**\n\n"
            f"Now send me any text and I'll translate it to {lang_name}!"
        )
    
    elif data == 'cancel':
        await query.edit_message_text("❌ Operation cancelled.")

def translate_sync(text, target_lang):
    """Synchronous translation function for thread pool."""
    try:
        # Detect language
        detector = GoogleTranslator(source='auto', target='en')
        detected = detector.translate(text[:100])  # Use first 100 chars for detection
        
        # Translate
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated = translator.translate(text)
        return translated, detected
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None, None

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate incoming messages."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text or len(text.strip()) == 0:
        await update.message.reply_text("Please send me some text to translate!")
        return
    
    # Get user's target language (default to English)
    target_lang = 'en'
    if user_id in user_states:
        target_lang = user_states[user_id].get('target_lang', 'en')
    
    try:
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Run translation in thread pool (non-blocking)
        loop = asyncio.get_event_loop()
        translated_text, detected_text = await loop.run_in_executor(
            executor, translate_sync, text, target_lang
        )
        
        if translated_text is None:
            await update.message.reply_text(
                "❌ Sorry, I couldn't translate that message. Please try again."
            )
            return
        
        # Get language names
        target_lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        
        # Try to detect source language (simplified detection)
        source_lang_name = "Unknown"
        for code, name in SUPPORTED_LANGUAGES.items():
            # Simple check - if translated text equals original, language might be same
            if translated_text == text and code == target_lang:
                source_lang_name = target_lang_name
                break
        
        response = f"""
🔤 **Translation:**

📝 **Original:**
{text}

🔄 **Translated to {target_lang_name}:**
{translated_text}
        """
        
        # Add note if same language
        if translated_text == text and target_lang in SUPPORTED_LANGUAGES:
            response += f"\n\nℹ️ The text appears to already be in {target_lang_name}."
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ Sorry, I couldn't translate that message. Please try again later."
        )

async def current_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current settings."""
    user_id = update.effective_user.id
    
    if user_id in user_states:
        target_lang = user_states[user_id].get('target_lang', 'en')
        lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        await update.message.reply_text(
            f"⚙️ **Current Settings:**\n"
            f"Target Language: **{lang_name}**\n\n"
            f"To change, use /setlang"
        )
    else:
        await update.message.reply_text(
            "⚙️ **Current Settings:**\n"
            f"Target Language: **English** (default)\n\n"
            f"To change, use /setlang"
        )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About the bot."""
    about_text = """
🤖 **Language27 Translator Bot**

A powerful translation bot supporting 27 languages.

**Features:**
• Auto language detection
• Translation to 27 languages
• Simple and intuitive interface
• Fast and accurate translations

**Tech Stack:**
• Python 3.11
• python-telegram-bot
• deep-translator (Google Translate API)

Made with ❤️ for the Telegram community
    """
    await update.message.reply_text(about_text)

def main():
    """Start the bot."""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables")
        return
    
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setlang", set_language))
    application.add_handler(CommandHandler("listlang", list_languages))
    application.add_handler(CommandHandler("current", current_settings))
    application.add_handler(CommandHandler("about", about))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

    # Check if running on Railway
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        port = int(os.environ.get('PORT', 8443))
        domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
        
        if domain:
            webhook_url = f"https://{domain}/{token}"
        else:
            webhook_url = f"https://{os.environ.get('RAILWAY_STATIC_URL', '')}/{token}"
        
        logger.info(f"Starting webhook on port {port}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=webhook_url
        )
    else:
        logger.info("Starting polling mode...")
        application.run_polling()

if __name__ == '__main__':
    main()
