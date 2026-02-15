"""
Обработчик для Hero блока (фото/видео, формат, соотношение сторон, скидка)
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

from .states import COLLECTING_HERO_MEDIA, COLLECTING_HERO_DISCOUNT, COLLECTING_CHARACTERISTICS


class HeroHandler(BaseHandler):
    """Обработчик для Hero блока"""
    
    async def select_media_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа медиа для hero блока (фото или видео)"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        media_type = query.data.replace('hero_', '')  # 'photo' или 'video'
        
        self.update_user_data(user_id, hero_media_type=media_type)
        self.log('info', f'Selected hero media type: {media_type}', user_id)
        
        if media_type == 'photo':
            # Выбор формата фото
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("JPEG", callback_data="format_jpeg")],
                [InlineKeyboardButton("PNG", callback_data="format_png")],
                [InlineKeyboardButton("SVG", callback_data="format_svg")]
            ])
            
            await query.edit_message_text(
                "📸 **Формат фото для hero блока**\n\n"
                "⚠️ **ВАЖНО:** Укажите точный формат, иначе фото не отобразится!\n\n"
                "Выберите формат:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:  # video
            # Выбор формата видео
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("MP4", callback_data="format_mp4")],
                [InlineKeyboardButton("MOV", callback_data="format_mov")],
                [InlineKeyboardButton("AVI", callback_data="format_avi")],
                [InlineKeyboardButton("WEBM", callback_data="format_webm")]
            ])
            
            await query.edit_message_text(
                "🎥 **Формат видео для hero блока**\n\n"
                "⚠️ **ВАЖНО:** Укажите точный формат, иначе видео не отобразится!\n\n"
                "Выберите формат:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        return COLLECTING_HERO_MEDIA
    
    async def select_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор формата файла для hero блока"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        format_key = query.data.replace('format_', '')
        
        data = self.get_user_data(user_id)
        
        # Сохраняем формат
        self.update_user_data(user_id, hero_media_format=format_key)
        
        # Выбор соотношения сторон
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("3:4 (Стандартное)", callback_data="aspect_3_4")],
            [InlineKeyboardButton("9:16 (Вертикальное)", callback_data="aspect_9_16")],
            [InlineKeyboardButton("Другое", callback_data="aspect_custom")]
        ])
        
        await query.edit_message_text(
            f"✅ Формат: **{format_key.upper()}**\n\n"
            "📐 **Соотношение сторон**\n\n"
            "Выберите соотношение сторон:\n\n"
            "3:4 - стандартное соотношение\n"
            "9:16 - вертикальное (как в телефоне)\n"
            "Другое - укажите своё",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_HERO_MEDIA
    
    async def select_aspect_ratio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор соотношения сторон для hero блока"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        aspect_key = query.data.replace('aspect_', '').replace('_', ':')
        
        if aspect_key == 'custom':
            await query.edit_message_text(
                "📐 **Укажите своё соотношение сторон**\n\n"
                "Например: 16:9, 4:3, 1:1\n\n"
                "Введите в формате: ШИРИНА:ВЫСОТА",
                parse_mode='Markdown'
            )
            return COLLECTING_HERO_MEDIA
        
        self.update_user_data(user_id, hero_aspect_ratio=aspect_key)
        
        # Спрашиваем про скидку
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Есть скидка", callback_data="discount_yes")],
            [InlineKeyboardButton("❌ Нет скидки", callback_data="discount_no")]
        ])
        
        await query.edit_message_text(
            f"✅ Соотношение: **{aspect_key}**\n\n"
            "💰 **Есть ли скидка на товар?**\n\n"
            "Если есть скидка, она будет отображаться в углу hero фото/видео.",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_HERO_DISCOUNT
    
    async def collect_custom_aspect_ratio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор кастомного соотношения сторон"""
        user_id = update.effective_user.id
        aspect_text = update.message.text.strip()
        
        # Валидация формата
        if ':' not in aspect_text:
            await update.message.reply_text(
                "❌ Неверный формат. Используйте: ШИРИНА:ВЫСОТА\n"
                "_Например: 16:9_",
                parse_mode='Markdown'
            )
            return COLLECTING_HERO_MEDIA
        
        self.update_user_data(user_id, hero_aspect_ratio=aspect_text)
        
        # Спрашиваем про скидку
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Есть скидка", callback_data="discount_yes")],
            [InlineKeyboardButton("❌ Нет скидки", callback_data="discount_no")]
        ])
        
        await update.message.reply_text(
            f"✅ Соотношение: **{aspect_text}**\n\n"
            "💰 **Есть ли скидка на товар?**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_HERO_DISCOUNT
    
    async def select_discount_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора наличия скидки"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        has_discount = query.data == 'discount_yes'
        
        if not has_discount:
            self.update_user_data(user_id, hero_discount=None, hero_discount_position=None)
            # Переходим к загрузке медиа
            data = self.get_user_data(user_id)
            media_type = data.get('hero_media_type')
            
            if media_type == 'photo':
                await query.edit_message_text(
                    "📸 **Загрузите фото для hero блока**\n\n"
                    "Отправьте фото товара.",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "🎥 **Загрузите видео для hero блока**\n\n"
                    "Отправьте видео товара.",
                    parse_mode='Markdown'
                )
            return COLLECTING_HERO_MEDIA
        
        # Если есть скидка - спрашиваем позицию
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Левый верхний", callback_data="discount_pos_top_left")],
            [InlineKeyboardButton("Правый верхний", callback_data="discount_pos_top_right")],
            [InlineKeyboardButton("Левый нижний", callback_data="discount_pos_bottom_left")],
            [InlineKeyboardButton("Правый нижний", callback_data="discount_pos_bottom_right")]
        ])
        
        await query.edit_message_text(
            "💰 **Позиция скидки на фото/видео**\n\n"
            "В каком углу отображать скидку?",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_HERO_DISCOUNT
    
    async def select_discount_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор позиции скидки"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        position = query.data.replace('discount_pos_', '')
        
        # Маппинг позиций на русский язык
        position_names = {
            'top_left': 'Левый верхний',
            'top_right': 'Правый верхний',
            'bottom_left': 'Левый нижний',
            'bottom_right': 'Правый нижний'
        }
        position_name = position_names.get(position, position)
        
        # Обновляем данные
        self.update_user_data(user_id, hero_discount_position=position)
        
        # ВАЖНО: Сохраняем состояние в БД
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_HERO_DISCOUNT', data)
        
        self.log('info', f'Selected discount position: {position} ({position_name})', user_id)
        
        await query.edit_message_text(
            f"✅ Позиция: **{position_name}**\n\n"
            "💰 **Укажите размер скидки**\n\n"
            "Например: 30%, 50%, -30%",
            parse_mode='Markdown'
        )
        return COLLECTING_HERO_DISCOUNT
    
    async def collect_discount_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор значения скидки"""
        user_id = update.effective_user.id
        discount = update.message.text.strip()
        
        # Обновляем данные
        self.update_user_data(user_id, hero_discount=discount)
        
        self.log('info', f'Entered discount value: {discount}', user_id)
        
        # Переходим к загрузке медиа
        data = self.get_user_data(user_id)
        media_type = data.get('hero_media_type')
        
        # Сохраняем состояние для загрузки медиа
        self.save_state(user_id, 'COLLECTING_HERO_MEDIA', data)
        
        if media_type == 'photo':
            await update.message.reply_text(
                "📸 **Загрузите фото для hero блока**\n\n"
                "Отправьте фото товара.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🎥 **Загрузите видео для hero блока**\n\n"
                "Отправьте видео товара.",
                parse_mode='Markdown'
            )
        return COLLECTING_HERO_MEDIA
    
    async def collect_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор фото/видео для hero блока"""
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        media_type = data.get('hero_media_type')
        
        if media_type == 'photo':
            # Обработка фото
            if not update.message.photo:
                await update.message.reply_text("❌ Отправьте фото!")
                return COLLECTING_HERO_MEDIA
            
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            
            # Проверяем размер файла
            is_valid, error_msg = self.check_file_size(file.file_size, 'фото')
            if not is_valid:
                await update.message.reply_text(error_msg, parse_mode='Markdown')
                return COLLECTING_HERO_MEDIA
            
            # Получаем оригинальное имя файла из подписи к фото
            original_filename = None
            if update.message.caption:
                # Имя файла может быть указано в подписи к фото
                caption_text = update.message.caption.strip()
                # Пробуем извлечь имя файла (может быть с расширением или без)
                # Убираем расширение, если есть
                if '.' in caption_text:
                    original_filename = os.path.splitext(caption_text)[0]
                else:
                    original_filename = caption_text
                # Очищаем от лишних символов
                original_filename = original_filename.strip().replace('/', '_').replace('\\', '_')
            
            photos_dir = data.get('photos_dir')
            format_key = data.get('hero_media_format', 'jpeg')
            file_ext = format_key if format_key != 'jpeg' else 'jpg'
            
            hero_path = os.path.join(photos_dir, f'hero.{file_ext}')
            await file.download_to_drive(hero_path)
            
            # Проверяем тип файла
            is_valid, error_msg = self.validate_uploaded_file(hero_path, 'image')
            if not is_valid:
                await update.message.reply_text(f"❌ {error_msg}")
                return COLLECTING_HERO_MEDIA
            
            # Сохраняем оригинальное имя файла (будет использовано в промпте и HTML)
            self.update_user_data(user_id, hero_media=hero_path, hero_media_filename=original_filename)
            
            if original_filename:
                self.log('info', f'Extracted filename for hero media: {original_filename}', user_id)
            self.log('info', f'Uploaded hero photo: {hero_path}', user_id)
            
        else:  # video
            # Обработка видео
            if not update.message.video:
                await update.message.reply_text("❌ Отправьте видео!")
                return COLLECTING_HERO_MEDIA
            
            video = update.message.video
            file = await context.bot.get_file(video.file_id)
            
            videos_dir = data.get('videos_dir')
            format_key = data.get('hero_media_format', 'mp4')
            
            hero_path = os.path.join(videos_dir, f'hero.{format_key}')
            await file.download_to_drive(hero_path)
            
            # Проверяем тип файла
            is_valid, error_msg = self.validate_uploaded_file(hero_path, 'video')
            if not is_valid:
                await update.message.reply_text(f"❌ {error_msg}")
                return COLLECTING_HERO_MEDIA
            
            self.update_user_data(user_id, hero_media=hero_path)
            self.log('info', f'Uploaded hero video: {hero_path}', user_id)
        
        # Сохраняем состояние перед переходом к характеристикам
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_CHARACTERISTICS', data)
        
        # Переходим к сбору 3 характеристик (пункт 3 структуры)
        await update.message.reply_text(
            "✅ Hero медиа загружено!\n\n"
            "✨ **3 яркие характеристики товара**\n\n"
            "Укажите 3 главные характеристики или преимущества.\n"
            "Каждое на новой строке.\n\n"
            "_Например:_\n"
            "_Эффект памяти_\n"
            "_Анатомическая форма_\n"
            "_Гипоаллергенные материалы_",
            parse_mode='Markdown'
        )
        return COLLECTING_CHARACTERISTICS

