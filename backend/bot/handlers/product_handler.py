"""
Обработчик для сбора информации о товаре (название, характеристики)
"""
from telegram import Update
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

from .states import COLLECTING_PRODUCT_NAME, COLLECTING_CHARACTERISTICS, COLLECTING_TIMER_SETTINGS, COLLECTING_HERO_MEDIA


class ProductHandler(BaseHandler):
    """Обработчик для сбора информации о товаре"""
    
    async def collect_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор названия товара (пункт 2 структуры)"""
        user_id = update.effective_user.id
        product_name = update.message.text.strip()
        
        self.update_user_data(user_id, product_name=product_name)
        self.log('info', f'Entered product name: {product_name}', user_id)
        
        # Сохраняем состояние перед переходом к hero блоку
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_HERO_MEDIA', data)
        
        # Переходим к hero блоку (пункт 1 структуры)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Фото", callback_data="hero_photo")],
            [InlineKeyboardButton("🎥 Видео", callback_data="hero_video")]
        ])
        
        await update.message.reply_text(
            "✅ Название сохранено!\n\n"
            "📸 **Hero блок (верхняя часть лендинга)**\n\n"
            "Выберите, что будет в верхней части:\n\n"
            "📸 **Фото** - фотография товара\n"
            "🎥 **Видео** - видео товара\n\n"
            "_Соотношение сторон: 3:4 или 9:16_",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_HERO_MEDIA
    
    async def collect_characteristics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор 3 ярких характеристик (пункт 3 структуры)"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Разделяем по строкам
        characteristics = [c.strip() for c in text.split('\n') if c.strip()][:3]
        
        if len(characteristics) < 3:
            await update.message.reply_text(
                f"⚠️ Указано только {len(characteristics)} характеристик.\n\n"
                "Нужно минимум 3. Добавьте ещё:",
                parse_mode='Markdown'
            )
            return COLLECTING_CHARACTERISTICS
        
        self.update_user_data(user_id, characteristics=characteristics[:3])
        self.log('info', f'Entered characteristics: {characteristics}', user_id)
        
        # Сохраняем состояние перед переходом к таймеру
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_TIMER_SETTINGS', data)
        
        # Переходим к таймеру (пункт 4 структуры)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, нужен таймер", callback_data="timer_yes")],
            [InlineKeyboardButton("❌ Нет, не нужен", callback_data="timer_no")]
        ])
        
        await update.message.reply_text(
            "✅ Характеристики сохранены!\n\n"
            "⏱️ **Таймер обратного отсчета**\n\n"
            "Нужен ли таймер обратного отсчета?\n\n"
            "Таймер можно настроить:\n"
            "• До конкретной даты\n"
            "• С обнулением каждые сутки",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_TIMER_SETTINGS

