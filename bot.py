import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from googletrans import Translator, LANGUAGES
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translator
translator = Translator()

# Language codes for 27 languages
SUPPORTED_LANGUAGES = {
    'af': 'Afrikaans',
    'ar': 'Arabic',
    'zh-cn': 'Chinese (Simplified)',
    'zh-tw': 'Chinese (Traditional)',
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

# User state storage (simple in-memory, use database for production)
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
    
    # Create inline keyboard for language selection
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
    
    # Format languages in columns for better readability
    languages = list(SUPPORTED_LANGUAGES.items())
    for i in range(0, len(languages), 3):
        chunk = languages[i:i+3]
        line = " | ".join([f"`{code}` - {name}" for code, name in chunk])
        lang_list += line + "\n"
    
    await update.message.reply_text(lang_list, parse_mode='Markdown')

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the target language for translation."""
    user_id = update.effective_user.id
    
    # Create language selection keyboard (paginated)
    keyboard = []
    row = []
    for i, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
        row.append(InlineKeyboardButton(name, callback_data=f'lang_{code}'))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add cancel button
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
        # Show language selection
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
        
        # Store user preference
        user_states[user_id] = {'target_lang': lang_code}
        
        await query.edit_message_text(
            f"✅ Target language set to: **{lang_name}**\n\n"
            f"Now send me any text and I'll translate it to {lang_name}!"
        )
    
    elif data == 'cancel':
        await query.edit_message_text("❌ Operation cancelled.")

async def translate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate incoming messages."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Get user's target language (default to English)
    target_lang = 'en'
    if user_id in user_states:
        target_lang = user_states[user_id].get('target_lang', 'en')
    
    try:
        # Detect language
        detection = translator.detect(text)
        source_lang = detection.lang
        confidence = detection.confidence
        
        # Don't translate if already in target language
        if source_lang == target_lang:
            await update.message.reply_text(
                f"📝 Your message is already in {SUPPORTED_LANGUAGES[target_lang]}.\n"
                f"Send text in another language for translation."
            )
            return
        
        # Translate
        translation = translator.translate(text, dest=target_lang)
        
        # Prepare response
        source_lang_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
        target_lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        
        response = f"""
🔤 **Translation:**
*From:* {source_lang_name} (Confidence: {confidence:.2%})
*To:* {target_lang_name}

📝 **Original:**
{text}

🔄 **Translated:**
{translation.text}
        """
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ Sorry, I couldn't translate that message. Please try again."
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
• Python
• python-telegram-bot
• Google Translate API

Made with ❤️ for the Telegram community
    """
    await update.message.reply_text(about_text)

def main():
    """Start the bot."""
    # Create the Application
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
    
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for translations
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_message))

    # Start the bot
    port = int(os.environ.get('PORT', 8443))
    
    # Check if running on Railway (using PORT environment variable)
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Webhook mode for Railway
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')}/{token}"
        )
    else:
        # Polling mode for local development
        application.run_polling()

if __name__ == '__main__':
    main()
