"""
Обработчик для сбора цен на товар
"""
from telegram import Update
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

from .states import COLLECTING_PRICES, COLLECTING_FORM_OPTIONS


class PriceHandler(BaseHandler):
    """Обработчик для сбора цен"""
    
    async def collect_prices(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор цен (пункт 5 структуры) - универсальный обработчик для старой и новой цены"""
        user_id = update.effective_user.id
        price_text = update.message.text.strip()
        
        # Добавляем BYN если валюта не указана
        if not any(c in price_text.upper() for c in ['BYN', 'BYR', 'RUB', 'USD', 'EUR', '₽', '$', '€']):
            price_text = f"{price_text} BYN"
        
        # Получаем текущие данные пользователя
        data = self.get_user_data(user_id)
        
        # Проверяем, собрана ли уже старая цена
        if 'old_price' not in data or not data.get('old_price'):
            # Собираем старую цену (до скидки)
            self.update_user_data(user_id, old_price=price_text)
            self.log('info', f'Entered old price: {price_text}', user_id)
            
            await update.message.reply_text(
                "💵 **Цена СО СКИДКОЙ**\n\n"
                "Какая цена со скидкой?\n"
                "_Например: 99 BYN_",
                parse_mode='Markdown'
            )
            return COLLECTING_PRICES
        else:
            # Собираем новую цену (со скидкой)
            self.update_user_data(user_id, new_price=price_text)
            self.log('info', f'Entered new price: {price_text}', user_id)
            
            # Сохраняем состояние перед переходом к опциям формы
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FORM_OPTIONS', data)
            
            # Всегда переходим к сбору опций формы (пункт 6 структуры)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор размера", callback_data="form_size_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_size_no")]
            ])
            
            await update.message.reply_text(
                "✅ Цены сохранены!\n\n"
                "📋 **Форма заказа**\n\n"
                "Нужен ли выбор размера в форме заказа?",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
    
    async def collect_new_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор новой цены (устаревший метод, используйте collect_prices)"""
        # Перенаправляем на основной метод
        return await self.collect_prices(update, context)

