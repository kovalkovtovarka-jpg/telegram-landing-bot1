"""
LLM клиент для генерации кода
Поддерживает OpenAI, Anthropic Claude, Google Gemini
"""
from openai import OpenAI
from typing import Dict, Optional, Any
import json
import re
import logging
import asyncio
from backend.config import Config

logger = logging.getLogger(__name__)

class LLMClient:
    """Клиент для работы с LLM API (OpenAI, Anthropic, Google)"""
    
    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        """
        Инициализация LLM клиента
        
        Args:
            api_key: API ключ (если None, берется из конфига)
            provider: Провайдер ('openai', 'anthropic', 'google')
        """
        self.provider = provider or Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.temperature = Config.LLM_TEMPERATURE
        self.max_tokens = Config.LLM_MAX_TOKENS
        
        # Инициализация клиента в зависимости от провайдера
        if self.provider == 'openai':
            self.api_key = api_key or Config.OPENAI_API_KEY
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
            else:
                self.client = None
        elif self.provider == 'anthropic':
            try:
                import anthropic
                self.api_key = api_key or Config.ANTHROPIC_API_KEY
                if self.api_key:
                    self.client = anthropic.Anthropic(api_key=self.api_key)
                else:
                    self.client = None
            except ImportError:
                logger.warning("Anthropic SDK не установлен. Установите: pip install anthropic")
                self.client = None
        elif self.provider == 'google':
            try:
                import google.generativeai as genai
                self.api_key = api_key or Config.GOOGLE_API_KEY
                if self.api_key:
                    genai.configure(api_key=self.api_key)
                    self.client = genai
                else:
                    self.client = None
            except ImportError:
                logger.warning("Google Generative AI SDK не установлен. Установите: pip install google-generativeai")
                self.client = None
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
    
    async def generate_landing(self, prompt: str) -> Dict[str, any]:
        """
        Генерация кода лендинга через LLM с retry и таймаутами
        
        Args:
            prompt: Промпт для генерации
            
        Returns:
            Словарь с HTML, CSS, JS кодом и метаданными
        """
        if not self.client:
            raise ValueError(f"{self.provider.upper()} API ключ не установлен или клиент не инициализирован")
        
        max_retries = Config.LLM_MAX_RETRIES
        timeout = Config.LLM_TIMEOUT
        retry_delay = Config.LLM_RETRY_DELAY
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Попытка {attempt + 1}/{max_retries} генерации через {self.provider}")
                
                # Применяем таймаут к генерации
                if self.provider == 'openai':
                    result = await asyncio.wait_for(
                        self._generate_openai(prompt),
                        timeout=timeout
                    )
                elif self.provider == 'anthropic':
                    result = await asyncio.wait_for(
                        self._generate_anthropic(prompt),
                        timeout=timeout
                    )
                elif self.provider == 'google':
                    result = await asyncio.wait_for(
                        self._generate_google(prompt),
                        timeout=timeout
                    )
                else:
                    raise ValueError(f"Неподдерживаемый провайдер: {self.provider}")
                
                logger.info(f"✓ Успешная генерация через {self.provider} (попытка {attempt + 1})")
                return result
                
            except asyncio.TimeoutError:
                last_exception = Exception(f"Таймаут при генерации через {self.provider} (превышено {timeout} секунд)")
                logger.warning(f"Таймаут на попытке {attempt + 1}/{max_retries}: {last_exception}")
                
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                # Проверяем тип ошибки
                if 'rate limit' in error_msg or '429' in error_msg:
                    logger.warning(f"Rate limit на попытке {attempt + 1}/{max_retries}. Ожидание...")
                    # Для rate limit увеличиваем задержку
                    wait_time = retry_delay * (2 ** attempt) * 2  # Exponential backoff с множителем для rate limit
                    if wait_time > 60:
                        wait_time = 60  # Максимум 60 секунд
                    await asyncio.sleep(wait_time)
                    continue
                elif 'timeout' in error_msg or 'timed out' in error_msg:
                    logger.warning(f"Таймаут на попытке {attempt + 1}/{max_retries}")
                elif 'network' in error_msg or 'connection' in error_msg:
                    logger.warning(f"Ошибка сети на попытке {attempt + 1}/{max_retries}")
                else:
                    logger.warning(f"Ошибка на попытке {attempt + 1}/{max_retries}: {e}")
                
                # Если это не последняя попытка - ждем перед retry
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Повтор через {wait_time:.1f} секунд...")
                    await asyncio.sleep(wait_time)
        
        # Все попытки исчерпаны
        error_message = f"Не удалось сгенерировать код через {self.provider} после {max_retries} попыток"
        if last_exception:
            error_message += f": {str(last_exception)}"
        
        logger.error(error_message)
        raise Exception(error_message) from last_exception
    
    async def _generate_openai(self, prompt: str) -> Dict[str, any]:
        """Генерация через OpenAI"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=0.9,
            presence_penalty=0.1,
            frequency_penalty=0.2
        )
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        code_data = self._parse_response(content)
        
        return {
            'html': code_data.get('html', ''),
            'css': code_data.get('css', ''),
            'js': code_data.get('js', ''),
            'oferta_html': code_data.get('oferta_html', ''),
            'obmen_html': code_data.get('obmen_html', ''),
            'politics_html': code_data.get('politics_html', ''),
            'send_php': code_data.get('send_php', ''),
            'tokens_used': tokens_used,
            'model': self.model,
            'provider': 'openai',
            'raw_response': content
        }
    
    async def _generate_anthropic(self, prompt: str) -> Dict[str, any]:
        """Генерация через Anthropic Claude"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        content = message.content[0].text
        tokens_used = message.usage.input_tokens + message.usage.output_tokens
        
        code_data = self._parse_response(content)
        
        return {
            'html': code_data.get('html', ''),
            'css': code_data.get('css', ''),
            'js': code_data.get('js', ''),
            'oferta_html': code_data.get('oferta_html', ''),
            'obmen_html': code_data.get('obmen_html', ''),
            'politics_html': code_data.get('politics_html', ''),
            'send_php': code_data.get('send_php', ''),
            'tokens_used': tokens_used,
            'model': self.model,
            'provider': 'anthropic',
            'raw_response': content
        }
    
    async def _generate_google(self, prompt: str) -> Dict[str, any]:
        """Генерация через Google Gemini"""
        model = self.client.GenerativeModel(
            model_name=self.model,
            generation_config={
                'temperature': self.temperature,
                'max_output_tokens': self.max_tokens,
            }
        )
        
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        content = response.text
        
        # Gemini не возвращает точное количество токенов, используем приблизительную оценку
        tokens_used = len(content.split()) * 1.3  # Примерная оценка
        
        code_data = self._parse_response(content)
        
        return {
            'html': code_data.get('html', ''),
            'css': code_data.get('css', ''),
            'js': code_data.get('js', ''),
            'oferta_html': code_data.get('oferta_html', ''),
            'obmen_html': code_data.get('obmen_html', ''),
            'politics_html': code_data.get('politics_html', ''),
            'send_php': code_data.get('send_php', ''),
            'tokens_used': int(tokens_used),
            'model': self.model,
            'provider': 'google',
            'raw_response': content
        }
    
    def _parse_response(self, response: str) -> Dict[str, str]:
        """
        Улучшенный парсинг ответа от LLM (извлечение HTML, CSS, JS и дополнительных файлов)
        
        Args:
            response: Ответ от LLM
            
        Returns:
            Словарь с html, css, js, oferta_html, obmen_html, politics_html, send_php
        """
        result = {
            'html': '', 
            'css': '', 
            'js': '',
            'oferta_html': '',
            'obmen_html': '',
            'politics_html': '',
            'send_php': ''
        }
        
        # Метод 1: Пытаемся найти JSON в ответе (самый надежный)
        # Ищем JSON объект, который может быть многострочным
        json_patterns = [
            r'\{[\s\S]*?"html"[\s\S]*?"css"[\s\S]*?"js"[\s\S]*?\}',  # Полный JSON
            r'\{[\s\S]*?\}',  # Любой JSON объект
        ]
        
        for pattern in json_patterns:
            json_match = re.search(pattern, response, re.MULTILINE | re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    # Убираем markdown код блоки если есть
                    json_str = re.sub(r'```json\s*', '', json_str, flags=re.IGNORECASE)
                    json_str = re.sub(r'```\s*$', '', json_str, flags=re.IGNORECASE)
                    json_str = json_str.strip()
                    
                    data = json.loads(json_str)
                    html = data.get('html', '')
                    css = data.get('css', '')
                    js = data.get('js', '')
                    
                    # Проверяем что основные данные не пустые
                    if html and css and js:
                        result['html'] = html
                        result['css'] = css
                        result['js'] = js
                        # Дополнительные файлы (могут быть пустыми)
                        result['oferta_html'] = data.get('oferta_html', '')
                        result['obmen_html'] = data.get('obmen_html', '')
                        result['politics_html'] = data.get('politics_html', '')
                        result['send_php'] = data.get('send_php', '')
                        logger.info("Успешно извлечен JSON из ответа")
                        return result
                except json.JSONDecodeError as e:
                    logger.warning(f"Ошибка парсинга JSON: {e}")
                    continue
        
        # Метод 2: Извлекаем код из markdown блоков
        html_match = re.search(r'```html\s*([\s\S]*?)```', response, re.IGNORECASE)
        if html_match:
            result['html'] = html_match.group(1).strip()
        
        css_match = re.search(r'```css\s*([\s\S]*?)```', response, re.IGNORECASE)
        if css_match:
            result['css'] = css_match.group(1).strip()
        
        js_match = re.search(r'```javascript\s*([\s\S]*?)```', response, re.IGNORECASE)
        if not js_match:
            js_match = re.search(r'```js\s*([\s\S]*?)```', response, re.IGNORECASE)
        if js_match:
            result['js'] = js_match.group(1).strip()
        
        # Метод 3: Пытаемся найти код между тегами или в строках
        if not result['html']:
            # Ищем HTML документ
            html_doc = re.search(r'(<!DOCTYPE[\s\S]*?</html>)', response, re.IGNORECASE)
            if html_doc:
                result['html'] = html_doc.group(1).strip()
        
        if not result['css']:
            # Ищем CSS между фигурными скобками или в стилях
            css_block = re.search(r'(\{[^}]*\{[\s\S]*?\}[^}]*\})', response)
            if css_block and len(css_block.group(1)) > 100:
                result['css'] = css_block.group(1).strip()
        
        if not result['js']:
            # Ищем JavaScript функции
            js_functions = re.search(r'(function\s+\w+[\s\S]*?\n\})', response)
            if js_functions:
                result['js'] = js_functions.group(1).strip()
        
        # Логируем результат парсинга
        if result['html'] and result['css'] and result['js']:
            logger.info(f"Успешно извлечен код: HTML={len(result['html'])} символов, CSS={len(result['css'])} символов, JS={len(result['js'])} символов")
        else:
            logger.warning(f"Неполный парсинг: HTML={len(result['html'])}, CSS={len(result['css'])}, JS={len(result['js'])}")
        
        return result
    
    def test_connection(self) -> bool:
        """
        Проверка подключения к API
        
        Returns:
            True если подключение успешно
        """
        if not self.client:
            return False
        
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10
                )
                return True
            elif self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                return True
            elif self.provider == 'google':
                model = self.client.GenerativeModel(model_name=self.model)
                response = model.generate_content("test")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки подключения к {self.provider}: {e}")
            return False
    
    # Улучшенный системный промпт с четкими инструкциями
    SYSTEM_PROMPT = """Ты - профессиональный веб-разработчик, специализирующийся на создании высококачественных продающих лендингов.

ТВОЯ ЗАДАЧА: Создать ПОЛНЫЙ, РАБОТАЮЩИЙ лендинг с HTML, CSS и JavaScript.

⚠️ КРИТИЧЕСКИ ВАЖНО:
- Используй ВСЕ данные из промпта пользователя
- НЕ используй заглушки - только реальные данные
- CSS должен быть ПОЛНЫМ (минимум 500 строк) с ВСЕМИ стилями
- ОБЯЗАТЕЛЬНО используй РЕКОМЕНДУЕМЫЕ цвета и шрифты из промпта!
- Все цвета должны быть ЯРКИМИ и ВИДИМЫМИ (не прозрачные, не бесцветные!)
- Все шрифты должны быть подключены через Google Fonts
- Формы должны использовать ВСЕ собранные данные (размеры, цвета, характеристики)

═══════════════════════════════════════════════════════════════
ТРЕБОВАНИЯ К HTML (ОБЯЗАТЕЛЬНО):
═══════════════════════════════════════════════════════════════

1. СТРУКТУРА ДОКУМЕНТА (полная):
   <!DOCTYPE html>
   <html lang="ru">
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0">
     <title>[НАЗВАНИЕ ТОВАРА ИЗ ПРОМПТА - ИСПОЛЬЗУЙ ТОЧНО!]</title>
     <link rel="stylesheet" href="css/style.css">
   </head>
   <body>
     [ВСЕ СЕКЦИИ ЛЕНДИНГА]
     <script src="js/script.js"></script>
   </body>
   </html>

2. ОБЯЗАТЕЛЬНЫЕ СЕКЦИИ:
   - Hero-секция с главным изображением/видео и ценой
   - Название товара (ИСПОЛЬЗУЙ ТОЧНО из промпта!)
   - 3 яркие характеристики (ИСПОЛЬЗУЙ ТОЧНО из промпта!)
   - Таймер обратного отсчета (если включен)
   - Цены (старая зачеркнута, новая выделена)
   - Форма заказа с ВСЕМИ полями из промпта (размеры, цвета, характеристики)
   - Описание товара
   - Отзывы (если указаны)
   - Подвал с данными клиента (ИСПОЛЬЗУЙ ТОЧНО из промпта!)
   - Футер

3. ФОРМЫ:
   - Все формы должны иметь action="send.php" method="POST"
   - ОБЯЗАТЕЛЬНЫЕ поля: name, phone
   - ОПЦИОНАЛЬНЫЕ поля (если указаны в промпте):
     * size (select) - для размеров
     * color (radio) - для цветов
     * characteristic (select) - для характеристик
   - ⚠️ ВАЖНО: Использовать ВСЕ поля из промпта (размеры, цвета, характеристики)!
   - Кнопка отправки с текстом "Заказать"
   - Все поля должны быть стилизованы (background, border, padding, font-size)

4. ИСПОЛЬЗОВАНИЕ ДАННЫХ:
   - НАЗВАНИЕ ТОВАРА: используй ТОЧНО из промпта, не "Название товара"
   - ОПИСАНИЕ: используй ТОЧНО из промпта
   - НОВАЯ ЦЕНА: используй ТОЧНО из промпта, не "99 BYN"
   - СТАРАЯ ЦЕНА: используй ТОЧНО из промпта, зачеркни через <s> или text-decoration: line-through
   - ПРЕИМУЩЕСТВА: перечисли ВСЕ из промпта
   - ФОТОГРАФИИ: используй пути из промпта (img/photo_1.jpg, img/photo_2.jpg и т.д.)

═══════════════════════════════════════════════════════════════
ТРЕБОВАНИЯ К CSS (ОБЯЗАТЕЛЬНО):
═══════════════════════════════════════════════════════════════

1. МИНИМУМ 400+ СТРОК КОДА (ОБЯЗАТЕЛЬНО!):
   ⚠️ КРИТИЧЕСКИ ВАЖНО: CSS ДОЛЖЕН БЫТЬ ПОЛНЫМ С ВСЕМИ СТИЛЯМИ!
   
   ОБЯЗАТЕЛЬНО ВКЛЮЧИ:
   - CSS переменные для цветов (:root {{ --primary-color: #ff6b9d; --secondary-color: #c084fc; --dark-bg: #0a0e27; ... }})
   - Reset стили (* {{ margin: 0; padding: 0; box-sizing: border-box; }})
   - Базовые стили для body, html (фон, шрифты, цвета)
   - Темный фон с градиентами (linear-gradient)
   - Стили для ВСЕХ секций (hero, характеристики, таймер, форма, отзывы, подвал)
   - Яркие цвета для акцентов (primary-color, secondary-color)
   - Стили для форм (поля ввода, селекторы, радиокнопки, кнопки)
   - Стили для кнопок (gradient backgrounds, hover effects)
   - Стили для цен (старая зачеркнута, новая выделена крупным шрифтом)
   - Стили для таймера (крупный шрифт, яркий цвет, эффект свечения)
   - Стили для каруселей (кнопки навигации, индикаторы)
   - Адаптивный дизайн (mobile-first с @media queries)
   - Плавные переходы и анимации (transition, transform, animation)

2. АДАПТИВНОСТЬ:
   - Mobile-first подход
   - @media (min-width: 768px) для планшетов
   - @media (min-width: 1024px) для десктопов

3. АНИМАЦИИ:
   - Плавные переходы (transition: all 0.3s ease)
   - Анимации при наведении (hover: transform, box-shadow)
   - Анимации при скролле (fade-in, slide-in)

4. НЕ ДОПУСКАЙ:
   - Пустой CSS файл
   - Только комментарии без кода
   - Меньше 400 строк
   - Отсутствие цветов и стилей
   - Отсутствие стилей для форм

═══════════════════════════════════════════════════════════════
ТРЕБОВАНИЯ К JAVASCRIPT (ОБЯЗАТЕЛЬНО):
═══════════════════════════════════════════════════════════════

1. МИНИМУМ 150+ СТРОК КОДА:
   - Таймер обратного отсчета (24 часа, обнуляется в 00:00)
   - Форматирование телефона +375 (__) ___-__-__
   - Валидация форм
   - Карусели (галерея, отзывы) с правильным центрированием
   - Плавные анимации при скролле
   - Обработка отправки форм

2. ТАЙМЕР:
   - Обратный отсчет 24 часа
   - Обнуляется каждый день в 00:00
   - Формат: ЧЧ:ММ:СС
   - Обновление каждую секунду

3. ФОРМАТИРОВАНИЕ ТЕЛЕФОНА:
   - Маска: +375 (__) ___-__-__
   - Автоматическое форматирование при вводе
   - Валидация формата

4. КАРУСЕЛИ:
   - Плавная прокрутка
   - Правильное центрирование активного элемента
   - Кнопки навигации (prev/next)
   - Автоматическая прокрутка (опционально)

5. НЕ ДОПУСКАЙ:
   - Пустой JS файл
   - Только комментарии без кода
   - Меньше 50 строк

═══════════════════════════════════════════════════════════════
ФОРМАТ ОТВЕТА (КРИТИЧЕСКИ ВАЖНО):
═══════════════════════════════════════════════════════════════

ВЕРНИ ТОЛЬКО ВАЛИДНЫЙ JSON БЕЗ ДОПОЛНИТЕЛЬНОГО ТЕКСТА:

{
  "html": "<!DOCTYPE html>\\n<html lang=\\"ru\\">\\n<head>\\n...полный HTML код...\\n</html>",
  "css": "/* CSS переменные */\\n:root {\\n...полный CSS код...\\n}",
  "js": "// Таймер\\nfunction initTimer() {\\n...полный JavaScript код...\\n}"
}

ВАЖНО:
- JSON должен быть валидным (экранируй кавычки и переносы строк)
- HTML должен быть ПОЛНЫМ документом (от <!DOCTYPE> до </html>)
- CSS должен быть ПОЛНЫМ файлом (минимум 500 строк) с ВСЕМИ стилями
- CSS ОБЯЗАТЕЛЬНО должен содержать:
  * CSS переменные (:root с --primary-color, --secondary-color и т.д.)
  * Яркие цвета и градиенты (linear-gradient)
  * Темный фон с градиентами
  * Подключенные шрифты через Google Fonts
  * Стили для ВСЕХ элементов (hero, цены, таймер, форма, отзывы, подвал)
  * Адаптивный дизайн (@media queries)
- JS должен быть ПОЛНЫМ файлом (минимум 200 строк)
- Используй РЕАЛЬНЫЕ данные из промпта, НЕ заглушки
- ОБЯЗАТЕЛЬНО используй РЕКОМЕНДУЕМЫЕ цвета и шрифты из промпта!
- Все пути к файлам: css/style.css, js/script.js, img/photo_X.jpg"""
