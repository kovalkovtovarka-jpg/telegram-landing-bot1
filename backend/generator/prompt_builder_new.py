"""
Новый промпт-билдер для структуры из 17 пунктов (для товарщиков)
"""
from typing import Dict, Any

class NewPromptBuilder:
    """Промпт-билдер для новой структуры лендинга из 17 пунктов"""
    
    def _analyze_product_and_suggest_style(self, product_name: str, description: str = '') -> Dict[str, Any]:
        """
        Анализирует товар и предлагает цветовую схему и стиль на основе названия и описания
        
        Args:
            product_name: Название товара
            description: Описание товара
            
        Returns:
            Словарь с предложенными цветами и стилями
        """
        text = (product_name + ' ' + description).lower()
        
        # Определяем категорию товара
        categories = {
            'health': ['подушка', 'ортопедическ', 'здоров', 'сон', 'матрас', 'кровать', 'спальн'],
            'beauty': ['крем', 'маска', 'косметик', 'красот', 'уход', 'шампунь'],
            'tech': ['телефон', 'смартфон', 'планшет', 'ноутбук', 'компьютер', 'гаджет'],
            'fashion': ['одежд', 'обув', 'сумк', 'аксессуар', 'мод'],
            'home': ['мебель', 'декор', 'интерьер', 'дом', 'квартир'],
            'sports': ['спорт', 'фитнес', 'тренировк', 'кроссовк', 'спортивн'],
            'food': ['еда', 'продукт', 'питани', 'кухн', 'рецепт']
        }
        
        category = 'general'
        for cat, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                category = cat
                break
        
        # Подбираем цветовую схему на основе категории
        color_schemes = {
            'health': {
                'primary': '#4f46e5',  # Индиго (спокойствие, здоровье)
                'secondary': '#10b981',  # Зеленый (здоровье, природа)
                'accent': '#06b6d4',  # Циан
                'bg_dark': '#0f172a',  # Темно-синий
                'bg_darker': '#020617'
            },
            'beauty': {
                'primary': '#ec4899',  # Розовый
                'secondary': '#f472b6',  # Светло-розовый
                'accent': '#a855f7',  # Фиолетовый
                'bg_dark': '#1e1b4b',  # Темно-фиолетовый
                'bg_darker': '#0f0b2e'
            },
            'tech': {
                'primary': '#3b82f6',  # Синий
                'secondary': '#8b5cf6',  # Фиолетовый
                'accent': '#06b6d4',  # Циан
                'bg_dark': '#0f172a',  # Темно-синий
                'bg_darker': '#020617'
            },
            'fashion': {
                'primary': '#f59e0b',  # Оранжевый
                'secondary': '#ef4444',  # Красный
                'accent': '#ec4899',  # Розовый
                'bg_dark': '#1c1917',  # Темно-коричневый
                'bg_darker': '#0c0a09'
            },
            'home': {
                'primary': '#f97316',  # Оранжевый
                'secondary': '#eab308',  # Желтый
                'accent': '#84cc16',  # Лайм
                'bg_dark': '#1c1917',  # Темно-коричневый
                'bg_darker': '#0c0a09'
            },
            'sports': {
                'primary': '#ef4444',  # Красный
                'secondary': '#f59e0b',  # Оранжевый
                'accent': '#10b981',  # Зеленый
                'bg_dark': '#1e293b',  # Темно-серый
                'bg_darker': '#0f172a'
            },
            'food': {
                'primary': '#f59e0b',  # Оранжевый
                'secondary': '#ef4444',  # Красный
                'accent': '#eab308',  # Желтый
                'bg_dark': '#1c1917',  # Темно-коричневый
                'bg_darker': '#0c0a09'
            },
            'general': {
                'primary': '#ff6b9d',  # Розовый
                'secondary': '#c084fc',  # Фиолетовый
                'accent': '#f97316',  # Оранжевый
                'bg_dark': '#0a0e27',  # Темно-синий
                'bg_darker': '#050715'
            }
        }
        
        colors = color_schemes.get(category, color_schemes['general'])
        
        # Подбираем шрифты
        fonts = {
            'health': ('Inter', 'Montserrat'),
            'beauty': ('Playfair Display', 'Poppins'),
            'tech': ('Roboto', 'Inter'),
            'fashion': ('Playfair Display', 'Lato'),
            'home': ('Merriweather', 'Open Sans'),
            'sports': ('Oswald', 'Roboto'),
            'food': ('Poppins', 'Roboto'),
            'general': ('Montserrat', 'Inter')
        }
        
        font_pair = fonts.get(category, fonts['general'])
        
        return {
            'category': category,
            'colors': colors,
            'fonts': font_pair,
            'style': 'modern' if category in ['tech', 'fashion', 'sports'] else 'elegant'
        }
    
    def _get_format_variations(self, media_type: str, format_key: str) -> str:
        """Получить вариации формата для промпта"""
        variations = {
            'photo': {
                'jpeg': 'jpg, jpeg, JPEG, JPG',
                'png': 'png, PNG',
                'svg': 'svg, SVG'
            },
            'video': {
                'mp4': 'mp4, MP4',
                'mov': 'mov, MOV',
                'avi': 'avi, AVI',
                'webm': 'webm, WEBM'
            }
        }
        return variations.get(media_type, {}).get(format_key, format_key)
    
    def build_prompt(self, user_data: Dict[str, Any]) -> str:
        """
        Построение промпта для новой структуры лендинга
        
        Args:
            user_data: Данные пользователя (собранные по новой структуре)
            
        Returns:
            Готовый промпт для LLM
        """
        # Извлекаем все данные
        product_name = user_data.get('product_name', 'Товар')
        description_text = user_data.get('description_text', '')
        
        # Анализируем товар и подбираем стиль
        style_suggestion = self._analyze_product_and_suggest_style(product_name, description_text)
        suggested_colors = style_suggestion['colors']
        suggested_fonts = style_suggestion['fonts']
        suggested_style = style_suggestion['style']
        
        hero_media_filename = user_data.get('hero_media_filename')  # Оригинальное имя файла
        hero_media_type = user_data.get('hero_media_type', 'photo')
        hero_media_format = user_data.get('hero_media_format', 'jpeg')
        hero_aspect_ratio = user_data.get('hero_aspect_ratio', '3:4')
        hero_discount = user_data.get('hero_discount')
        hero_discount_position = user_data.get('hero_discount_position')
        characteristics = user_data.get('characteristics', [])
        timer_enabled = user_data.get('timer_enabled', False)
        timer_type = user_data.get('timer_type')
        timer_date = user_data.get('timer_date')
        old_price = user_data.get('old_price', '')
        new_price = user_data.get('new_price', '')
        sizes = user_data.get('sizes', [])
        colors = user_data.get('colors', [])
        characteristics_list = user_data.get('characteristics_list', [])
        middle_block_type = user_data.get('middle_block_type')
        middle_video = user_data.get('middle_video')
        middle_gallery = user_data.get('middle_gallery', [])
        description_text = user_data.get('description_text', '')
        description_photos = user_data.get('description_photos', [])
        description_is_wildberries = user_data.get('description_is_wildberries', False)
        reviews = user_data.get('reviews', [])
        reviews_type = user_data.get('reviews_type')
        footer_info = user_data.get('footer_info', {})
        
        # Формируем промпт
        prompt = f"""═══════════════════════════════════════════════════════════════
ЗАДАЧА: Создать ПРОДАЮЩИЙ, ПРОФЕССИОНАЛЬНЫЙ лендинг для перепродажи товара
═══════════════════════════════════════════════════════════════

🎨 ДИЗАЙН И СТИЛИ (ОБЯЗАТЕЛЬНО ИСПОЛЬЗОВАТЬ!):
Товар: "{product_name}"
Категория: {style_suggestion['category']}
Стиль: {suggested_style}

ЦВЕТОВАЯ СХЕМА (ОБЯЗАТЕЛЬНО использовать эти цвета в CSS!):
- Primary: {suggested_colors['primary']} (основной акцент)
- Secondary: {suggested_colors['secondary']} (вторичный акцент)
- Accent: {suggested_colors['accent']} (дополнительный акцент)
- Dark BG: {suggested_colors['bg_dark']} (темный фон)
- Darker BG: {suggested_colors['bg_darker']} (еще более темный фон)
"""
        preferred_colors = (user_data.get('preferred_colors') or '').strip()
        if preferred_colors:
            prompt += f"""
ПРЕДПОЧТЕНИЯ ПОЛЬЗОВАТЕЛЯ ПО ЦВЕТАМ (учти при оформлении!):
Пользователь указал: «{preferred_colors}»
Скорректируй цветовую схему в эту сторону, сохраняя контраст и читаемость.
"""
        prompt += f"""
ШРИФТЫ (ОБЯЗАТЕЛЬНО использовать эти шрифты!):
- Заголовки: {suggested_fonts[0]} (font-weight: 700-900)
- Основной текст: {suggested_fonts[1]} (font-weight: 300-600)
- Подключить через Google Fonts в CSS!

⚠️ КРИТИЧЕСКИ ВАЖНО:
- Используй ТОЧНО все данные, указанные ниже
- НЕ используй заглушки типа "Название товара", "99 BYN", "Пример адреса"
- Все данные клиента (УНП, адрес, телефон, email) использовать ТОЧНО как указано
- Создай СОВРЕМЕННЫЙ дизайн с ЯРКИМИ ЦВЕТАМИ и ГРАДИЕНТАМИ
- CSS ДОЛЖЕН быть ПОЛНЫМ (минимум 500 строк) с ВСЕМИ стилями
- Используй РЕКОМЕНДУЕМЫЕ цвета и шрифты выше!
- Лендинг должен быть продающим и профессиональным

╔═══════════════════════════════════════════════════════════════╗
║ СТРУКТУРА ЛЕНДИНГА (17 ПУНКТОВ)                                ║
╚═══════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════
ПУНКТ 1: HERO БЛОК (верхняя часть)
═══════════════════════════════════════════════════════════════

Тип медиа: {hero_media_type}
Формат: {hero_media_format}
Соотношение сторон: {hero_aspect_ratio}
"""
        
        if hero_discount:
            prompt += f"Скидка: {hero_discount} (позиция: {hero_discount_position})\n"
        
        if hero_media_filename:
            prompt += f"""
⚠️ КРИТИЧЕСКИ ВАЖНО: Оригинальное имя файла hero медиа: "{hero_media_filename}"
ИСПОЛЬЗУЙ ЭТО НАЗВАНИЕ в HTML:
- В атрибуте alt тега <img> или <video>: alt="{hero_media_filename}"
- В атрибуте title: title="{hero_media_filename}"
- В описании товара, если это уместно
- Путь к файлу: img/hero.{hero_media_format if hero_media_format != 'jpeg' else 'jpg'} (но alt и title должны содержать "{hero_media_filename}")
"""
        
        prompt += f"""
ТРЕБОВАНИЯ:
- Фото/видео товара с соотношением сторон {hero_aspect_ratio}
- Если указана скидка - отобразить в углу ({hero_discount_position})
- ВАЖНО: Учесть все вариации формата {hero_media_format}:
  * Для фото: {self._get_format_variations('photo', hero_media_format)}
  * Для видео: {self._get_format_variations('video', hero_media_format)}

═══════════════════════════════════════════════════════════════
ПУНКТ 2: НАЗВАНИЕ ТОВАРА
═══════════════════════════════════════════════════════════════

"{product_name}"

ТРЕБОВАНИЯ:
- Название с маркетинговым усилением (если нужно)
- Использовать ТОЧНО это название: "{product_name}"
- НЕ использовать заглушки типа "Название товара" или "Товар"
- Если название уже хорошее - можно оставить как есть, но добавить эмоциональности

═══════════════════════════════════════════════════════════════
ПУНКТ 3: 3 ЯРКИЕ ХАРАКТЕРИСТИКИ
═══════════════════════════════════════════════════════════════

{chr(10).join([f"- {c}" for c in characteristics])}

ТРЕБОВАНИЯ:
- Отобразить все 3 характеристики
- Шрифтом помельче

═══════════════════════════════════════════════════════════════
ПУНКТ 4: ТАЙМЕР ОБРАТНОГО ОТСЧЕТА
═══════════════════════════════════════════════════════════════

"""
        
        if timer_enabled:
            if timer_type == 'date':
                prompt += f"Тип: До конкретной даты\nДата: {timer_date}\n"
            else:
                prompt += "Тип: Обнуление каждые сутки в 00:00\n"
        else:
            prompt += "Таймер: НЕ нужен\n"
        
        prompt += f"""
═══════════════════════════════════════════════════════════════
ПУНКТ 5: ЦЕНЫ
═══════════════════════════════════════════════════════════════

НОВАЯ ЦЕНА: {new_price}
СТАРАЯ ЦЕНА: {old_price}

ТРЕБОВАНИЯ:
- Старая цена ОБЯЗАТЕЛЬНО перечеркнуть через <s> или text-decoration: line-through
- Новая цена выделить крупным шрифтом и ярким цветом
- Отобразить экономию (разница между старой и новой ценой)
- Формат: "152 BYN 99 BYN" или "152 BYN" зачеркнуто, "99 BYN" крупно
- ⚠️ ВАЖНО: Использовать ТОЧНО эти цены: {old_price} и {new_price}

═══════════════════════════════════════════════════════════════
ПУНКТ 6: ФОРМА ЗАКАЗА (верхняя)
═══════════════════════════════════════════════════════════════

ОБЯЗАТЕЛЬНЫЕ ПОЛЯ:
- Имя (input name="name")
- Телефон (input name="phone" с автоподстановкой +375 и маской)
- ⚠️ ВАЖНО: Форма должна иметь action="send.php" (НЕ sendCPA.php!)

ОПЦИОНАЛЬНЫЕ ПОЛЯ (если есть в типе лендинга):
"""
        
        form_fields_html = []
        form_fields_html.append('<input type="text" name="name" placeholder="Ваше имя" class="form-input" required>')
        form_fields_html.append('<input type="tel" name="phone" id="phone" placeholder="+375 (__) ___-__-__" class="form-input" required>')
        
        if sizes:
            sizes_list = ', '.join(sizes) if isinstance(sizes, list) else str(sizes)
            prompt += f"""
⚠️ ВАЖНО: В форме ОБЯЗАТЕЛЬНО добавить выбор размера!
Размеры: {sizes_list}

Пример HTML для размеров:
<select name="size" class="form-input" required>
  <option value="">Выберите размер</option>
"""
            for size in sizes:
                prompt += f'  <option value="{size}">{size}</option>\n'
            prompt += "</select>\n"
            
            form_fields_html.append(f'<select name="size" class="form-input" required>\n  <option value="">Выберите размер</option>\n' + 
                                   '\n'.join([f'  <option value="{s}">{s}</option>' for s in sizes]) + '\n</select>')
            prompt += "  * ИЛИ кнопки выбора размера с визуальным отображением\n"
        
        if colors:
            colors_list = ', '.join(colors) if isinstance(colors, list) else str(colors)
            prompt += f"""
⚠️ ВАЖНО: В форме ОБЯЗАТЕЛЬНО добавить выбор цвета!
Цвета: {colors_list}

Пример HTML для цветов:
<div class="color-selector">
"""
            for color in colors:
                prompt += f'  <label class="color-option"><input type="radio" name="color" value="{color}" required> {color}</label>\n'
            prompt += "</div>\n"
            
            form_fields_html.append('<div class="color-selector">\n' + 
                                   '\n'.join([f'  <label class="color-option"><input type="radio" name="color" value="{c}" required> {c}</label>' for c in colors]) + 
                                   '\n</div>')
        
        if characteristics_list:
            chars_list = ', '.join(characteristics_list) if isinstance(characteristics_list, list) else str(characteristics_list)
            prompt += f"""
⚠️ ВАЖНО: В форме ОБЯЗАТЕЛЬНО добавить выбор характеристик!
Характеристики: {chars_list}

Пример HTML для характеристик:
<select name="characteristic" class="form-input" required>
  <option value="">Выберите характеристику</option>
"""
            for char in characteristics_list:
                prompt += f'  <option value="{char}">{char}</option>\n'
            prompt += "</select>\n"
            
            form_fields_html.append(f'<select name="characteristic" class="form-input" required>\n  <option value="">Выберите характеристику</option>\n' + 
                                   '\n'.join([f'  <option value="{c}">{c}</option>' for c in characteristics_list]) + '\n</select>')
        
        prompt += """
- Кнопка согласия с политикой конфиденциальности (изначально выбрана)

ТРЕБОВАНИЯ К ФОРМЕ:
- Формат телефона: +375 (__) ___-__-__
- Вставка первых цифр +375 в форму
- Ввод девяти цифр после +375
- ⚠️ ВАЖНО: Использовать ВСЕ указанные выше поля (размеры, цвета, характеристики) если они есть!
- Форма должна быть стилизована и красиво оформлена
- Все поля должны быть обязательными (required)
- Кнопка отправки должна быть яркой и заметной

ПРИМЕР ПОЛНОЙ ФОРМЫ:
<form action="send.php" method="POST" class="order-form" id="orderForm">
"""
        prompt += '\n'.join(form_fields_html)
        prompt += """
  <label class="privacy-checkbox">
    <input type="checkbox" name="privacy" checked required>
    Я согласен с политикой конфиденциальности
  </label>
  <button type="submit" class="btn-order">Заказать</button>
</form>
"""
        
        prompt += f"""
═══════════════════════════════════════════════════════════════
ПУНКТ 7: СРЕДНИЙ БЛОК
═══════════════════════════════════════════════════════════════

Тип блока: {middle_block_type}
"""
        
        if middle_block_type == 'video':
            prompt += f"""
- Видео: {middle_video}
- Формат: {user_data.get('middle_video_format', 'mp4')}
- Соотношение сторон: {user_data.get('middle_video_aspect_ratio', '3:4')}
- Автопроигрывание при попадании в поле зрения
- Возможность включить звук
"""
        elif middle_block_type == 'gallery':
            # Обрабатываем middle_gallery (могут быть словарями или строками)
            gallery_list = []
            for photo in middle_gallery:
                if isinstance(photo, dict):
                    gallery_list.append({
                        'path': photo.get('path', ''),
                        'filename': photo.get('filename', '')
                    })
                else:
                    gallery_list.append({'path': photo, 'filename': None})
            
            prompt += f"""
- Галерея: {len(gallery_list)} фото
- Формат карусели
- Автопрокрутка каждые 5 секунд
- Кнопки вперёд/назад
- Нижние кругляши для навигации
"""
            for i, photo_info in enumerate(gallery_list, 1):
                if photo_info.get('filename'):
                    filename = photo_info['filename']
                    prompt += f"- Фото {i}: {filename} (путь: img/gallery_{i}.jpg)\n"
                    prompt += f"  ⚠️ КРИТИЧЕСКИ ВАЖНО: В HTML используй:\n"
                    prompt += f"    * alt=\"{filename}\" в теге <img>\n"
                    prompt += f"    * title=\"{filename}\" в теге <img>\n"
                    prompt += f"    * Путь: img/gallery_{i}.jpg, но alt и title должны содержать \"{filename}\"\n"
        else:
            prompt += "- Сразу описание\n"
        
        prompt += f"""
═══════════════════════════════════════════════════════════════
ПУНКТ 8: ОПИСАНИЕ ТОВАРА
═══════════════════════════════════════════════════════════════

ОПИСАНИЕ ТОВАРА:
{description_text}
"""
        
        # Если текст с Wildberries - добавляем инструкции по обработке
        if description_is_wildberries:
            prompt += """
⚠️ ВАЖНО: Это описание с Wildberries (маркетплейса)!

ТРЕБОВАНИЯ К ОБРАБОТКЕ:
1. УБРАТЬ ЛИШНЕЕ:
   - Артикулы, штрихкоды, коды товара
   - Информацию о продавце и бренде (если не критично)
   - Категории и подкатегории
   - Информацию о доставке/возврате/гарантии (если есть отдельный блок)
   - Рейтинги и оценки
   - Упоминания Wildberries

2. ДОРАБОТАТЬ МАРКЕТИНГОВО:
   - Сделать текст более продающим и эмоциональным
   - Добавить акцент на преимуществах и выгодах
   - Использовать маркетинговые триггеры (эксклюзивно, ограниченная серия, и т.д.)
   - Улучшить структуру: короткие абзацы, списки преимуществ
   - Добавить призывы к действию
   - Сделать текст более живым и понятным для покупателя

3. СОХРАНИТЬ ВАЖНОЕ:
   - Характеристики товара
   - Состав и материалы (если важно)
   - Размеры и параметры
   - Основные преимущества
   - Уникальные особенности

4. РЕЗУЛЬТАТ:
   - Текст должен быть продающим и цепляющим
   - Без технических деталей маркетплейса
   - С акцентом на выгоды для покупателя
   - Легко читается и воспринимается

"""
        
        # Обрабатываем description_photos (могут быть словарями или строками)
        description_photos_list = []
        for photo in description_photos:
            if isinstance(photo, dict):
                description_photos_list.append({
                    'path': photo.get('path', ''),
                    'filename': photo.get('filename', '')
                })
            else:
                description_photos_list.append({'path': photo, 'filename': None})
        
        prompt += f"""
Фото для описания: {len(description_photos_list)} шт.
"""
        
        if description_photos_list:
            prompt += "- Фото разделены текстом\n"
            prompt += "- Максимум 4 фото\n"
            for i, photo_info in enumerate(description_photos_list, 1):
                if photo_info.get('filename'):
                    filename = photo_info['filename']
                    prompt += f"- Фото {i}: {filename} (путь: img/description_{i}.jpg)\n"
                    prompt += f"  ⚠️ КРИТИЧЕСКИ ВАЖНО: В HTML используй:\n"
                    prompt += f"    * alt=\"{filename}\" в теге <img>\n"
                    prompt += f"    * title=\"{filename}\" в теге <img>\n"
                    prompt += f"    * Путь: img/description_{i}.jpg, но alt и title должны содержать \"{filename}\"\n"
        
        prompt += f"""
═══════════════════════════════════════════════════════════════
ПУНКТ 9-10: ЦЕНЫ И ФОРМА ЗАКАЗА (средняя)
═══════════════════════════════════════════════════════════════

Дублирует пункты 5 и 6 с:
- Напоминанием о скидке
- Новым маркетинговым крючком

═══════════════════════════════════════════════════════════════
ПУНКТ 11: БЛОК ВИДЕО/ГАЛЕРЕЯ/ОТЗЫВЫ
═══════════════════════════════════════════════════════════════

Аналогично пункту 7

═══════════════════════════════════════════════════════════════
ПУНКТ 12: БЛОК ОТЗЫВОВ
═══════════════════════════════════════════════════════════════

Тип отзывов: {reviews_type}
Количество: {len(reviews)}
"""
        
        if reviews:
            for i, review in enumerate(reviews, 1):
                prompt += f"\nОтзыв {i}:\n"
                prompt += f"  Имя: {review.get('name', 'Пользователь')}\n"
                prompt += f"  Город: {review.get('city', 'Беларусь')}\n"
                prompt += f"  Текст: {review.get('text', '')}\n"
                if review.get('photo'):
                    # Путь к фото должен быть относительным: img/review_X.jpg
                    photo_filename = review.get('photo_filename', '')
                    if photo_filename:
                        prompt += f"  Фото: img/review_{i}.jpg (оригинальное имя: {photo_filename})\n"
                        prompt += f"  ⚠️ КРИТИЧЕСКИ ВАЖНО: В HTML используй:\n"
                        prompt += f"    * <img src=\"img/review_{i}.jpg\" alt=\"{photo_filename}\" title=\"{photo_filename}\">\n"
                        prompt += f"    * Путь: img/review_{i}.jpg, но alt и title должны содержать \"{photo_filename}\"\n"
                    else:
                        prompt += f"  Фото: img/review_{i}.jpg (используй этот путь в <img src=\"img/review_{i}.jpg\">)\n"
        
        prompt += f"""
ТРЕБОВАНИЯ:
- Карусель отзывов
- Автопрокрутка каждые 5 секунд
- Кнопки вперёд/назад
- Нижние кругляши
- Соотношение сторон фото: {user_data.get('reviews_aspect_ratio', '3:4')}
- Формат фото: {user_data.get('reviews_photo_format', 'jpeg')} (с вариациями)

═══════════════════════════════════════════════════════════════
ПУНКТ 13-16: ДУБЛИРОВАНИЕ HERO, ТАЙМЕРА, ЦЕН, ФОРМЫ
═══════════════════════════════════════════════════════════════

Дублирует параметры из верхней части лендинга

═══════════════════════════════════════════════════════════════
ПУНКТ 17: ПОДВАЛ
═══════════════════════════════════════════════════════════════

Тип: {footer_info.get('type', 'ip').upper()}
"""
        
        if footer_info.get('type') == 'ip':
            prompt += f"""
ФИО: {footer_info.get('fio', '')}
УНП: {footer_info.get('unp', '')}
Адрес: {footer_info.get('address', '')}
Email: {footer_info.get('email', '')}
Телефон: {footer_info.get('phone', '')}
Время работы: {footer_info.get('schedule', '')}
"""
        else:
            prompt += f"""
Название компании: {footer_info.get('company_name', '')}
УНП: {footer_info.get('unp', '')}
Адрес: {footer_info.get('address', '')}
Email: {footer_info.get('email', '')}
Телефон: {footer_info.get('phone', '')}
Время работы: {footer_info.get('schedule', '')}
"""
        
        prompt += """
Ссылки:
- Политика конфиденциальности: politics.html
- Публичная оферта: oferta.html
- Возврат и обмен: obmen.html

╔═══════════════════════════════════════════════════════════════╗
║ ОБЯЗАТЕЛЬНЫЕ ФАЙЛЫ                                            ║
╚═══════════════════════════════════════════════════════════════╝

1. index.html - главная страница
2. good.html - страница благодарности после заказа
3. oferta.html - публичная оферта
4. obmen.html - возврат и обмен
5. politics.html - политика конфиденциальности
6. send.php - обработчик отправки заявок (ОБЯЗАТЕЛЬНО send.php, НЕ sendCPA.php!)
7. css/style.css - стили (или css/styles.css)
8. js/script.js - скрипты
9. img/ - папка с фото и видео

⚠️ КРИТИЧЕСКИ ВАЖНО:
- Все пути к изображениям должны быть относительными: img/photo_1.jpg, img/review_1.jpg
- НЕ используйте абсолютные пути типа generated_landings/user_XXX_content/photos/
- Форма должна иметь action="send.php" (НЕ sendCPA.php!)

╔═══════════════════════════════════════════════════════════════╗
║ ТРЕБОВАНИЯ К КОДУ (КРИТИЧЕСКИ ВАЖНО!)                         ║
╚═══════════════════════════════════════════════════════════════╝

HTML (МИНИМУМ 500+ СТРОК):
- Полный документ от <!DOCTYPE html> до </html>
- Все 17 пунктов структуры в правильном порядке
- Современная семантическая разметка (header, section, footer)
- Правильная структура форм с action="send.php" method="POST"
- Все данные из промпта должны быть в HTML
- НЕ использовать заглушки - только реальные данные!
- ⚠️ КРИТИЧЕСКИ ВАЖНО: Для всех изображений используй имена файлов из промпта:
  * В атрибуте alt: alt="[имя файла из промпта]"
  * В атрибуте title: title="[имя файла из промпта]"
  * Путь к файлу: img/[тип]_[номер].jpg (но alt и title - имена из промпта!)

CSS (МИНИМУМ 500+ СТРОК - ОБЯЗАТЕЛЬНО!):
- ⚠️ КРИТИЧЕСКИ ВАЖНО: CSS ДОЛЖЕН БЫТЬ ПОЛНЫМ И РАБОТАЮЩИМ!
- ⚠️ НЕ ДОПУСКАЕТСЯ: пустой CSS, только комментарии, отсутствие стилей!

ПОДБОР СТИЛЯ НА ОСНОВЕ ТОВАРА:
Товар: "{product_name}"
Категория: {style_suggestion['category']}
Рекомендуемый стиль: {suggested_style}

РЕКОМЕНДУЕМАЯ ЦВЕТОВАЯ СХЕМА (используй эти цвета!):
- Primary color: {suggested_colors['primary']} (основной акцентный цвет)
- Secondary color: {suggested_colors['secondary']} (вторичный акцент)
- Accent color: {suggested_colors['accent']} (дополнительный акцент)
- Dark background: {suggested_colors['bg_dark']} (темный фон)
- Darker background: {suggested_colors['bg_darker']} (еще более темный фон)

РЕКОМЕНДУЕМЫЕ ШРИФТЫ (используй эти шрифты!):
- Основной шрифт: {suggested_fonts[0]} (для заголовков и важного текста)
- Вспомогательный шрифт: {suggested_fonts[1]} (для основного текста)
- Подключи через Google Fonts: @import url('https://fonts.googleapis.com/css2?family={suggested_fonts[0].replace(' ', '+')}:wght@400;600;700;800;900&family={suggested_fonts[1].replace(' ', '+')}:wght@300;400;500;600&display=swap');

ОБЯЗАТЕЛЬНЫЕ ЭЛЕМЕНТЫ CSS:

1. CSS ПЕРЕМЕННЫЕ (ОБЯЗАТЕЛЬНО!):
:root {{
    --primary-color: {suggested_colors['primary']};
    --secondary-color: {suggested_colors['secondary']};
    --accent-color: {suggested_colors['accent']};
    --dark-bg: {suggested_colors['bg_dark']};
    --darker-bg: {suggested_colors['bg_darker']};
    --text-light: #ffffff;
    --text-gray: #d1d5db;
    --text-dark: #1f2937;
}}

2. БАЗОВЫЕ СТИЛИ:
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: '{suggested_fonts[1]}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-light);
    background: linear-gradient(135deg, var(--darker-bg) 0%, var(--dark-bg) 50%, #1a1f3a 100%);
    min-height: 100vh;
    line-height: 1.6;
}}

3. HERO СЕКЦИЯ (ОБЯЗАТЕЛЬНО!):
- Фото/видео с красивым оформлением (border-radius: 20px, box-shadow)
- Заголовок с градиентом (linear-gradient с primary и secondary цветами)
- Крупный шрифт ({suggested_fonts[0]}, font-weight: 900, font-size: 2.2rem+)
- Яркие цвета для акцентов

4. ЦЕНЫ (ОБЯЗАТЕЛЬНО!):
- Старая цена: text-decoration: line-through; color: #6b7280; font-size: 1.5rem;
- Новая цена: color: var(--primary-color); font-size: 2.5rem+; font-weight: 900; text-shadow: 0 0 20px rgba(...);
- Эффект свечения для новой цены

5. ТАЙМЕР (ОБЯЗАТЕЛЬНО!):
- Крупный шрифт (2rem+)
- Яркий цвет (var(--primary-color))
- Эффект свечения (text-shadow)

6. ФОРМА (ОБЯЗАТЕЛЬНО!):
- Поля ввода: background: rgba(255, 255, 255, 0.1); border: 2px solid rgba(255, 255, 255, 0.2);
- При фокусе: border-color: var(--primary-color); box-shadow: 0 0 20px rgba(...);
- Кнопка: gradient background (linear-gradient с primary и secondary), крупный шрифт, hover эффекты
- Селекторы и радиокнопки: стилизованы как поля ввода

7. ХАРАКТЕРИСТИКИ (ОБЯЗАТЕЛЬНО!):
- Список с иконками (check-icon с градиентом)
- Hover эффекты
- Градиентные фоны для элементов

8. ОТЗЫВЫ (ОБЯЗАТЕЛЬНО!):
- Карусель с плавными переходами
- Карточки отзывов с фоном (rgba(255, 255, 255, 0.08)) и границами
- Фото отзывов: круглые, с рамкой (border: 3px solid var(--primary-color))

9. ПОДВАЛ (ОБЯЗАТЕЛЬНО!):
- Темный фон (rgba(0, 0, 0, 0.3))
- Центрированный текст
- Правильные отступы

10. АДАПТИВНОСТЬ (ОБЯЗАТЕЛЬНО!):
@media (max-width: 768px) {{
    /* Стили для мобильных */
    .product-title {{ font-size: 1.8rem; }}
    .new-price {{ font-size: 2rem; }}
    .timer {{ font-size: 1.8rem; }}
}}

⚠️ ВАЖНО: ВСЕ стили должны быть применены! НЕ оставляй пустые секции!

JavaScript (МИНИМУМ 200+ СТРОК):
- Таймер обратного отсчета (если timer_enabled = true):
  * Формат: ЧЧ:ММ:СС
  * Обнуление каждый день в 00:00 (если timer_type = 'daily')
  * Или обратный отсчет до конкретной даты (если timer_type = 'date')
  * Обновление каждую секунду
- Форматирование телефона:
  * Автоподстановка +375
  * Маска: +375 (__) ___-__-__
  * Валидация (9 цифр после +375)
- Карусели:
  * Автопрокрутка каждые 5 секунд
  * Кнопки вперёд/назад
  * Индикаторы (кругляши) внизу
  * Плавные переходы
- Валидация форм перед отправкой
- Плавные анимации при скролле

PHP (send.php):
- Отправка в Telegram-чат (если notification_type = 'telegram'):
  * Использовать notification_telegram_token и notification_telegram_chat_id
  * Формат сообщения: "Новый заказ:\n\nТовар: {product_name}\nЦена: {new_price}\n..."
- Или отправка на email (если notification_type = 'email'):
  * Использовать notification_email
  * Тема: "Новый заказ: {product_name}"
- Редирект на good.html после успешной отправки

╔═══════════════════════════════════════════════════════════════╗
║ ФОРМАТ ОТВЕТА                                                 ║
╚═══════════════════════════════════════════════════════════════╝

ВЕРНИ ТОЛЬКО JSON:

{
  "html": "<!DOCTYPE html>...",
  "css": "/* CSS код */",
  "js": "// JS код",
  "oferta_html": "<!DOCTYPE html>...",
  "obmen_html": "<!DOCTYPE html>...",
  "politics_html": "<!DOCTYPE html>...",
  "send_php": "<?php ... ?>"
}

⚠️ КРИТИЧЕСКИ ВАЖНО - ПРОВЕРЬ ПЕРЕД ОТПРАВКОЙ:

1. ДАННЫЕ ТОВАРА:
   ✓ Название: "{product_name}" (использовать ТОЧНО, не "Товар" или "Название товара")
   ✓ Новая цена: {new_price} (использовать ТОЧНО, не "99 BYN" или другие заглушки)
   ✓ Старая цена: {old_price} (использовать ТОЧНО, перечеркнуть)
   ✓ Характеристики: {', '.join(characteristics) if characteristics else 'не указаны'} (использовать ВСЕ)

2. ДАННЫЕ КЛИЕНТА (ПОДВАЛ):
   ✓ УНП: {footer_info.get('unp', 'НЕ УКАЗАНО')} (использовать ТОЧНО)
   ✓ Адрес: {footer_info.get('address', 'НЕ УКАЗАНО')} (использовать ТОЧНО)
   ✓ Телефон: {footer_info.get('phone', 'НЕ УКАЗАНО')} (использовать ТОЧНО)
   ✓ Email: {footer_info.get('email', 'НЕ УКАЗАНО')} (использовать ТОЧНО)
   ✓ Время работы: {footer_info.get('schedule', 'НЕ УКАЗАНО')} (использовать ТОЧНО)

3. КАЧЕСТВО КОДА:
   ✓ HTML: минимум 500 строк, полная структура
   ✓ CSS: минимум 400 строк, ПОЛНЫЙ дизайн с ВСЕМИ стилями
   ✓ JS: минимум 200 строк, весь функционал работает
   ✓ Все файлы в едином стиле
   ✓ Адаптивный дизайн (mobile-first)
   ✓ ⚠️ КРИТИЧЕСКИ ВАЖНО: CSS должен содержать ВСЕ стили для ВСЕХ элементов!
   ✓ ⚠️ НЕ ДОПУСКАЕТСЯ: пустой CSS, отсутствие цветов, отсутствие стилей для форм!

4. ФОРМЫ:
   ✓ Использовать ВСЕ собранные данные:
     * Размеры: {', '.join(sizes) if sizes else 'не указаны'} {"⚠️ ОБЯЗАТЕЛЬНО добавить в форму!" if sizes else ""}
     * Цвета: {', '.join(colors) if colors else 'не указаны'} {"⚠️ ОБЯЗАТЕЛЬНО добавить в форму!" if colors else ""}
     * Характеристики: {', '.join(characteristics_list) if characteristics_list else 'не указаны'} {"⚠️ ОБЯЗАТЕЛЬНО добавить в форму!" if characteristics_list else ""}
   ✓ Все поля должны быть стилизованы (background, border, padding, font-size, colors)
   ✓ Селекторы и радиокнопки должны быть красиво оформлены
   ✓ Кнопка отправки должна быть яркой и заметной (gradient background, крупный шрифт)

5. CSS (КРИТИЧЕСКИ ВАЖНО!):
   ✓ Минимум 500 строк кода (ОБЯЗАТЕЛЬНО!)
   ✓ ВСЕ стили должны быть применены (НЕ пустой CSS!)
   ✓ Использовать РЕКОМЕНДУЕМЫЕ цвета: {suggested_colors['primary']}, {suggested_colors['secondary']}, {suggested_colors['accent']}
   ✓ Использовать РЕКОМЕНДУЕМЫЕ шрифты: {suggested_fonts[0]}, {suggested_fonts[1]}
   ✓ Яркие цвета и градиенты (linear-gradient)
   ✓ Темный фон с градиентами (background: linear-gradient с {suggested_colors['bg_darker']} и {suggested_colors['bg_dark']})
   ✓ Стили для ВСЕХ элементов (hero, цены, таймер, форма, характеристики, отзывы, подвал)
   ✓ Адаптивный дизайн (mobile-first с @media queries)
   ✓ CSS переменные ОБЯЗАТЕЛЬНО должны быть определены в :root
   ✓ Все элементы должны иметь видимые стили (не прозрачные, не бесцветные!)

4. ФУНКЦИОНАЛ:
   ✓ Таймер работает (если включен)
   ✓ Форматирование телефона работает
   ✓ Карусели работают с автопрокруткой
   ✓ Формы валидируются перед отправкой
   ✓ Все ссылки работают (oferta.html, obmen.html, politics.html)

5. ОПИСАНИЕ (если с Wildberries):
   ✓ Убрано всё лишнее (артикулы, коды, информация о продавце)
   ✓ Доработано маркетингово (продающий, эмоциональный текст)
   ✓ Сохранены важные характеристики и преимущества

НЕ ИСПОЛЬЗУЙ ЗАГЛУШКИ! ТОЛЬКО РЕАЛЬНЫЕ ДАННЫЕ ИЗ ПРОМПТА!
"""
        
        return prompt
    
    def _get_format_variations(self, media_type: str, format_key: str) -> str:
        """Получить вариации формата для надежности"""
        variations = {
            'photo': {
                'jpeg': ['jpeg', 'jpg', 'JPEG', 'JPG', 'Jpeg', 'Jpg'],
                'png': ['png', 'PNG', 'Png'],
                'svg': ['svg', 'SVG', 'Svg']
            },
            'video': {
                'mp4': ['mp4', 'MP4', 'Mp4', 'mpeg4', 'MPEG4'],
                'mov': ['mov', 'MOV', 'Mov', 'quicktime', 'QuickTime'],
                'avi': ['avi', 'AVI', 'Avi'],
                'webm': ['webm', 'WEBM', 'WebM']
            }
        }
        
        if media_type in variations and format_key in variations[media_type]:
            return ', '.join(variations[media_type][format_key])
        return format_key

