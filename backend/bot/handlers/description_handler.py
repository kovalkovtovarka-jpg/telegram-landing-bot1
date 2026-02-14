"""
Обработчик для сбора описания товара
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from .states import COLLECTING_DESCRIPTION, COLLECTING_REVIEWS_BLOCK
from backend.utils.text_processor import TextProcessor


class DescriptionHandler(BaseHandler):
    """Обработчик для сбора описания товара"""
    
    async def collect_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор описания товара"""
        user_id = update.effective_user.id
        description_text = update.message.text.strip()
        
        # Проверяем и обрабатываем текст с Wildberries
        processed_text, is_wildberries = TextProcessor.process_description(description_text)
        
        data = self.get_user_data(user_id)
        description_photos = data.get('description_photos', [])
        
        # Сохраняем текст описания (обработанный) и флаг Wildberries
        self.update_user_data(
            user_id,
            description_text=processed_text,
            description_is_wildberries=is_wildberries,
            description_original=description_text  # Сохраняем оригинал на случай
        )
        
        # Если фото еще не загружены - предлагаем загрузить
        if not description_photos:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Пропустить фото", callback_data="description_photos_skip")
            ]])
            await update.message.reply_text(
                "✅ Описание сохранено!\n\n"
                "📸 **Фото для описания** (опционально, до 4 штук)\n\n"
                "Отправьте фото для описания или нажмите кнопку для пропуска.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_DESCRIPTION
        else:
            # Фото уже есть - переходим к отзывам
            await update.message.reply_text(
                "✅ Описание сохранено!\n\n"
                "Переходим к блоку отзывов...",
                parse_mode='Markdown'
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен блок отзывов", callback_data="reviews_yes")],
                [InlineKeyboardButton("❌ Нет, пропустить", callback_data="reviews_no")]
            ])
            await update.message.reply_text(
                "⭐ **Блок отзывов**\n\n"
                "Нужен ли блок отзывов на лендинге?",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_REVIEWS_BLOCK
    
    async def collect_photos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор фото для описания"""
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        
        if not update.message.photo:
            await update.message.reply_text("❌ Отправьте фото!")
            return COLLECTING_DESCRIPTION
        
        description_photos = data.get('description_photos', [])
        
        if len(description_photos) >= 4:
            await update.message.reply_text(
                "⚠️ Максимум 4 фото для описания. Переходим к отзывам...",
                parse_mode='Markdown'
            )
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен блок отзывов", callback_data="reviews_yes")],
                [InlineKeyboardButton("❌ Нет, пропустить", callback_data="reviews_no")]
            ])
            await update.message.reply_text(
                "⭐ **Блок отзывов**\n\n"
                "Нужен ли блок отзывов на лендинге?",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_REVIEWS_BLOCK
        
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Проверяем размер файла
        is_valid, error_msg = self.check_file_size(file.file_size, 'фото')
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return COLLECTING_DESCRIPTION
        
        photos_dir = data.get('photos_dir')
        format_key = data.get('description_photo_format', 'jpeg')
        file_ext = format_key if format_key != 'jpeg' else 'jpg'
        
        photo_path = os.path.join(photos_dir, f'description_{len(description_photos) + 1}.{file_ext}')
        await file.download_to_drive(photo_path)
        
        # Проверяем тип файла
        is_valid, error_msg = self.validate_uploaded_file(photo_path, 'image')
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return COLLECTING_DESCRIPTION
        
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
            self.log('info', f'Extracted filename for description photo {len(description_photos) + 1}: {original_filename}', user_id)
        description_photos.append(photo_info)
        self.update_user_data(user_id, description_photos=description_photos)
        
        if len(description_photos) < 4:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Готово", callback_data="description_photos_done")
            ]])
            await update.message.reply_text(
                f"✅ Фото {len(description_photos)}/4 загружено.\n\n"
                "Можно добавить ещё фото или завершить.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_DESCRIPTION
        else:
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Да, нужен блок отзывов", callback_data="reviews_yes")],
                [InlineKeyboardButton("❌ Нет, пропустить", callback_data="reviews_no")]
            ])
            await update.message.reply_text(
                "✅ Фото для описания загружены (максимум 4)!\n\n"
                "⭐ **Блок отзывов**\n\n"
                "Нужен ли блок отзывов на лендинге?",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return COLLECTING_REVIEWS_BLOCK
    
    async def photos_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение загрузки фото описания"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, нужен блок отзывов", callback_data="reviews_yes")],
            [InlineKeyboardButton("❌ Нет, пропустить", callback_data="reviews_no")]
        ])
        await query.edit_message_text(
            "✅ Фото для описания сохранены!\n\n"
            "⭐ **Блок отзывов**\n\n"
            "Нужен ли блок отзывов на лендинге?",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_REVIEWS_BLOCK
    
    async def photos_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропуск загрузки фото описания"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, нужен блок отзывов", callback_data="reviews_yes")],
            [InlineKeyboardButton("❌ Нет, пропустить", callback_data="reviews_no")]
        ])
        await query.edit_message_text(
            "✅ Описание сохранено!\n\n"
            "⭐ **Блок отзывов**\n\n"
            "Нужен ли блок отзывов на лендинге?",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_REVIEWS_BLOCK

