"""
Обработчик для блока отзывов
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from .states import COLLECTING_REVIEWS_BLOCK, COLLECTING_FOOTER_INFO


class ReviewsHandler(BaseHandler):
    """Обработчик для блока отзывов"""
    
    async def select_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор необходимости блока отзывов"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        reviews_needed = query.data == 'reviews_yes'
        
        if not reviews_needed:
            self.update_user_data(user_id, reviews_block_enabled=False, reviews_type=None, reviews=[])
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            await self._go_to_footer(query, user_id)
            return COLLECTING_FOOTER_INFO
        
        self.update_user_data(user_id, reviews_block_enabled=True)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 С текстом и фото", callback_data="reviews_type_text_photo")],
            [InlineKeyboardButton("🖼️ Только фото (текст на фото)", callback_data="reviews_type_photo_only")],
            [InlineKeyboardButton("📄 Только текст", callback_data="reviews_type_text_only")],
            [InlineKeyboardButton("🤖 Сгенерировать автоматически", callback_data="reviews_type_generated")]
        ])
        
        await query.edit_message_text(
            "⭐ **Тип отзывов**\n\n"
            "Какой тип отзывов использовать?\n\n"
            "📝 **С текстом и фото** - текст отзыва + фото автора\n"
            "🖼️ **Только фото** - текст отзыва на самом фото\n"
            "📄 **Только текст** - только текстовые отзывы\n"
            "🤖 **Сгенерировать** - нейросеть создаст отзывы на основе описания товара",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_REVIEWS_BLOCK
    
    async def select_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор типа отзывов"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        reviews_type = query.data.replace('reviews_type_', '')
        
        self.update_user_data(user_id, reviews_type=reviews_type)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        if reviews_type == 'generated':
            # Сгенерированные отзывы - переходим к подвалу
            await query.edit_message_text(
                "✅ Отзывы будут сгенерированы автоматически на основе описания товара.\n\n"
                "Переходим к информации для подвала...",
                parse_mode='Markdown'
            )
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            await self._go_to_footer(query, user_id)
            return COLLECTING_FOOTER_INFO
        
        # Для остальных типов - спрашиваем соотношение сторон
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("3:4 (Стандартное)", callback_data="reviews_aspect_3_4")],
            [InlineKeyboardButton("9:16 (Вертикальное)", callback_data="reviews_aspect_9_16")]
        ])
        
        await query.edit_message_text(
            "📐 **Соотношение сторон фото отзывов**\n\n"
            "Выберите соотношение сторон для фото отзывов:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_REVIEWS_BLOCK
    
    async def select_aspect_ratio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор соотношения сторон для фото отзывов"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        aspect_key = query.data.replace('reviews_aspect_', '').replace('_', ':')
        
        self.update_user_data(user_id, reviews_aspect_ratio=aspect_key)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        # Спрашиваем формат фото
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("JPEG", callback_data="reviews_format_jpeg")],
            [InlineKeyboardButton("PNG", callback_data="reviews_format_png")],
            [InlineKeyboardButton("SVG", callback_data="reviews_format_svg")]
        ])
        
        await query.edit_message_text(
            f"✅ Соотношение: **{aspect_key}**\n\n"
            "📸 **Формат фото отзывов**\n\n"
            "⚠️ **ВАЖНО:** Укажите точный формат!\n\n"
            "Выберите формат:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return COLLECTING_REVIEWS_BLOCK
    
    async def select_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор формата фото для отзывов"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        format_key = query.data.replace('reviews_format_', '')
        
        self.update_user_data(user_id, reviews_photo_format=format_key)
        data = self.get_user_data(user_id)
        reviews_type = data.get('reviews_type')
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        if reviews_type == 'photo_only':
            # Только фото - сразу загружаем фото
            await query.edit_message_text(
                f"✅ Формат: **{format_key.upper()}**\n\n"
                "🖼️ **Загрузите фото отзывов**\n\n"
                "Отправьте фото отзывов (текст должен быть на самих фото).\n"
                "Каждое фото по одному.\n\n"
                "После загрузки всех фото нажмите кнопку.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Фото загружены", callback_data="reviews_photos_done")
                ]])
            )
        else:
            # С текстом - сначала спрашиваем количество
            await query.edit_message_text(
                f"✅ Формат: **{format_key.upper()}**\n\n"
                "📊 **Сколько отзывов добавить?**\n\n"
                "Введите количество отзывов (рекомендуется 3-5):",
                parse_mode='Markdown'
            )
        return COLLECTING_REVIEWS_BLOCK
    
    async def collect_reviews_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Универсальный обработчик для сбора данных отзывов (количество или текст)"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        data = self.get_user_data(user_id)
        
        # Проверяем, ожидается ли количество отзывов
        if 'reviews_count' not in data or not data.get('reviews_count'):
            # Ожидается количество - пытаемся преобразовать в число
            try:
                count = int(text)
                if count < 1 or count > 10:
                    await update.message.reply_text("⚠️ Введите число от 1 до 10")
                    return COLLECTING_REVIEWS_BLOCK
                
                self.update_user_data(user_id, reviews_count=count)
                data = self.get_user_data(user_id)
                reviews_type = data.get('reviews_type')
                self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
                
                if reviews_type == 'text_only':
                    # Только текст - собираем тексты
                    await update.message.reply_text(
                        f"✅ Количество: **{count}**\n\n"
                        "📝 **Введите отзывы**\n\n"
                        "Введите отзывы. Каждый отзыв на новой строке.\n"
                        "Формат: Имя, Город - Текст отзыва\n\n"
                        "_Например:_\n"
                        "_Анна, Минск - Отличный товар! Очень довольна покупкой._\n"
                        "_Иван, Гродно - Качество на высоте, рекомендую!_",
                        parse_mode='Markdown'
                    )
                else:
                    # С фото - собираем тексты и фото
                    await update.message.reply_text(
                        f"✅ Количество: **{count}**\n\n"
                        "📝 **Введите отзывы**\n\n"
                        "Введите отзывы. Каждый отзыв на новой строке.\n"
                        "Формат: Имя, Город - Текст отзыва\n\n"
                        "_После ввода текстов нужно будет загрузить фото._",
                        parse_mode='Markdown'
                    )
                return COLLECTING_REVIEWS_BLOCK
            except ValueError:
                await update.message.reply_text("❌ Введите число!")
                return COLLECTING_REVIEWS_BLOCK
        else:
            # Ожидается текст отзывов - вызываем collect_text
            return await self.collect_text(update, context)
    
    async def collect_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор количества отзывов (устаревший метод, используйте collect_reviews_data)"""
        return await self.collect_reviews_data(update, context)
    
    async def collect_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор текстов отзывов"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Разделяем по строкам
        reviews_texts = [r.strip() for r in text.split('\n') if r.strip()]
        
        data = self.get_user_data(user_id)
        reviews_count = data.get('reviews_count', len(reviews_texts))
        
        if len(reviews_texts) < reviews_count:
            await update.message.reply_text(
                f"⚠️ Введено только {len(reviews_texts)} отзывов. Нужно {reviews_count}.\n"
                "Добавьте ещё:",
                parse_mode='Markdown'
            )
            return COLLECTING_REVIEWS_BLOCK
        
        # Сохраняем тексты
        reviews = []
        for i, review_text in enumerate(reviews_texts[:reviews_count]):
            # Парсим формат: Имя, Город - Текст
            parts = review_text.split(' - ', 1)
            if len(parts) == 2:
                name_city = parts[0].strip()
                review_text_only = parts[1].strip()
                name_city_parts = name_city.split(',', 1)
                name = name_city_parts[0].strip() if name_city_parts else "Пользователь"
                city = name_city_parts[1].strip() if len(name_city_parts) > 1 else "Беларусь"
            else:
                name = f"Пользователь {i+1}"
                city = "Беларусь"
                review_text_only = review_text
            
            reviews.append({
                'name': name,
                'city': city,
                'text': review_text_only,
                'photo': None
            })
        
        self.update_user_data(user_id, reviews=reviews)
        data = self.get_user_data(user_id)
        reviews_type = data.get('reviews_type')
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        if reviews_type in ['text_photo', 'photo_only']:
            # Нужны фото
            await update.message.reply_text(
                f"✅ Отзывы сохранены: {len(reviews)} шт.\n\n"
                "📸 **Загрузите фото для отзывов**\n\n"
                "Отправьте фото. Каждое фото по одному.\n"
                "После загрузки всех фото нажмите кнопку.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Фото загружены", callback_data="reviews_photos_done")
                ]])
            )
            return COLLECTING_REVIEWS_BLOCK
        else:
            # Только текст - переходим к подвалу
            await update.message.reply_text(
                f"✅ Отзывы сохранены: {len(reviews)} шт.\n\n"
                "Переходим к информации для подвала...",
                parse_mode='Markdown'
            )
            data = self.get_user_data(user_id)
            self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
            await self._go_to_footer(update, user_id)
            return COLLECTING_FOOTER_INFO
    
    async def collect_photos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор фото для отзывов"""
        user_id = update.effective_user.id
        
        if not update.message.photo:
            await update.message.reply_text("❌ Отправьте фото!")
            return COLLECTING_REVIEWS_BLOCK
        
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Проверяем размер файла
        is_valid, error_msg = self.check_file_size(file.file_size, 'фото')
        if not is_valid:
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return COLLECTING_REVIEWS_BLOCK
        
        data = self.get_user_data(user_id)
        photos_dir = data.get('photos_dir')
        reviews = data.get('reviews', [])
        reviews_photo_format = data.get('reviews_photo_format', 'jpeg')
        file_ext = reviews_photo_format if reviews_photo_format != 'jpeg' else 'jpg'
        
        # Находим первый отзыв без фото
        photo_index = None
        for i, review in enumerate(reviews):
            if not review.get('photo'):
                photo_index = i
                break
        
        if photo_index is None:
            # Все фото загружены
            await update.message.reply_text(
                "✅ Все фото загружены! Нажмите кнопку для продолжения.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Фото загружены", callback_data="reviews_photos_done")
                ]])
            )
            return COLLECTING_REVIEWS_BLOCK
        
        photo_path = os.path.join(photos_dir, f'review_{photo_index + 1}.{file_ext}')
        await file.download_to_drive(photo_path)
        
        # Проверяем тип файла
        is_valid, error_msg = self.validate_uploaded_file(photo_path, 'image')
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}")
            return COLLECTING_REVIEWS_BLOCK
        
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
        
        reviews[photo_index]['photo'] = photo_path
        if original_filename:
            reviews[photo_index]['photo_filename'] = original_filename
            self.log('info', f'Extracted filename for review photo {photo_index + 1}: {original_filename}', user_id)
        self.update_user_data(user_id, reviews=reviews)
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_REVIEWS_BLOCK', data)
        
        loaded_count = sum(1 for r in reviews if r.get('photo'))
        total_count = len(reviews)
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Фото загружены", callback_data="reviews_photos_done")
        ]])
        
        await update.message.reply_text(
            f"📷 Фото #{photo_index + 1} сохранено!\n"
            f"Загружено: {loaded_count}/{total_count}\n\n"
            "Отправьте ещё фото или нажмите кнопку.",
            reply_markup=keyboard
        )
        return COLLECTING_REVIEWS_BLOCK
    
    async def photos_done(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Завершение загрузки фото отзывов"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = self.get_user_data(user_id)
        reviews = data.get('reviews', [])
        reviews_type = data.get('reviews_type')
        
        if reviews_type == 'photo_only':
            # Для фото-only проверяем, что все фото загружены
            if not all(r.get('photo') for r in reviews):
                await query.edit_message_text(
                    "⚠️ Не все фото загружены!\n\nОтправьте оставшиеся фото.",
                    parse_mode='Markdown'
                )
                return COLLECTING_REVIEWS_BLOCK
        
        await query.edit_message_text(
            f"✅ Блок отзывов готов: {len(reviews)} отзывов\n\n"
            "Переходим к информации для подвала...",
            parse_mode='Markdown'
        )
        data = self.get_user_data(user_id)
        self.save_state(user_id, 'COLLECTING_FOOTER_INFO', data)
        await self._go_to_footer(query, user_id)
        return COLLECTING_FOOTER_INFO
    
    async def _go_to_footer(self, update, user_id):
        """Переход к сбору информации для подвала"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
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

