"""
Новый промпт-билдер для структуры из 17 пунктов (для товарщиков)
"""
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

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
                'primary': '#5b7c99',  # Приглушённый синий (сон, спокойствие)
                'secondary': '#6b9080',  # Мягкий зелёный (здоровье, отдых)
                'accent': '#a4c3b2',  # Светло-зелёный
                'bg_dark': '#1e2d3a',  # Тёмно-синий, не агрессивный
                'bg_darker': '#0d1821'
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
            'style': 'elegant' if category == 'health' else 'modern',
            'colors': colors,
            'fonts': font_pair,
        }
    
    def _is_very_bright_palette(self, colors: dict) -> bool:
        """Проверка, что палитра слишком яркая для категории health (высокая насыщенность primary)."""
        primary = (colors.get('primary') or '').strip()
        if not primary or not primary.startswith('#'):
            return False
        try:
            hex_val = primary.lstrip('#')
            if len(hex_val) == 6:
                r, g, b = int(hex_val[0:2], 16) / 255, int(hex_val[2:4], 16) / 255, int(hex_val[4:6], 16) / 255
            elif len(hex_val) == 3:
                r, g, b = (int(hex_val[i], 16) * 17 / 255 for i in range(3))
            else:
                return False
            mx, mn = max(r, g, b), min(r, g, b)
            if mx == 0:
                return False
            saturation = (mx - mn) / mx
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return saturation > 0.65 or luminance > 0.75
        except Exception:
            return False

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
    
    async def analyze_product_image(self, image_path: str, product_name: str, description: str, llm_client) -> Optional[Dict[str, Any]]:
        """
        Анализ фото товара через Vision API для получения цветов и стиля
        
        Args:
            image_path: Путь к hero-изображению товара
            product_name: Название товара
            description: Описание товара
            llm_client: Экземпляр LLMClient для вызова vision API
            
        Returns:
            Словарь с цветами, шрифтами и стилем на основе изображения, или None если анализ не удался
        """
        if not image_path or not os.path.exists(image_path):
            logger.info("Hero image not found or path invalid, using text-based style analysis")
            return None
        
        try:
            logger.info(f"Analyzing product image via Vision API: {image_path}")
            vision_result = await llm_client.analyze_image_style(image_path, product_name, description)
            
            if vision_result and 'colors' in vision_result and 'fonts' in vision_result:
                logger.info(f"✓ Vision API analysis successful: primary color={vision_result['colors'].get('primary')}, fonts={vision_result['fonts']}")
                return vision_result
            else:
                logger.warning("Vision API returned invalid result, falling back to text-based analysis")
                return None
        except Exception as e:
            logger.error(f"Error in vision analysis: {e}", exc_info=True)
            return None
    
    def build_prompt(self, user_data: Dict[str, Any]) -> str:
        """
        Построение промпта для новой структуры лендинга
        
        Args:
            user_data: Данные пользователя (собранные по новой структуре)
                      Может содержать 'vision_style_suggestion' с результатом vision анализа
            
        Returns:
            Готовый промпт для LLM
        """
        # Извлекаем все данные
        product_name = user_data.get('product_name', 'Товар')
        description_text = user_data.get('description_text', '')
        
        # Используем результат vision анализа, если есть, иначе - текстовый анализ
        vision_suggestion = user_data.get('vision_style_suggestion')
        if vision_suggestion and 'colors' in vision_suggestion and 'fonts' in vision_suggestion:
            logger.info("Using vision-based style suggestion from image analysis")
            style_suggestion = vision_suggestion
            # Для здоровья/сна: если Vision вернул слишком яркие цвета — подменяем на спокойную палитру
            category = style_suggestion.get('category', 'general')
            if category == 'health' and self._is_very_bright_palette(style_suggestion.get('colors', {})):
                fallback = self._analyze_product_and_suggest_style(product_name, description_text)
                style_suggestion = {**style_suggestion, 'colors': fallback['colors']}
                logger.info("Vision colors too bright for health category, using calmer palette")
        else:
            logger.info("Using text-based style suggestion (no vision analysis available)")
            style_suggestion = self._analyze_product_and_suggest_style(product_name, description_text)
        
        suggested_colors = style_suggestion['colors']
        suggested_fonts = style_suggestion['fonts']
        suggested_style = style_suggestion.get('style', 'modern')
        
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
- CSS должен быть полным и рабочим: все секции стилизованы, без пустых блоков.
- Используй РЕКОМЕНДУЕМЫЕ цвета и шрифты выше!
- Лендинг шаблонный: важна правильная подача информации, а не креатив. Все блоки — в строгом порядке ниже.

╔═══════════════════════════════════════════════════════════════╗
║ СТРУКТУРА ЛЕНДИНГА (строгий порядок блоков)                   ║
╚═══════════════════════════════════════════════════════════════╝

СТРОГИЙ ПОРЯДОК БЛОКОВ (каждый блок — отдельная <section class="...">, не сливать):
1. HERO — обязательно главное фото (на всю ширину) + скидка/акция + короткое описание + форма заказа (имя, телефон, action="send.php").
2. [Если есть видео] Видеоблок — сразу под hero; иначе переходи к п.3.
3. ОПИСАНИЕ — текст разбить на абзацы и подзаголовки (h2/h3); при наличии — фото в блоке описания (каждое в своей секции/абзаце).
4. СРЕДНЯЯ ФОРМА — дубликат формы заказа (те же поля, action="send.php").
5. Галерея (карусель, минимум 2 фото, 3:4) ИЛИ сразу отзывы, если галереи нет.
6. ОТЗЫВЫ — карусель, фото отзывов полноформатные 3:4.
7. ДУБЛЬ HERO — снова главное фото + форма заказа (третий экземпляр формы).
8. ПОДВАЛ — ИП (ФИО) или ООО (название), УНП, адрес, телефон, email, время работы (все данные из промпта).
После отправки формы — редирект на good.html (страница благодарности).

ТРЕБОВАНИЯ К ВЕРСТКЕ (ОБЯЗАТЕЛЬНО):
- Каждая смысловая часть — в отдельном теге <section class="..."> (hero, description-section, gallery-section, reviews-section, footer). Не сливать блоки в один поток.
- Фото строго по блокам: hero — одно главное; описание — свои фото в блоке описания; галерея — в отдельной секции; отзывы — фото в блоке отзывов. Каждый блок со своими классами и отступами.
- Все изображения на всю ширину контейнера: в CSS для section img, .hero img, .gallery img, .description img, .reviews img задать width: 100%; max-width: 100%; height: auto; object-fit: cover; display: block;
- Текст описания разбить на короткие абзацы и списки (буллеты), с подзаголовками (h2/h3); не один сплошной абзац.

═══════════════════════════════════════════════════════════════
БЛОК 1: HERO (первый кадр, самый сочный)
═══════════════════════════════════════════════════════════════

Тип медиа: {hero_media_type}
Формат: {hero_media_format}
Соотношение сторон: {hero_aspect_ratio} (полноформатные фото).
В hero обязательно: скидка/акция/предложение, короткое описание, форма заказа (поля: имя, телефон; при наличии — размер/цвет/кол-во). Эта же форма дублируется в средней части и внизу лендинга.
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
- Первый кадр — самый сочный; при необходимости показать несколько цветов — несколько фото в hero, все полноформатные {hero_aspect_ratio}.
- Фото/видео с соотношением сторон {hero_aspect_ratio}. Скидка/акция — в углу ({hero_discount_position or 'по умолчанию'}).
- Вариации формата: фото {self._get_format_variations('photo', hero_media_format)}; видео {self._get_format_variations('video', hero_media_format)}.

В составе hero (первый экран):
- Название товара: "{product_name}" (использовать ТОЧНО, без заглушек)
- 3 яркие характеристики: {chr(10).join([f"  • {c}" for c in characteristics])}
- Таймер обратного отсчёта:
"""
        
        if timer_enabled:
            if timer_type == 'date':
                prompt += f"Тип: До конкретной даты\nДата: {timer_date}\n"
            else:
                prompt += "Тип: Обнуление каждые сутки в 00:00\n"
        else:
            prompt += "Таймер: НЕ нужен\n"
        
        prompt += f"""
- Цены в hero: новая {new_price}, старая {old_price} (старую зачеркнуть; новую выделить крупно и ярко). Использовать ТОЧНО эти значения.
- Форма заказа (в hero, затем дублируется в середине и внизу):

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
БЛОК 2: ВИДЕО (если есть) — сразу под hero
═══════════════════════════════════════════════════════════════

"""
        
        if middle_block_type == 'video':
            prompt += f"""
Тип блока: видео.
- Видео: {middle_video}
- Формат: {user_data.get('middle_video_format', 'mp4')}
- Соотношение сторон: {user_data.get('middle_video_aspect_ratio', '3:4')}
- ОБЯЗАТЕЛЬНО: автопроигрывание при попадании в зону видимости (когда блок попадает в viewport). Возможность включить звук.
"""
        elif middle_block_type == 'gallery':
            # Галерея идёт после описания и средней формы (БЛОК 5 в порядке лендинга)
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
- Видео нет. Ниже будут блоки: Описание → Средняя форма → эта Галерея → Отзывы → Дубль hero → Подвал.
- Галерея (разместить после средней формы заказа): карусель, минимум 2 фото, полноформатные 3:4. Всего фото: {len(gallery_list)}.
- Автопрокрутка каждые 5 секунд, кнопки вперёд/назад, нижние кругляши.
"""
            for i, photo_info in enumerate(gallery_list, 1):
                if photo_info.get('filename'):
                    filename = photo_info['filename']
                    prompt += f"- Фото {i}: {filename} (путь: img/gallery_{i}.jpg)\n"
                    prompt += f"  В HTML: alt=\"{filename}\", title=\"{filename}\", src=\"img/gallery_{i}.jpg\"\n"
                else:
                    prompt += f"- Фото {i}: img/gallery_{i}.jpg\n"
        else:
            prompt += "- Видео нет. Следующий блок после hero — описание.\n"
        
        prompt += f"""
═══════════════════════════════════════════════════════════════
БЛОК 3: ОПИСАНИЕ ТОВАРА
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
БЛОК 4: СРЕДНЯЯ ФОРМА ЗАКАЗА
═══════════════════════════════════════════════════════════════

Дубликат формы из hero (те же поля: имя, телефон, размер/цвет/кол-во по данным). Напоминание о скидке, короткий маркетинговый крючок.

═══════════════════════════════════════════════════════════════
БЛОК 5: ГАЛЕРЕЯ (если достаточно фото) — см. данные выше
═══════════════════════════════════════════════════════════════

Карусель, минимум 2 фото, полноформатные 3:4.

═══════════════════════════════════════════════════════════════
БЛОК 6: ОТЗЫВЫ
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
- Соотношение сторон фото отзывов: {user_data.get('reviews_aspect_ratio', '3:4')} (полноформатные). Формат: {user_data.get('reviews_photo_format', 'jpeg')}.
- Отзывы генерируются под товар на основе описания; могут быть с фото или без.

═══════════════════════════════════════════════════════════════
БЛОК 7: ДУБЛЬ HERO (фото + форма заказа)
═══════════════════════════════════════════════════════════════

Повтор hero: то же фото (или несколько, если разные цвета), скидка/акция, форма заказа (идентичная верхней и средней).

═══════════════════════════════════════════════════════════════
БЛОК 8: ПОДВАЛ САЙТА (ОБЯЗАТЕЛЬНО вывести все указанные данные)
═══════════════════════════════════════════════════════════════

В подвале <footer class="footer"> вывести ВСЕ данные ниже: ИП (ФИО) или ООО (название), УНП, адрес, телефон, email, время работы. Не заменять заглушками.
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
║ ТРЕБОВАНИЯ К КОДУ                                              ║
╚═══════════════════════════════════════════════════════════════╝

HTML:
- Должен быть полным (complete), готовым к использованию (production-ready), с чёткой структурой (fully structured).
- Все перечисленные выше блоки (1–8) в правильном порядке. Полный документ от <!DOCTYPE html> до </html>.
- Современная семантическая разметка (header, section, footer).
- Формы: action="send.php" method="POST". Все данные из промпта — в HTML, без заглушек.
- Изображения: alt и title — имена из промпта; путь — img/[тип]_[номер].jpg.

CSS:
- Полный и рабочий: все секции оформлены, без пустых блоков и без «воды».
- Изображения в секциях на всю ширину: section img, .hero img, .gallery img, .product-visual img {{ width: 100%; max-width: 100%; height: auto; object-fit: cover; display: block; }}
- Недопустимо: пустой файл, только комментарии, отсутствие стилей.

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

Все перечисленные элементы CSS должны быть реализованы; пустые секции не допускаются.

JavaScript:
- Полный и рабочий: весь описанный функционал реализован.
- Таймер (если включён): формат ЧЧ:ММ:СС, обновление каждую секунду; обнуление в 00:00 или до указанной даты.
- Телефон: автоподстановка +375, маска +375 (__) ___-__-__, валидация 9 цифр.
- Карусели: автопрокрутка каждые 5 сек, кнопки вперёд/назад, индикаторы внизу, плавные переходы.
- Валидация форм перед отправкой, плавные анимации при скролле.

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
   ✓ HTML: полный, production-ready, все блоки (1–8) в порядке, без заглушек
   ✓ CSS: полный и рабочий, все секции оформлены, без пустых блоков
   ✓ JS: весь функционал реализован (таймер, телефон, карусели, валидация)
   ✓ Единый стиль, адаптив (mobile-first)
   ✓ Недопустимо: пустой CSS, отсутствие стилей для форм и секций

4. ФОРМЫ:
   ✓ Использовать ВСЕ собранные данные:
     * Размеры: {', '.join(sizes) if sizes else 'не указаны'} {"⚠️ ОБЯЗАТЕЛЬНО добавить в форму!" if sizes else ""}
     * Цвета: {', '.join(colors) if colors else 'не указаны'} {"⚠️ ОБЯЗАТЕЛЬНО добавить в форму!" if colors else ""}
     * Характеристики: {', '.join(characteristics_list) if characteristics_list else 'не указаны'} {"⚠️ ОБЯЗАТЕЛЬНО добавить в форму!" if characteristics_list else ""}
   ✓ Все поля должны быть стилизованы (background, border, padding, font-size, colors)
   ✓ Селекторы и радиокнопки должны быть красиво оформлены
   ✓ Кнопка отправки должна быть яркой и заметной (gradient background, крупный шрифт)

5. CSS:
   ✓ Полный файл: все секции и элементы оформлены (НЕ пустой CSS!)
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

