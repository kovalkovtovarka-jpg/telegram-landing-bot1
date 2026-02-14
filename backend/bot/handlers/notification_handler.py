"""
Обработчик для настройки уведомлений
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from .states import COLLECTING_NOTIFICATION_TYPE, COLLECTING_NOTIFICATION_DATA, CONFIRMING


class NotificationHandler(BaseHandler):
    """Обработчик для настройки уведомлений"""
    
    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа уведомлений"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        notification_type = query.data.replace('notif_', '')
        
        self.update_user_data(user_id, notification_type=notification_type)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_NOTIFICATION_DATA', data)
        
        if notification_type == 'email':
            await query.edit_message_text(
                "📧 **Email для уведомлений**\n\n"
                "Введите email, на который будут приходить заявки:\n"
                "_Например: orders@example.com_",
                parse_mode='Markdown'
            )
        else:  # telegram
            await query.edit_message_text(
                "💬 **Telegram уведомления**\n\n"
                "Для получения уведомлений в Telegram нужно:\n\n"
                "1. Создать бота через @BotFather\n"
                "2. Получить токен бота\n"
                "3. Узнать свой Chat ID\n\n"
                "**Введите токен бота:**\n"
                "_Например: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz_",
                parse_mode='Markdown'
            )
        return COLLECTING_NOTIFICATION_DATA
    
    async def collect_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор данных уведомлений"""
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        notification_type = data.get('notification_type')
        
        if notification_type == 'email':
            email = update.message.text.strip()
            
            # Простая валидация email
            if '@' not in email or '.' not in email:
                await update.message.reply_text(
                    "❌ Неверный формат email!\n\n"
                    "Введите email в формате: example@domain.com",
                    parse_mode='Markdown'
                )
                return COLLECTING_NOTIFICATION_DATA
            
            self.update_user_data(user_id, notification_email=email, notification_data={'email': email})
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'CONFIRMING', data)
            
            await update.message.reply_text(
                f"✅ Email сохранен: **{email}**\n\n"
                "Переходим к подтверждению...",
                parse_mode='Markdown'
            )
            # Показываем сводку и запрашиваем подтверждение
            await self._show_summary(update, user_id)
            return CONFIRMING
        else:  # telegram
            token = update.message.text.strip()
            
            # Простая валидация токена (формат: число:строка)
            if ':' not in token or len(token.split(':')) != 2:
                await update.message.reply_text(
                    "❌ Неверный формат токена!\n\n"
                    "Токен должен быть в формате: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
                    parse_mode='Markdown'
                )
                return COLLECTING_NOTIFICATION_DATA
            
            self.update_user_data(user_id, notification_telegram_token=token)
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_NOTIFICATION_DATA', data)
            
            await update.message.reply_text(
                "✅ Токен сохранен!\n\n"
                "**Введите Chat ID:**\n"
                "_Например: 123456789_\n\n"
                "_Чтобы узнать Chat ID, напишите боту @userinfobot_",
                parse_mode='Markdown'
            )
            return COLLECTING_NOTIFICATION_DATA
    
    async def collect_telegram_chat_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор Chat ID для Telegram"""
        user_id = update.effective_user.id
        chat_id = update.message.text.strip()
        
        # Простая валидация (должно быть число)
        try:
            int(chat_id)
        except ValueError:
            await update.message.reply_text(
                "❌ Chat ID должен быть числом!\n\n"
                "Введите Chat ID:",
                parse_mode='Markdown'
            )
            return COLLECTING_NOTIFICATION_DATA
        
        data = self.get_user_data(user_id)
        notification_data = {
            'telegram_token': data.get('notification_telegram_token'),
            'telegram_chat_id': chat_id
        }
        self.update_user_data(
            user_id,
            notification_telegram_chat_id=chat_id,
            notification_data=notification_data
        )
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'CONFIRMING', data)
        
        await update.message.reply_text(
            f"✅ Chat ID сохранен: **{chat_id}**\n\n"
            "Переходим к подтверждению...",
            parse_mode='Markdown'
        )
        # Показываем сводку и запрашиваем подтверждение
        await self._show_summary(update, user_id)
        return CONFIRMING
    
    async def _show_summary(self, update, user_id):
        """Показать сводку собранных данных"""
        data = self.get_user_data(user_id)
        
        # Формируем сводку
        summary = "📋 **Сводка данных для лендинга**\n\n"
        summary += f"📦 **Товар:** {data.get('product_name', 'Не указано')}\n"
        summary += f"💰 **Цена:** {data.get('old_price', 'Не указано')} → {data.get('new_price', 'Не указано')}\n"
        
        if data.get('hero_discount'):
            summary += f"🎯 **Скидка:** {data.get('hero_discount')}\n"
        
        summary += "\n✅ Все данные собраны!\n\n"
        summary += "Нажмите кнопку для генерации лендинга:"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Сгенерировать лендинг", callback_data="confirm_generate")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ])
        
        if hasattr(update, 'reply_text'):
            await update.reply_text(summary, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await update.message.reply_text(summary, parse_mode='Markdown', reply_markup=keyboard)

