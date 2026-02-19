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
import base64
import os
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
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10
                )
                return True
            elif self.provider == 'anthropic':
                self.client.messages.create(
                    model=self.model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                return True
            elif self.provider == 'google':
                model = self.client.GenerativeModel(model_name=self.model)
                model.generate_content("test")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка проверки подключения к {self.provider}: {e}")
            return False
    
    # Улучшенный системный промпт с четкими инструкциями
    SYSTEM_PROMPT = """Ты - профессиональный веб-разработчик, специализирующийся на создании высококачественных продающих лендингов.

ТВОЯ ЗАДАЧА: Создать ПОЛНЫЙ, РАБОТАЮЩИЙ лендинг с HTML, CSS и JavaScript.

⚠️ КРИТИЧЕСКИ ВАЖНО:
- Используй ВСЕ данные из промпта пользователя; НЕ используй заглушки — только реальные данные.
- HTML: полный (complete), готовый к использованию (production-ready), с чёткой структурой (fully structured). Все блоки из промпта — в указанном порядке.
- CSS: полный и рабочий — все секции оформлены, без пустых блоков. Недопустимо: пустой файл, только комментарии.
- JS: весь описанный функционал реализован (таймер, телефон, карусели, валидация).
- ОБЯЗАТЕЛЬНО используй РЕКОМЕНДУЕМЫЕ цвета и шрифты из промпта; цвета яркие и видимые; шрифты через Google Fonts.
- Формы: ВСЕ собранные поля (размеры, цвета, характеристики), action="send.php".

═══════════════════════════════════════════════════════════════
ТРЕБОВАНИЯ К HTML:
═══════════════════════════════════════════════════════════════

1. СТРУКТУРА: полный документ от <!DOCTYPE html> до </html>, title = название товара из промпта, link на css/style.css, script на js/script.js.

2. ПОРЯДОК БЛОКОВ (как в промпте):
   - Hero: первый кадр (фото/несколько при разных цветах), скидка/акция, короткое описание, форма заказа
   - При наличии видео: блок видео сразу под hero, автозапуск при попадании в viewport
   - Описание товара (абзацы, при необходимости фото)
   - Средняя форма заказа (дубликат формы из hero)
   - При наличии фото: галерея-карусель (минимум 2 фото, 3:4)
   - Отзывы (под товар, с фото или без; фото 3:4)
   - Дубль hero (фото + форма)
   - Подвал: ИП/ООО, УНП, адрес, время работы, email

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
ТРЕБОВАНИЯ К CSS:
═══════════════════════════════════════════════════════════════

CSS должен быть полным и рабочим (complete, production-ready). Все секции оформлены; пустые блоки не допускаются.

Включи: CSS переменные (:root с --primary-color, --secondary-color, --dark-bg и т.д.), reset, стили body/html, темный фон с градиентами, стили для hero, цен, таймера, формы, отзывов, подвала, каруселей; адаптив (mobile-first, @media); переходы и анимации. Недопустимо: пустой файл, только комментарии, отсутствие стилей для форм и секций.

═══════════════════════════════════════════════════════════════
ТРЕБОВАНИЯ К JAVASCRIPT:
═══════════════════════════════════════════════════════════════

JS должен быть полным и рабочим: весь описанный в промпте функционал реализован.

Включи: таймер обратного отсчёта (формат ЧЧ:ММ:СС, обновление каждую секунду), форматирование телефона +375 (__) ___-__-__ и валидацию, карусели (плавная прокрутка, кнопки prev/next, автопрокрутка), валидацию форм, анимации при скролле. Недопустимо: пустой файл, только комментарии.

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
- JSON валидный (экранируй кавычки и переносы строк).
- HTML: полный документ (от <!DOCTYPE> до </html>), все блоки в порядке из промпта.
- CSS: полный и рабочий — переменные, градиенты, стили для всех секций, адаптив, Google Fonts. Без пустых блоков.
- JS: полный и рабочий — таймер, телефон, карусели, валидация.
- Только РЕАЛЬНЫЕ данные из промпта, РЕКОМЕНДУЕМЫЕ цвета и шрифты. Пути: css/style.css, js/script.js, img/..."""
    
    async def analyze_image_style(self, image_path: str, product_name: str = '', description: str = '') -> Dict[str, Any]:
        """
        Анализ изображения товара через Vision API для получения цветов, стиля и шрифтов
        
        Args:
            image_path: Путь к изображению товара
            product_name: Название товара (для контекста)
            description: Описание товара (для контекста)
            
        Returns:
            Словарь с цветами, шрифтами и стилем на основе изображения
        """
        if not self.client:
            raise ValueError(f"{self.provider.upper()} API ключ не установлен или клиент не инициализирован")
        
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}, falling back to text-based analysis")
            return None
        
        # Проверяем размер файла (лимиты для vision API)
        file_size = os.path.getsize(image_path)
        max_size = 20 * 1024 * 1024  # 20MB для большинства vision API
        
        if file_size > max_size:
            logger.warning(f"Image file too large ({file_size / 1024 / 1024:.1f}MB), falling back to text-based analysis")
            return None
        
        try:
            # Читаем изображение
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Формируем промпт для анализа
            analysis_prompt = f"""Проанализируй это изображение товара{" " + product_name if product_name else ""} и предложи:
1. Цветовую палитру для лендинга (5 цветов в hex формате):
   - primary (основной акцентный цвет, должен быть ярким и привлекательным)
   - secondary (вторичный акцент)
   - accent (дополнительный акцент)
   - bg_dark (темный фон)
   - bg_darker (еще более темный фон для контраста)
   
2. Стиль дизайна (modern/elegant/minimalist/bold/playful)
3. Пару шрифтов (названия из Google Fonts, например: "Montserrat", "Inter")

Ответ в формате JSON:
{{
  "colors": {{
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "bg_dark": "#hex",
    "bg_darker": "#hex"
  }},
  "fonts": ["FontName1", "FontName2"],
  "style": "modern|elegant|minimalist|bold|playful",
  "category": "health|beauty|tech|fashion|home|sports|food|general"
}}"""
            
            if self.provider == 'openai':
                return await self._analyze_image_openai(image_base64, analysis_prompt, image_path)
            elif self.provider == 'anthropic':
                return await self._analyze_image_anthropic(image_path, analysis_prompt)
            elif self.provider == 'google':
                return await self._analyze_image_google(image_path, analysis_prompt)
            else:
                logger.warning(f"Vision API not supported for provider {self.provider}, falling back to text-based analysis")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}", exc_info=True)
            return None
    
    async def _analyze_image_openai(self, image_base64: str, prompt: str, image_path: str) -> Optional[Dict[str, Any]]:
        """Анализ изображения через OpenAI Vision API"""
        try:
            # Определяем MIME тип по расширению
            ext = os.path.splitext(image_path)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')
            
            # Используем gpt-4o или gpt-4-turbo для vision
            vision_model = 'gpt-4o' if 'gpt-4o' in self.model.lower() else 'gpt-4o'
            
            response = self.client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Парсим JSON из ответа
            try:
                # Извлекаем JSON из ответа (может быть обернут в markdown код)
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    
                    # Валидация структуры
                    if 'colors' in result and 'fonts' in result:
                        logger.info(f"✓ Successfully analyzed image style via OpenAI Vision: colors={result['colors'].get('primary')}, fonts={result['fonts']}")
                        return result
                    else:
                        logger.warning(f"Invalid structure in vision analysis result: {result}")
                        return None
                else:
                    logger.warning(f"No JSON found in vision analysis response: {content[:200]}")
                    return None
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from vision analysis: {e}, response: {content[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error in OpenAI vision analysis: {e}", exc_info=True)
            return None
    
    async def _analyze_image_anthropic(self, image_path: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Анализ изображения через Anthropic Claude Vision API"""
        try:
            import anthropic
            
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Определяем MIME тип
            ext = os.path.splitext(image_path)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')
            
            message = self.client.messages.create(
                model='claude-3-5-sonnet-20241022',  # Claude поддерживает vision
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": base64.b64encode(image_data).decode('utf-8')
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            content = message.content[0].text
            
            # Парсим JSON
            try:
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    
                    if 'colors' in result and 'fonts' in result:
                        logger.info(f"✓ Successfully analyzed image style via Anthropic Vision: colors={result['colors'].get('primary')}, fonts={result['fonts']}")
                        return result
                    else:
                        logger.warning(f"Invalid structure in vision analysis result: {result}")
                        return None
                else:
                    logger.warning(f"No JSON found in vision analysis response: {content[:200]}")
                    return None
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from vision analysis: {e}, response: {content[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error in Anthropic vision analysis: {e}", exc_info=True)
            return None
    
    async def _analyze_image_google(self, image_path: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Анализ изображения через Google Gemini Vision API"""
        try:
            import google.generativeai as genai
            
            # Загружаем изображение
            import PIL.Image
            image = PIL.Image.open(image_path)
            
            # Используем модель с поддержкой vision
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Google Gemini API синхронный, но мы в async функции - используем asyncio.to_thread или run_in_executor
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: model.generate_content([prompt, image]))
            content = response.text
            
            # Парсим JSON
            try:
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    
                    if 'colors' in result and 'fonts' in result:
                        logger.info(f"✓ Successfully analyzed image style via Google Vision: colors={result['colors'].get('primary')}, fonts={result['fonts']}")
                        return result
                    else:
                        logger.warning(f"Invalid structure in vision analysis result: {result}")
                        return None
                else:
                    logger.warning(f"No JSON found in vision analysis response: {content[:200]}")
                    return None
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from vision analysis: {e}, response: {content[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error in Google vision analysis: {e}", exc_info=True)
            return None
