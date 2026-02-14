"""
Обработчик для сбора информации для подвала лендинга
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from .states import COLLECTING_FOOTER_INFO, COLLECTING_NOTIFICATION_TYPE


class FooterHandler(BaseHandler):
    """Обработчик для сбора информации для подвала"""
    
    async def start_collection(self, update: Update, user_id: int):
        """Начало сбора информации для подвала"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 ИП (Индивидуальный предприниматель)", callback_data="footer_ip")],
            [InlineKeyboardButton("🏢 ЮЛ (Юридическое лицо)", callback_data="footer_ul")]
        ])
        
        text = (
            "📋 **Информация для подвала лендинга**\n\n"
            "Выберите тип организации:\n\n"
            "👤 **ИП** - Индивидуальный предприниматель\n"
            "🏢 **ЮЛ** - Юридическое лицо"
        )
        
        if hasattr(update, 'edit_message_text'):
            await update.edit_message_text(text, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await update.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)
    
    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа организации (ИП/ЮЛ)"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        footer_type = query.data.replace('footer_', '')
        
        self.update_user_data(user_id, footer_info={'type': footer_type})
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
        
        if footer_type == 'ip':
            await query.edit_message_text(
                "👤 **Информация для ИП**\n\n"
                "📝 **ФИО индивидуального предпринимателя**\n\n"
                "Введите ФИО полностью:\n"
                "_Например: Иванов Иван Иванович_",
                parse_mode='Markdown'
            )
        else:  # ul
            await query.edit_message_text(
                "🏢 **Информация для ЮЛ**\n\n"
                "📝 **Название компании**\n\n"
                "Введите полное название юридического лица:\n"
                "_Например: ООО \"Компания\"_",
                parse_mode='Markdown'
            )
        return COLLECTING_FOOTER_INFO
    
    async def collect_footer_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Универсальный обработчик для сбора данных подвала"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        data = self.get_user_data(user_id)
        footer_info = data.get('footer_info', {})
        footer_type = footer_info.get('type')
        
        # Определяем, какое поле ожидается по порядку
        # 1. ФИО/Название компании
        if footer_type and ('fio' not in footer_info and 'company_name' not in footer_info):
            # Собираем ФИО или название компании
            if footer_type == 'ip':
                footer_info['fio'] = text
            else:
                footer_info['company_name'] = text
            
            self.update_user_data(user_id, footer_info=footer_info)
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            
            await update.message.reply_text(
                "✅ Сохранено!\n\n"
                "🔢 **УНП (Учетный номер плательщика)**\n\n"
                "Введите УНП:\n"
                "_Например: 123456789_",
                parse_mode='Markdown'
            )
            return COLLECTING_FOOTER_INFO
        
        # 2. УНП
        elif 'unp' not in footer_info or not footer_info.get('unp'):
            footer_info['unp'] = text
            self.update_user_data(user_id, footer_info=footer_info)
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            
            await update.message.reply_text(
                "✅ УНП сохранено!\n\n"
                "📍 **Адрес**\n\n"
                "Введите адрес ИП/ЮЛ:\n"
                "_Например: г. Минск, ул. Ленина, д. 1, офис 101_",
                parse_mode='Markdown'
            )
            return COLLECTING_FOOTER_INFO
        
        # 3. Адрес
        elif 'address' not in footer_info or not footer_info.get('address'):
            footer_info['address'] = text
            self.update_user_data(user_id, footer_info=footer_info)
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            
            await update.message.reply_text(
                "✅ Адрес сохранен!\n\n"
                "📧 **Email**\n\n"
                "Введите email для связи:\n"
                "_Например: info@example.com_",
                parse_mode='Markdown'
            )
            return COLLECTING_FOOTER_INFO
        
        # 4. Email
        elif 'email' not in footer_info or not footer_info.get('email'):
            # Простая валидация email
            if '@' not in text or '.' not in text:
                await update.message.reply_text(
                    "❌ Неверный формат email!\n\n"
                    "Введите email в формате: example@domain.com",
                    parse_mode='Markdown'
                )
                return COLLECTING_FOOTER_INFO
            
            footer_info['email'] = text
            self.update_user_data(user_id, footer_info=footer_info)
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            
            await update.message.reply_text(
                "✅ Email сохранен!\n\n"
                "📞 **Контактный телефон**\n\n"
                "Введите контактный телефон:\n"
                "_Например: +375 29 123-45-67_",
                parse_mode='Markdown'
            )
            return COLLECTING_FOOTER_INFO
        
        # 5. Телефон
        elif 'phone' not in footer_info or not footer_info.get('phone'):
            footer_info['phone'] = text
            self.update_user_data(user_id, footer_info=footer_info)
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            
            await update.message.reply_text(
                "✅ Телефон сохранен!\n\n"
                "🕐 **Время работы**\n\n"
                "Введите время работы:\n"
                "_Например: Пн-Пт: 9:00-18:00, Сб-Вс: 10:00-16:00_",
                parse_mode='Markdown'
            )
            return COLLECTING_FOOTER_INFO
        
        # 6. Время работы
        else:
            return await self.collect_schedule(update, context)
    
    async def collect_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор ФИО ИП или названия ЮЛ (устаревший метод, используйте collect_footer_data)"""
        return await self.collect_footer_data(update, context)
    
    async def collect_unp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор УНП (устаревший метод, используйте collect_footer_data)"""
        return await self.collect_footer_data(update, context)
    
    async def collect_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор адреса (устаревший метод, используйте collect_footer_data)"""
        return await self.collect_footer_data(update, context)
    
    async def collect_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор email (устаревший метод, используйте collect_footer_data)"""
        return await self.collect_footer_data(update, context)
    
    async def collect_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор телефона (устаревший метод, используйте collect_footer_data)"""
        return await self.collect_footer_data(update, context)
    
    async def collect_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор времени работы"""
        user_id = update.effective_user.id
        schedule = update.message.text.strip()
        
        data = self.get_user_data(user_id)
        footer_info = data.get('footer_info', {})
        footer_info['schedule'] = schedule
        self.update_user_data(user_id, footer_info=footer_info)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_NOTIFICATION_TYPE', data)
        
        await update.message.reply_text(
            "✅ Время работы сохранено!\n\n"
            "✅ **Информация для подвала собрана!**\n\n"
            "Переходим к настройке уведомлений...",
            parse_mode='Markdown'
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📧 Email", callback_data="notif_email")],
            [InlineKeyboardButton("💬 Telegram", callback_data="notif_telegram")]
        ])
        
        await update.message.reply_text(
            "📬 **Тип уведомлений**\n\n"
            "Как получать заявки с лендинга?",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_NOTIFICATION_TYPE

