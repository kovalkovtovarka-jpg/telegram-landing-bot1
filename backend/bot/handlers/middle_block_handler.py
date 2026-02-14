"""
Обработчик для среднего блока (видео, галерея, описание)
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from .states import COLLECTING_MIDDLE_BLOCK, COLLECTING_DESCRIPTION


class MiddleBlockHandler(BaseHandler):
    """Обработчик для среднего блока"""
    
    async def select_block_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа среднего блока"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        block_type = query.data.replace('middle_', '')
        
        self.update_user_data(user_id, middle_block_type=block_type)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_MIDDLE_BLOCK', data)
        
        if block_type == 'video':
            # Выбор формата видео
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("MP4", callback_data="middle_video_format_mp4")],
                [InlineKeyboardButton("MOV", callback_data="middle_video_format_mov")],
                [InlineKeyboardButton("AVI", callback_data="middle_video_format_avi")],
                [InlineKeyboardButton("WEBM", callback_data="middle_video_format_webm")]
            ])
            await query.edit_message_text(
                "🎥 **Формат видео**\n\n"
                "⚠️ **ВАЖНО:** Укажите точный формат!\n\n"
                "Выберите формат:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_MIDDLE_BLOCK
        elif block_type == 'gallery':
            await query.edit_message_text(
                "📸 **Галерея фото**\n\n"
                "Отправьте от 2 до 7 фотографий.\n"
                "Большее количество перегрузит лендинг.\n\n"
                "Отправьте первое фото:",
                parse_mode='Markdown'
            )
            return COLLECTING_MIDDLE_BLOCK
        else:  # description
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_DESCRIPTION', data)
            await query.edit_message_text(
                "📝 **Описание товара**\n\n"
                "Напишите подробное описание товара.\n"
                "Можно вставить текст с Wildberries - он будет обработан.\n\n"
                "Отправьте описание:",
                parse_mode='Markdown'
            )
            return COLLECTING_DESCRIPTION
    
    async def select_video_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор формата видео для среднего блока"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        format_key = query.data.replace('middle_video_format_', '')
        
        self.update_user_data(user_id, middle_video_format=format_key)
        
        # Выбор соотношения сторон
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("3:4 (Стандартное)", callback_data="middle_aspect_3_4")],
            [InlineKeyboardButton("9:16 (Вертикальное)", callback_data="middle_aspect_9_16")],
            [InlineKeyboardButton("Другое", callback_data="middle_aspect_custom")]
        ])
        
        await query.edit_message_text(
            f"✅ Формат: **{format_key.upper()}**\n\n"
            "📐 **Соотношение сторон**\n\n"
            "Выберите соотношение:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_MIDDLE_BLOCK
    
    async def select_aspect_ratio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор соотношения сторон для видео"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        aspect_key = query.data.replace('middle_aspect_', '').replace('_', ':')
        
        if aspect_key == 'custom':
            await query.edit_message_text(
                "📐 **Укажите своё соотношение сторон**\n\n"
                "Например: 16:9, 4:3, 1:1\n\n"
                "Введите в формате: ШИРИНА:ВЫСОТА",
                parse_mode='Markdown'
            )
            return COLLECTING_MIDDLE_BLOCK
        
        self.update_user_data(user_id, middle_aspect_ratio=aspect_key)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_MIDDLE_BLOCK', data)
        
        await query.edit_message_text(
            f"✅ Соотношение: **{aspect_key}**\n\n"
            "🎥 **Загрузите видео**\n\n"
            "Отправьте видео товара.\n"
            "Видео будет автоматически воспроизводиться при попадании в поле зрения.",
            parse_mode='Markdown'
        )
        return COLLECTING_MIDDLE_BLOCK
    
    async def collect_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор видео для среднего блока"""
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        
        if not update.message.video:
            await update.message.reply_text("❌ Отправьте видео!")
            return COLLECTING_MIDDLE_BLOCK
        
        video = update.message.video
        file = await context.bot.get_file(video.file_id)
        
        # Проверяем размер файла
        is_valid, error_msg = self.check_file_size(file.file_size, 'видео')
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return COLLECTING_MIDDLE_BLOCK
        
        videos_dir = data.get('videos_dir')
        format_key = data.get('middle_video_format', 'mp4')
        
        video_path = os.path.join(videos_dir, f'middle.{format_key}')
        await file.download_to_drive(video_path)
        
        # Проверяем тип файла
        is_valid, error_msg = self.validate_uploaded_file(video_path, 'video')
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return COLLECTING_MIDDLE_BLOCK
        
        self.update_user_data(user_id, middle_video=video_path)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_DESCRIPTION', data)
        
        await update.message.reply_text(
            "✅ Видео загружено!\n\n"
            "📝 **Описание товара**\n\n"
            "Напишите подробное описание товара.\n"
            "Можно вставить текст с Wildberries - он будет обработан.\n\n"
            "Отправьте описание:",
            parse_mode='Markdown'
        )
        return COLLECTING_DESCRIPTION
    
    async def collect_gallery(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор галереи фото"""
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        
        if not update.message.photo:
            await update.message.reply_text("❌ Отправьте фото!")
            return COLLECTING_MIDDLE_BLOCK
        
        gallery = data.get('middle_gallery', [])
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Проверяем размер файла
        is_valid, error_msg = self.check_file_size(file.file_size, 'фото')
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return COLLECTING_MIDDLE_BLOCK
        
        photos_dir = data.get('photos_dir')
        format_key = data.get('middle_gallery_format', 'jpeg')
        file_ext = format_key if format_key != 'jpeg' else 'jpg'
        
        photo_path = os.path.join(photos_dir, f'gallery_{len(gallery) + 1}.{file_ext}')
        await file.download_to_drive(photo_path)
        
        # Проверяем тип файла
        is_valid, error_msg = self.validate_uploaded_file(photo_path, 'image')
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return COLLECTING_MIDDLE_BLOCK
        
        # Получаем оригинальное имя файла из подписи к фото
        original_filename = None
        if update.message.caption:
            # Имя файла может быть указано в подписи к фото
            caption_text = update.message.caption.strip()
            # Пробуем извлечь имя файла (может быть с расширением или без)
            if '.' in caption_text:
                original_filename = os.path.splitext(caption_text)[0]
            else:
                original_filename = caption_text
            # Очищаем от лишних символов
            original_filename = original_filename.strip().replace('/', '_').replace('\\', '_')
        
        photo_info = {'path': photo_path}
        if original_filename:
            photo_info['filename'] = original_filename
            self.log('info', f'Extracted filename for gallery photo {len(gallery) + 1}: {original_filename}', user_id)
        gallery.append(photo_info)
        self.update_user_data(user_id, middle_gallery=gallery)
        
        if len(gallery) < 2:
            await update.message.reply_text(
                f"✅ Фото {len(gallery)}/7 загружено.\n\n"
                "Отправьте следующее фото (минимум 2, максимум 7):",
                parse_mode='Markdown'
            )
            return COLLECTING_MIDDLE_BLOCK
        elif len(gallery) < 7:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Готово", callback_data="gallery_done")]
            ])
            await update.message.reply_text(
                f"✅ Фото {len(gallery)}/7 загружено.\n\n"
                "Можно добавить ещё фото или завершить загрузку.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_MIDDLE_BLOCK
        else:
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_DESCRIPTION', data)
            await update.message.reply_text(
                "✅ Галерея загружена (максимум 7 фото)!\n\n"
                "📝 **Описание товара**\n\n"
                "Напишите подробное описание товара.\n"
                "Можно вставить текст с Wildberries - он будет обработан.\n\n"
                "Отправьте описание:",
                parse_mode='Markdown'
            )
            return COLLECTING_DESCRIPTION
    
    async def gallery_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение загрузки галереи"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_DESCRIPTION', data)
        
        await query.edit_message_text(
            "✅ Галерея сохранена!\n\n"
            "📝 **Описание товара**\n\n"
            "Напишите подробное описание товара.\n"
            "Можно вставить текст с Wildberries - он будет обработан.\n\n"
            "Отправьте описание:",
            parse_mode='Markdown'
        )
        return COLLECTING_DESCRIPTION

