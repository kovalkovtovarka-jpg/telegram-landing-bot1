"""
Обработчик для сбора опций формы заказа (размер, цвет, характеристики, количество)
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

from .states import COLLECTING_FORM_OPTIONS, COLLECTING_MIDDLE_BLOCK


class FormHandler(BaseHandler):
    """Обработчик для опций формы заказа"""
    
    async def select_size_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор необходимости размера в форме"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        has_size = query.data == 'form_size_yes'
        
        self.update_user_data(user_id, form_has_sizes=has_size)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_FORM_OPTIONS', data)
        
        if has_size:
            await query.edit_message_text(
                "✅ Размер будет добавлен в форму.\n\n"
                "📏 **Укажите доступные размеры**\n\n"
                "Каждый размер на новой строке.\n"
                "_Например:_\n"
                "_S_\n"
                "_M_\n"
                "_L_",
                parse_mode='Markdown'
            )
            return COLLECTING_FORM_OPTIONS
        else:
            # Спрашиваем про цвет
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор цвета", callback_data="form_color_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_color_no")]
            ])
            await query.edit_message_text(
                "✅ Размер не нужен.\n\n"
                "🎨 **Нужен ли выбор цвета в форме заказа?**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
    
    async def select_color_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор необходимости цвета в форме"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        has_color = query.data == 'form_color_yes'
        
        self.update_user_data(user_id, form_has_colors=has_color)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_FORM_OPTIONS', data)
        
        if has_color:
            await query.edit_message_text(
                "✅ Цвет будет добавлен в форму.\n\n"
                "🎨 **Укажите доступные цвета**\n\n"
                "Каждый цвет на новой строке.\n"
                "_Например:_\n"
                "_Черный_\n"
                "_Белый_\n"
                "_Красный_",
                parse_mode='Markdown'
            )
            return COLLECTING_FORM_OPTIONS
        else:
            # Спрашиваем про характеристики
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор характеристик", callback_data="form_char_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_char_no")]
            ])
            await query.edit_message_text(
                "✅ Цвет не нужен.\n\n"
                "⚙️ **Нужен ли выбор характеристик в форме заказа?**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
    
    async def select_characteristics_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор необходимости характеристик в форме"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        has_char = query.data == 'form_char_yes'
        
        self.update_user_data(user_id, form_has_characteristics=has_char)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_FORM_OPTIONS', data)
        
        if has_char:
            await query.edit_message_text(
                "✅ Характеристики будут добавлены в форму.\n\n"
                "⚙️ **Укажите варианты характеристик**\n\n"
                "Каждая характеристика на новой строке.\n"
                "_Например:_\n"
                "_Стандарт_\n"
                "_Премиум_\n"
                "_Люкс_",
                parse_mode='Markdown'
            )
            return COLLECTING_FORM_OPTIONS
        else:
            # Спрашиваем про количество
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор количества", callback_data="form_quantity_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_quantity_no")]
            ])
            await query.edit_message_text(
                "✅ Характеристики не нужны.\n\n"
                "🔢 **Нужен ли выбор количества в форме заказа?**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
    
    async def select_quantity_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор необходимости количества в форме"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        has_quantity = query.data == 'form_quantity_yes'
        
        self.update_user_data(user_id, form_has_quantity=has_quantity)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_MIDDLE_BLOCK', data)
        
        # Переходим к среднему блоку
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎥 Видео", callback_data="middle_video")],
            [InlineKeyboardButton("📸 Галерея", callback_data="middle_gallery")],
            [InlineKeyboardButton("📝 Описание", callback_data="middle_description")]
        ])
        
        await query.edit_message_text(
            "✅ Опции формы сохранены!\n\n"
            "📋 **Средний блок лендинга**\n\n"
            "Что будет в среднем блоке?\n\n"
            "🎥 **Видео** - видео товара\n"
            "📸 **Галерея** - карусель фото (2-7 фото)\n"
            "📝 **Описание** - сразу перейти к описанию",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_MIDDLE_BLOCK
    
    async def collect_form_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Универсальный обработчик для сбора данных формы (размеры, цвета, характеристики)"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        data = self.get_user_data(user_id)
        
        # Определяем, какое поле ожидается
        # Проверяем по порядку: размеры -> цвета -> характеристики
        
        # Если ожидаются размеры
        if data.get('form_has_sizes') and ('sizes' not in data or not data.get('sizes')):
            sizes = [s.strip() for s in text.split('\n') if s.strip()]
            self.update_user_data(user_id, sizes=sizes)
            self.log('info', f'Entered sizes: {sizes}', user_id)
            
            # Спрашиваем про цвет
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор цвета", callback_data="form_color_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_color_no")]
            ])
            await update.message.reply_text(
                "✅ Размеры сохранены!\n\n"
                "🎨 **Нужен ли выбор цвета в форме заказа?**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
        
        # Если ожидаются цвета
        elif data.get('form_has_colors') and ('colors' not in data or not data.get('colors')):
            colors = [c.strip() for c in text.split('\n') if c.strip()]
            self.update_user_data(user_id, colors=colors)
            self.log('info', f'Entered colors: {colors}', user_id)
            
            # Спрашиваем про характеристики
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор характеристик", callback_data="form_char_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_char_no")]
            ])
            await update.message.reply_text(
                "✅ Цвета сохранены!\n\n"
                "⚙️ **Нужен ли выбор характеристик в форме заказа?**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
        
        # Если ожидаются характеристики
        elif data.get('form_has_characteristics') and ('characteristics_list' not in data or not data.get('characteristics_list')):
            characteristics_list = [c.strip() for c in text.split('\n') if c.strip()]
            self.update_user_data(user_id, characteristics_list=characteristics_list)
            self.log('info', f'Entered characteristics: {characteristics_list}', user_id)
            
            # Спрашиваем про количество
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен выбор количества", callback_data="form_quantity_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="form_quantity_no")]
            ])
            await update.message.reply_text(
                "✅ Характеристики сохранены!\n\n"
                "🔢 **Нужен ли выбор количества в форме заказа?**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_FORM_OPTIONS
        
        # Если все данные собраны, переходим к среднему блоку
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎥 Видео", callback_data="middle_video")],
                [InlineKeyboardButton("📸 Галерея", callback_data="middle_gallery")],
                [InlineKeyboardButton("📝 Описание", callback_data="middle_description")]
            ])
            await update.message.reply_text(
                "✅ Опции формы сохранены!\n\n"
                "📋 **Средний блок лендинга**\n\n"
                "Что будет в среднем блоке?\n\n"
                "🎥 **Видео** - видео товара\n"
                "📸 **Галерея** - карусель фото (2-7 фото)\n"
                "📝 **Описание** - сразу перейти к описанию",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_MIDDLE_BLOCK
    
    async def collect_sizes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор размеров для формы (устаревший метод, используйте collect_form_data)"""
        return await self.collect_form_data(update, context)
    
    async def collect_colors(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор цветов для формы (устаревший метод, используйте collect_form_data)"""
        return await self.collect_form_data(update, context)
    
    async def collect_characteristics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор характеристик для формы (устаревший метод, используйте collect_form_data)"""
        return await self.collect_form_data(update, context)

