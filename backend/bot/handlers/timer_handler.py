"""
Обработчик для настройки таймера обратного отсчета
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

from .states import COLLECTING_TIMER_SETTINGS, COLLECTING_PRICES


class TimerHandler(BaseHandler):
    """Обработчик для настройки таймера"""
    
    async def select_timer_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор необходимости таймера"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        timer_needed = query.data == 'timer_yes'
        
        if not timer_needed:
            self.update_user_data(user_id, timer_enabled=False, timer_type=None, timer_date=None)
            # Сохраняем состояние перед переходом к ценам
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_PRICES', data)
            
            # Переходим к ценам
            await query.edit_message_text(
                "✅ Таймер не нужен.\n\n"
                "💰 **Цены на товар**\n\n"
                "Какая была цена ДО скидки?\n"
                "_Например: 152 BYN_",
                parse_mode='Markdown'
            )
            return COLLECTING_PRICES
        
        # Если нужен таймер - спрашиваем тип
        self.update_user_data(user_id, timer_enabled=True)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_TIMER_SETTINGS', data)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 До конкретной даты", callback_data="timer_type_date")],
            [InlineKeyboardButton("🔄 Обнуление каждые сутки", callback_data="timer_type_daily")]
        ])
        
        await query.edit_message_text(
            "⏱️ **Тип таймера**\n\n"
            "Выберите тип таймера:\n\n"
            "📅 **До конкретной даты** - таймер до указанной даты\n"
            "🔄 **Обнуление каждые сутки** - таймер обнуляется в 00:00",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_TIMER_SETTINGS
    
    async def select_timer_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа таймера"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        timer_type = query.data.replace('timer_type_', '')
        
        self.update_user_data(user_id, timer_type=timer_type)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_TIMER_SETTINGS', data)
        
        if timer_type == 'date':
            await query.edit_message_text(
                "📅 **Укажите дату окончания акции**\n\n"
                "Формат: ДД.ММ.ГГГГ\n"
                "_Например: 31.12.2024_",
                parse_mode='Markdown'
            )
            return COLLECTING_TIMER_SETTINGS
        else:  # daily
            self.update_user_data(user_id, timer_date=None)
            # Сохраняем состояние перед переходом к ценам
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_PRICES', data)
            
            # Переходим к ценам
            await query.edit_message_text(
                "✅ Таймер настроен: обнуление каждые сутки в 00:00\n\n"
                "💰 **Цены на товар**\n\n"
                "Какая была цена ДО скидки?\n"
                "_Например: 152 BYN_",
                parse_mode='Markdown'
            )
            return COLLECTING_PRICES
    
    async def collect_timer_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор даты для таймера"""
        user_id = update.effective_user.id
        date_text = update.message.text.strip()
        
        # Простая валидация формата
        if '.' not in date_text or len(date_text.split('.')) != 3:
            await update.message.reply_text(
                "❌ Неверный формат. Используйте: ДД.ММ.ГГГГ\n"
                "_Например: 31.12.2024_",
                parse_mode='Markdown'
            )
            return COLLECTING_TIMER_SETTINGS
        
        self.update_user_data(user_id, timer_date=date_text)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_PRICES', data)
        
        await update.message.reply_text(
            f"✅ Дата сохранена: **{date_text}**\n\n"
            "💰 **Цены на товар**\n\n"
            "Какая была цена ДО скидки?\n"
            "_Например: 152 BYN_",
            parse_mode='Markdown'
        )
        return COLLECTING_PRICES

