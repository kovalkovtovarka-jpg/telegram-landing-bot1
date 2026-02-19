"""
Построитель промптов для LLM
"""
import json
from typing import Dict, Any
from backend.generator.template_loader import TemplateLoader
from backend.generator.prompt_builder_new import NewPromptBuilder

class PromptBuilder:
    """Класс для построения промптов на основе шаблонов"""
    
    def __init__(self, templates_path: str = 'landing-templates.json'):
        """
        Инициализация построителя промптов
        
        Args:
            templates_path: Путь к файлу с шаблонами
        """
        self.template_loader = TemplateLoader(templates_path)
        self.new_prompt_builder = NewPromptBuilder()
    
    def build_prompt(self, template_id: str, user_data: Dict[str, Any], prompts_path: str = 'chatbot-prompts.md') -> str:
        """
        Построение промпта для генерации
        
        Args:
            template_id: ID шаблона
            user_data: Данные пользователя
            prompts_path: Путь к файлу с промптами
            
        Returns:
            Готовый промпт для LLM
        """
        # Проверяем, используется ли новая структура (для товарщиков)
        if user_data.get('landing_type'):
            # Новая структура из 17 пунктов
            return self.new_prompt_builder.build_prompt(user_data)
        else:
            # Старая структура
            return self._build_detailed_prompt(user_data, template_id)
    
    def _build_detailed_prompt(self, user_data: Dict[str, Any], template_id: str) -> str:
        """
        Создание детального промпта с явной передачей данных пользователя
        
        Args:
            user_data: Данные пользователя
            template_id: ID шаблона
            
        Returns:
            Детальный промпт для LLM
        """
        # Получаем информацию о шаблоне
        template_info = self.template_loader.get_template(template_id)
        if not template_info:
            template_info = {}
        
        # Извлекаем данные пользователя
        product_name = user_data.get('product_name', 'Товар')
        product_description = user_data.get('product_description', '')
        description_is_wildberries = user_data.get('description_is_wildberries', False)
        old_price = user_data.get('old_price', '152 BYN')
        new_price = user_data.get('new_price', '99 BYN')
        benefits = user_data.get('benefits', [])
        photos = user_data.get('photos', [])
        
        # Формируем текст преимуществ
        if isinstance(benefits, list):
            benefits_text = '\n'.join([f"- {b}" for b in benefits])
        else:
            benefits_text = str(benefits)
        
        # Формируем пути к фотографиям
        photo_paths = []
        for i, photo_path in enumerate(photos):
            if isinstance(photo_path, str):
                # Используем относительный путь в img/
                photo_paths.append(f"img/photo_{i+1}.jpg")
        
        photo_paths_text = '\n'.join(photo_paths) if photo_paths else "img/photo_1.jpg"
        
        # Строим улучшенный детальный промпт
        prompt = f"""═══════════════════════════════════════════════════════════════
ЗАДАЧА: Создать ПОЛНЫЙ, РАБОТАЮЩИЙ продающий лендинг для товара
═══════════════════════════════════════════════════════════════

╔═══════════════════════════════════════════════════════════════╗
║ ДАННЫЕ ТОВАРА - ИСПОЛЬЗУЙ ТОЧНО КАК УКАЗАНО (НЕ ЗАГЛУШКИ!)    ║
╚═══════════════════════════════════════════════════════════════╝

📦 НАЗВАНИЕ ТОВАРА: "{product_name}"
   ⚠️ ВАЖНО: Используй ЭТО название везде, НЕ "Название товара"!

📝 ОПИСАНИЕ ТОВАРА: 
{product_description if product_description else 'Описание не предоставлено'}
   {"⚠️ ОСОБОЕ ВНИМАНИЕ: Это описание с Wildberries! ОБЯЗАТЕЛЬНО:" if description_is_wildberries else ""}
   {"   - Убрать артикулы, штрихкоды, коды товара" if description_is_wildberries else ""}
   {"   - Убрать информацию о продавце, бренде, категориях" if description_is_wildberries else ""}
   {"   - Убрать информацию о доставке/возврате/гарантии" if description_is_wildberries else ""}
   {"   - Убрать рейтинги и оценки" if description_is_wildberries else ""}
   {"   - Доработать маркетингово: сделать продающим, эмоциональным" if description_is_wildberries else ""}
   {"   - Добавить акцент на преимуществах и выгодах" if description_is_wildberries else ""}
   {"   - Сохранить характеристики, состав, размеры, преимущества" if description_is_wildberries else ""}

💰 ЦЕНЫ:
   • НОВАЯ ЦЕНА: {new_price}
   • СТАРАЯ ЦЕНА: {old_price} (зачеркни через <s> или CSS)
   ⚠️ ВАЖНО: Используй ЭТИ цены, НЕ "99 BYN" или другие заглушки!

✅ ПРЕИМУЩЕСТВА (перечисли ВСЕ):
{benefits_text if benefits_text else '- Преимущества не указаны'}

📸 ФОТОГРАФИИ (используй эти пути в тегах <img src="...">):
{photo_paths_text}

╔═══════════════════════════════════════════════════════════════╗
║ ТРЕБОВАНИЯ К HTML                                              ║
╚═══════════════════════════════════════════════════════════════╝

HTML должен быть полным (complete), готовым к использованию (production-ready), с чёткой структурой (fully structured). Все секции — в порядке.

1. ПОЛНАЯ СТРУКТУРА:
   <!DOCTYPE html>
   <html lang="ru">
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>{product_name}</title>
     <link rel="stylesheet" href="css/styles.css">
   </head>
   <body>
     [ВСЕ СЕКЦИИ]
     <script src="js/script.js"></script>
   </body>
   </html>

2. ОБЯЗАТЕЛЬНЫЕ СЕКЦИИ (в порядке):
   ✓ Шапка (header) с названием товара
   ✓ Hero-секция с главным изображением, ценой и кнопкой заказа
   ✓ Описание товара (используй product_description)
   ✓ Преимущества (список из benefits)
   ✓ Галерея фотографий (используй пути из photo_paths)
   ✓ Форма заказа (action="send.php" method="POST")
   ✓ Отзывы (если есть)
   ✓ Футер

3. ФОРМА ЗАКАЗА:
   <form action="send.php" method="POST">
     <input type="text" name="name" placeholder="Ваше имя" required>
     <input type="tel" name="phone" placeholder="+375 (__) ___-__-__" required>
     <input type="text" name="address" placeholder="Адрес доставки" required>
     <button type="submit">Заказать за {new_price}</button>
   </form>
   ⚠️ ВАЖНО: Форма должна иметь action="send.php" (НЕ sendCPA.php!)

4. ИСПОЛЬЗОВАНИЕ ДАННЫХ:
   ⚠️ КРИТИЧЕСКИ ВАЖНО: Замени ВСЕ заглушки на РЕАЛЬНЫЕ данные!
   • В заголовках: "{product_name}" (НЕ "Название товара")
   • В ценах: "{new_price}" и "{old_price}" (НЕ "99 BYN")
   • В описании: используй product_description
   • В списке преимуществ: перечисли ВСЕ из benefits
   • В изображениях: используй пути из photo_paths

╔═══════════════════════════════════════════════════════════════╗
║ ТРЕБОВАНИЯ К CSS                                               ║
╚═══════════════════════════════════════════════════════════════╝

CSS полный и рабочий: переменные, reset, стили для всех секций, адаптив (mobile-first, @media), формы, кнопки, карусели. Недопустимо: пустой файл, только комментарии.

╔═══════════════════════════════════════════════════════════════╗
║ ТРЕБОВАНИЯ К JAVASCRIPT                                        ║
╚═══════════════════════════════════════════════════════════════╝

JS полный и рабочий: таймер (ЧЧ:ММ:СС, обновление каждую секунду), форматирование телефона +375, валидация форм, карусели, анимации при скролле. Недопустимо: пустой файл, только комментарии.

╔═══════════════════════════════════════════════════════════════╗
║ ФОРМАТ ОТВЕТА - ТОЛЬКО ВАЛИДНЫЙ JSON                          ║
╚═══════════════════════════════════════════════════════════════╝

ВЕРНИ ТОЛЬКО JSON БЕЗ ДОПОЛНИТЕЛЬНОГО ТЕКСТА:

{{
  "html": "<!DOCTYPE html>\\n<html lang=\\"ru\\">\\n<head>\\n...ПОЛНЫЙ HTML КОД...\\n</html>",
  "css": "/* CSS переменные */\\n:root {{\\n...ПОЛНЫЙ CSS КОД...\\n}}",
  "js": "// Таймер\\nfunction initTimer() {{\\n...ПОЛНЫЙ JAVASCRIPT КОД...\\n}}"
}}

⚠️ КРИТИЧЕСКИ ВАЖНО:
✓ JSON должен быть валидным (экранируй кавычки: \\")
✓ HTML полный (от <!DOCTYPE> до </html>), все секции на месте
✓ CSS полный и рабочий, все секции оформлены
✓ JS полный и рабочий, весь функционал реализован
✓ Используй РЕАЛЬНЫЕ данные из промпта, НЕ заглушки!
✓ Все пути: css/styles.css, js/script.js, img/photo_X.jpg"""

        # Добавляем требования к шаблону
        if template_info:
            prompt += "\n\n" + self._add_technical_requirements(template_info)
        
        return prompt
    
    def _fill_prompt_template(self, template: str, user_data: Dict[str, Any], template_info: Dict) -> str:
        """
        Заполнение промпта данными пользователя
        
        Args:
            template: Шаблон промпта
            user_data: Данные пользователя
            template_info: Информация о шаблоне
            
        Returns:
            Заполненный промпт
        """
        filled = template
        
        # Заменяем плейсхолдеры вида {field_name}
        required_fields = template_info.get('required_fields', {})
        
        for field_name in required_fields:
            placeholder = f"{{{field_name}}}"
            value = user_data.get(field_name, '')
            
            # Форматирование значений
            if isinstance(value, list):
                value = '\n'.join(f"- {item}" for item in value)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            elif value is None:
                value = 'не указано'
            
            filled = filled.replace(placeholder, str(value))
        
        return filled
    
    def _add_common_requirements(self) -> str:
        """
        Добавление общих требований к генерации
        
        Returns:
            Текст с общими требованиями
        """
        return """

ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ:

1. HTML структура:
   - Валидный HTML5
   - Все секции из шаблона должны присутствовать
   - Формы с методом POST на send.php
   - Мета-теги для SEO

2. CSS стили:
   - Адаптивный дизайн (mobile-first)
   - Переменные CSS для цветов
   - Плавные анимации и переходы
   - Все стили в одном файле

3. JavaScript:
   - Таймер обратного отсчета с обнулением в 00:00
   - Форматирование телефона +375 (__) ___-__-__
   - Карусели галереи и отзывов с правильным центрированием
   - Плавные анимации при скролле
   - Валидация форм

4. Интеграции:
   - TikTok Pixel (ID: {tiktok_pixel_id}) перед закрывающим тегом </body>
   - Telegram интеграция через send.php

5. Файлы:
   - HTML: index.html
   - CSS: css/styles.css (или использовать pillow.css)
   - JS: js/script.js (или использовать pillow.js)
   - PHP: send.php (обработчик отправки заявок)

6. Оптимизация:
   - Оптимизированные изображения (указать размеры)
   - Минимальный критический CSS
   - Lazy loading для изображений
"""
    
    def _add_technical_requirements(self, template_info: Dict) -> str:
        """
        Добавление технических требований на основе шаблона
        
        Args:
            template_info: Информация о шаблоне
            
        Returns:
            Текст с техническими требованиями
        """
        requirements = "\n\nТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ К ШАБЛОНУ:\n"
        
        # Особенности шаблона
        features = template_info.get('features', {})
        if features.get('countdown_timer'):
            requirements += "- Обязателен таймер обратного отсчета на сутки\n"
        if features.get('image_carousel'):
            requirements += "- Карусель фотографий с центрированием крайних элементов\n"
        if features.get('reviews_carousel'):
            requirements += "- Карусель отзывов (1 отзыв видно, фото крупное)\n"
        if features.get('variant_selector'):
            requirements += "- Селектор вариантов с динамическим изменением цены\n"
        if features.get('size_guide_modal'):
            requirements += "- Модальное окно с таблицей размеров\n"
        
        # Структура секций
        sections = template_info.get('structure', {}).get('sections', [])
        requirements += f"\nСЕКЦИИ (в порядке отображения):\n"
        for i, section in enumerate(sections, 1):
            requirements += f"{i}. {section.get('name', 'Неизвестно')} - {section.get('elements', [])}\n"
        
        return requirements
