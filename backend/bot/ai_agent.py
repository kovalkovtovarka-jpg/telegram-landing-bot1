"""
AI-ассистент для сбора данных через диалог
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from backend.generator.llm_client import LLMClient
from backend.config import Config

logger = logging.getLogger(__name__)


class LandingAIAgent:
    """ИИ агент для сбора данных через диалог"""
    
    SYSTEM_PROMPT = """Ты — ассистент по созданию продающих лендингов. Диалог компактный, но структурированный.

=== ПОРЯДОК СБОРА ===

<b>Шаг 1. Главное фото + описание</b>
Попроси прислать ПЕРВЫМ то фото, которое клиент хочет видеть главным (в самом верху лендинга и ещё раз перед формой заявки). И описание товара (название + текст, можно с Wildberries).
По этому фото и описанию автоматически подбираются стиль, цвета и шрифты — не спрашивай про стиль/цвета.

<b>Шаг 2. Остальные фото</b>
Когда есть главное фото и описание — попроси прислать остальные фото для лендинга. Бот видит их количество. После этого переходи к мини-опросу.

<b>Шаг 3. Мини-опрос</b> (задай компактно, можно одним сообщением или двумя)
- Скидка: есть ли скидка и какой процент/текст (например: 30% или «−30%»).
- Цены: старая (до скидки) и новая (со скидкой), например 150 BYN и 99 BYN.
- Подвал сайта: ИП или ООО — название (ФИО для ИП / название компании для ООО), УНП, адрес, телефон, email, при необходимости время работы.
- Заявки из формы: куда отправлять — в Telegram (нужны токен бота и id чата) или на email (указать адрес).
- Распределение фото: кроме главного (hero), какие блоки заполнять — описание, галерея, отзывы. Например: «2 фото в описание, 3 в галерею, 2 в отзывы» или «все в галерею».
- Видео: нужен ли на лендинге блок с видео? Если да — попроси прислать видео потом.

Не растягивай: объединяй вопросы в блоки, не задавай по одному.

=== ФАЙЛЫ ===
- Первое присланное фото = главное (hero), оно же внизу перед формой.
- Остальные фото распределяются по блокам (описание / галерея / отзывы) по ответу клиента в мини-опросе.
- Если клиент пришлёт видео — использовать в блоке «видео».

=== ТЕКУЩЕЕ СОСТОЯНИЕ ===
Режим: {mode}
Этап: {stage}
Собранные данные: {collected_summary}"""
    
    def __init__(self, mode: str):
        """
        Инициализация агента
        
        Args:
            mode: Режим работы - 'SINGLE' или 'MULTI' (выбирается до запуска, после оплаты)
        """
        if mode not in ['SINGLE', 'MULTI']:
            raise ValueError("Mode must be 'SINGLE' or 'MULTI'")
        
        self.mode = mode
        self.llm_client = LLMClient()
        self.conversation_history = []
        self.collected_data = {
            'mode': mode,
            'general_info': {},
            'products': [],
            'current_product_index': 0,
            'stage': 'general_info',
            'files': []
        }
        self.stage = 'general_info'  # general_info -> products -> verification -> generation
        self.max_history_length = 20  # Максимальная длина истории диалога
        
        logger.info(f"AI Agent initialized with mode: {mode}")
    
    async def start_conversation(self) -> str:
        """
        Начать диалог: сначала главное фото + описание, потом остальные фото, затем мини-опрос.
        """
        mode_text = "лендинг для одного товара" if self.mode == 'SINGLE' else "сайт для нескольких товаров"
        greeting = (
            f"Привет! Создам продающий {mode_text}.\n\n"
            "📷 <b>Шаг 1.</b> Отправьте <b>главное фото</b> товара — то, что хотите видеть в самом верху лендинга "
            "и перед формой заявки. И пришлите <b>описание</b> (название + текст, можно с Wildberries).\n\n"
            "По ним подберу стиль, цвета и шрифты. Дальше попрошу остальные фото и несколько коротких вопросов.\n\n"
            "💡 /cancel_ai — отменить"
        )
        self.conversation_history.append({'role': 'assistant', 'content': greeting})
        return greeting
    
    async def process_message(self, message: str, user_id: int, files: List[Dict] = None) -> str:
        """
        Обработать сообщение пользователя и вернуть ответ
        
        Args:
            message: Текст сообщения пользователя
            user_id: ID пользователя
            files: Список файлов (фото/видео), если есть
            
        Returns:
            Ответ агента
        """
        # Обрабатываем файлы, если есть
        if files:
            file_info = await self._process_files(files)
            if file_info:
                message = f"{message}\n\n[Пользователь отправил файл: {file_info}]"
        
        # Добавляем сообщение пользователя в историю
        self.conversation_history.append({
            'role': 'user',
            'content': message
        })
        
        # Извлекаем данные из сообщения
        extracted_data = await self._extract_data(message, self.stage)
        if extracted_data:
            self._update_collected_data(extracted_data)
        
        # Генерируем ответ через LLM
        response = await self._generate_response()
        
        # Добавляем ответ в историю
        self.conversation_history.append({
            'role': 'assistant',
            'content': response
        })
        
        # Проверяем, нужно ли перейти к следующему этапу
        await self._check_stage_transition()
        
        return response
    
    async def _process_files(self, files: List[Dict]) -> Optional[str]:
        """
        Обработать загруженные файлы
        
        Args:
            files: Список файлов с информацией
            
        Returns:
            Описание обработанных файлов
        """
        if not files:
            return None
        
        file_descriptions = []
        for file_info in files:
            file_path = file_info.get('path', '')
            file_type = file_info.get('type', 'photo')  # photo или video
            original_name = file_info.get('original_name') or file_info.get('filename', 'file')
            
            if file_path and os.path.exists(file_path):
                # Определяем, для какого блока предназначен файл на основе текущего этапа и количества файлов
                block = self._determine_file_block(file_type)
                
                file_data = {
                    'path': file_path,
                    'type': file_type,
                    'original_name': original_name,
                    'block': block
                }
                self.collected_data['files'].append(file_data)
                
                file_descriptions.append(f"{file_type} ({original_name})")
        
        if file_descriptions:
            return ", ".join(file_descriptions)
        return None
    
    def _determine_file_block(self, file_type: str) -> str:
        """Определить, для какого блока предназначен файл"""
        files = self.collected_data.get('files', [])
        hero_files = [f for f in files if f.get('block') == 'hero']

        # Первый файл всегда hero (минимальный сценарий: фото + описание)
        if len(files) == 0:
            return 'hero'
        gallery_files = [f for f in files if f.get('block') == 'gallery']
        description_files = [f for f in files if f.get('block') == 'description']
        
        # Если нет hero - это hero
        if not hero_files:
            return 'hero'
        
        # Если есть hero и это видео - может быть middle_video
        if file_type == 'video' and hero_files:
            return 'middle_video'
        
        # Если есть hero и это фото - может быть gallery или description
        if file_type == 'photo' and hero_files:
            # Если мало файлов - скорее всего gallery
            if len(gallery_files) < 3:
                return 'gallery'
            # Если много - description
            elif len(description_files) < 5:
                return 'description'
            # Иначе review
            else:
                return 'review'
        
        return 'gallery'  # По умолчанию
    
    async def _extract_data(self, message: str, stage: str) -> Dict[str, Any]:
        """
        Извлечь структурированные данные из сообщения
        
        Args:
            message: Сообщение пользователя
            stage: Текущий этап
            
        Returns:
            Извлеченные данные
        """
        # Сначала пытаемся простой парсинг (быстрее и дешевле)
        extracted = self._simple_extract_data(message, stage)
        
        # Проверяем, все ли обязательные поля собраны для текущего этапа
        if stage == 'general_info':
            required_fields = ['goal', 'target_audience', 'style']
            general_info = self.collected_data.get('general_info', {})
            # Проверяем, какие обязательные поля еще не собраны
            missing_required = [field for field in required_fields if field not in general_info and field not in extracted]
            # Если есть не собранные обязательные поля, используем LLM
            if missing_required:
                logger.info(f"Missing required fields for general_info: {missing_required}, using LLM extraction")
                llm_extracted = await self._llm_extract_data(message, stage)
                if llm_extracted:
                    # Объединяем результаты простого парсинга и LLM
                    extracted.update(llm_extracted)
        elif stage == 'products' and self.mode == 'SINGLE':
            # Для товаров проверяем обязательные поля
            required_fields = ['product_name', 'product_description', 'new_price']
            products = self.collected_data.get('products', [])
            if products:
                product = products[0]
                missing_required = [field for field in required_fields if field not in product and field not in extracted]
                if missing_required:
                    logger.info(f"Missing required fields for products: {missing_required}, using LLM extraction")
                    llm_extracted = await self._llm_extract_data(message, stage)
                    if llm_extracted:
                        extracted.update(llm_extracted)
            elif not extracted:
                # Если товар еще не создан и простой парсинг ничего не нашел, используем LLM
                llm_extracted = await self._llm_extract_data(message, stage)
                if llm_extracted:
                    extracted.update(llm_extracted)
        elif not extracted and stage in ['general_info', 'products']:
            # Если простой парсинг не дал результатов, используем LLM
            extracted = await self._llm_extract_data(message, stage)
        
        return extracted
    
    def _simple_extract_data(self, message: str, stage: str) -> Dict[str, Any]:
        """Простое извлечение данных через ключевые слова (без LLM)"""
        extracted = {}
        message_lower = message.lower()
        
        if stage == 'general_info':
            # Цель сайта
            if any(word in message_lower for word in ['продаж', 'продать', 'продаю']):
                extracted['goal'] = 'продажа'
            elif any(word in message_lower for word in ['заявк', 'обратн', 'контакт']):
                extracted['goal'] = 'заявки'
            elif any(word in message_lower for word in ['каталог', 'категори']):
                extracted['goal'] = 'каталог'
            
            # Стиль
            if any(word in message_lower for word in ['минимал', 'минималист', 'простой', 'чист']):
                extracted['style'] = 'минималистичный'
            elif any(word in message_lower for word in ['премиум', 'люкс', 'дорог', 'элит']):
                extracted['style'] = 'премиум'
            elif any(word in message_lower for word in ['ярк', 'красочн', 'цветн']):
                extracted['style'] = 'яркий'
            elif any(word in message_lower for word in ['строг', 'делов', 'офиц']):
                extracted['style'] = 'строгий'
            
            # Уведомления
            if 'email' in message_lower or '@' in message:
                extracted['notification_type'] = 'email'
            elif 'telegram' in message_lower or 'телеграм' in message_lower:
                extracted['notification_type'] = 'telegram'

            # Скидка в hero (процент или текст)
            import re
            discount_match = re.search(r'скидк[аи]\s*[:\s]*(\d+)\s*%?|(\d+)\s*%\s*скидк', message_lower)
            if discount_match:
                pct = discount_match.group(1) or discount_match.group(2)
                if pct:
                    extracted['hero_discount'] = f'-{pct}%'
                    extracted['hero_discount_position'] = 'top_right'

            # Минимальный сценарий: если пользователь прислал текст как описание товара (длинное сообщение)
            # — считаем первую строку названием, весь текст — описанием
            if len(message.strip()) > 20:
                lines = [line.strip() for line in message.strip().split('\n') if line.strip()]
                extracted['product_name'] = (lines[0][:100] if lines else 'Товар')
                extracted['product_description'] = message.strip()
        
        elif stage == 'products':
            # Описание/название: длинное сообщение — первая строка название, весь текст описание
            if len(message.strip()) > 20:
                lines = [line.strip() for line in message.strip().split('\n') if line.strip()]
                extracted['product_name'] = (lines[0][:100] if lines else 'Товар')
                extracted['product_description'] = message.strip()
            # Цена (ищем числа с валютой)
            import re
            price_match = re.search(r'(\d+)\s*(?:BYN|руб|₽|\$|€)', message, re.IGNORECASE)
            if price_match:
                extracted['new_price'] = f"{price_match.group(1)} BYN"
            old_price_match = re.search(r'(?:было|старая|ранее|раньше)[:\s]+(\d+)\s*(?:BYN|руб|₽)', message, re.IGNORECASE)
            if old_price_match:
                extracted['old_price'] = f"{old_price_match.group(1)} BYN"
            # Скидка
            discount_match = re.search(r'скидк[аи]\s*[:\s]*(\d+)\s*%?|(\d+)\s*%\s*скидк', message_lower, re.IGNORECASE)
            if discount_match:
                pct = discount_match.group(1) or discount_match.group(2)
                if pct:
                    extracted['hero_discount'] = f'-{pct}%'
                    extracted['hero_discount_position'] = 'top_right'
        return extracted
    
    async def _llm_extract_data(self, message: str, stage: str) -> Dict[str, Any]:
        """Извлечение данных через LLM (только если простой парсинг не помог)"""
        extraction_prompt = f"""Извлеки структурированные данные из следующего сообщения пользователя.

Текущий этап: {stage}
Режим: {self.mode}

Сообщение: {message}

Собранные данные до этого сообщения:
{self._get_collected_summary()}

Извлеки только те данные, которые явно указаны в сообщении. Верни JSON с извлеченными данными.

Для этапа general_info извлекай:
- goal, target_audience, style, language
- notification_type (email/telegram)
- notification_email (если заявки на почту)
- notification_telegram_token, notification_telegram_chat_id (если заявки в Telegram)
- footer: type (ip/ooo), fio (для ИП), company_name (для ООО), unp, address, phone, email, schedule
- hero_discount (текст скидки, например "-30%"), hero_discount_position (top_right)
- photo_description_count, photo_gallery_count, photo_reviews_count (числа: сколько фото в блок описание, галерея, отзывы)
- want_video (true/false — нужен ли блок с видео)

Для этапа products (SINGLE) извлекай:
- product_name, product_description, old_price, new_price
- hero_discount, hero_discount_position
- characteristics (массив), utp, guarantees, delivery_payment, cta

Для этапа products (MULTI) извлекай:
- products_count (количество товаров)
- product_data (данные о товаре)

Верни только JSON, без дополнительного текста."""
        
        try:
            import json
            import re
            
            extraction_messages = [
                {"role": "system", "content": "Ты помощник для извлечения структурированных данных из текста. Верни только валидный JSON."},
                {"role": "user", "content": extraction_prompt}
            ]
            
            response_text = await self._call_llm_for_dialogue(extraction_messages, "Верни только JSON с извлеченными данными.")
            
            # Парсим JSON из ответа
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
                return extracted
        except Exception as e:
            logger.error(f"Error extracting data via LLM: {e}")
        
        return {}
    
    def _update_collected_data(self, extracted_data: Dict[str, Any]):
        """Обновить собранные данные"""
        if not extracted_data:
            return
        
        logger.info(f"Updating collected data for stage {self.stage}: {list(extracted_data.keys())}")
        
        if self.stage == 'general_info':
            self.collected_data['general_info'].update(
                {k: v for k, v in extracted_data.items() if k not in ('product_name', 'product_description')}
            )
            # Минимальный сценарий: описание из первого сообщения — сразу в товар (SINGLE)
            if self.mode == 'SINGLE' and (extracted_data.get('product_name') or extracted_data.get('product_description')):
                if not self.collected_data['products']:
                    self.collected_data['products'].append({})
                self.collected_data['products'][0].update({
                    k: v for k, v in extracted_data.items()
                    if k in ('product_name', 'product_description')
                })
            logger.info(f"General info after update: {list(self.collected_data['general_info'].keys())}")
        elif self.stage == 'products':
            # Поля подвала и уведомлений из мини-опроса могли прийти вместе с ценами — кладём в general_info
            footer_keys = {'notification_type', 'notification_email', 'notification_telegram_token', 'notification_telegram_chat_id',
                           'type', 'fio', 'company_name', 'unp', 'address', 'phone', 'email', 'schedule',
                           'photo_description_count', 'photo_gallery_count', 'photo_reviews_count', 'want_video'}
            general_from_extract = {k: v for k, v in extracted_data.items() if k in footer_keys}
            if general_from_extract:
                self.collected_data['general_info'].update(general_from_extract)
            if self.mode == 'SINGLE':
                if not self.collected_data['products']:
                    self.collected_data['products'].append({})
                product_extract = {k: v for k, v in extracted_data.items() if k not in footer_keys}
                self.collected_data['products'][0].update(product_extract)
            else:
                # Для нескольких товаров
                if 'products_count' in extracted_data:
                    count = extracted_data['products_count']
                    # Инициализируем список товаров
                    while len(self.collected_data['products']) < count:
                        self.collected_data['products'].append({})
                elif 'product_data' in extracted_data:
                    # Обновляем текущий товар
                    idx = self.collected_data['current_product_index']
                    if idx < len(self.collected_data['products']):
                        self.collected_data['products'][idx].update(extracted_data['product_data'])
    
    async def _generate_response(self) -> str:
        """Сгенерировать ответ через LLM"""
        # Формируем системный промпт с информацией о прогрессе
        stage_info = self._get_stage_info()
        system_prompt = self.SYSTEM_PROMPT.format(
            mode="Лендинг для одного товара" if self.mode == 'SINGLE' else "Сайт для нескольких товаров",
            stage=self.stage,
            collected_summary=self._get_collected_summary()
        )
        
        # Добавляем информацию о прогрессе в системный промпт
        system_prompt += f"\n\n{stage_info}"
        
        # Формируем историю диалога для LLM
        messages = []
        
        # Добавляем системное сообщение
        if Config.LLM_PROVIDER == 'openai':
            messages.append({"role": "system", "content": system_prompt})
        else:
            # Для других провайдеров системный промпт обрабатывается отдельно
            pass
        
        # Ограничиваем историю диалога для экономии токенов
        # Оставляем последние N сообщений (системное + последние сообщения)
        max_history = min(self.max_history_length, len(self.conversation_history))
        recent_history = self.conversation_history[-max_history:] if max_history > 0 else []
        
        for msg in recent_history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Периодически очищаем старую историю, если она слишком длинная
        if len(self.conversation_history) > self.max_history_length * 2:
            # Оставляем только последние сообщения
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            logger.debug(f"Cleaned conversation history, kept last {self.max_history_length} messages")
        
        # Генерируем ответ через LLM
        try:
            # Используем прямой вызов LLM API для диалога
            response_text = await self._call_llm_for_dialogue(messages, system_prompt)
            
            # Добавляем информацию о прогрессе в начало ответа
            if stage_info:
                response_text = f"{stage_info}\n\n{response_text}"
            
            return response_text
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "Извините, произошла ошибка. Пожалуйста, попробуйте еще раз."
    
    def _get_stage_info(self) -> str:
        """Получить информацию о текущем этапе для показа пользователю"""
        stage_map = {
            'general_info': ('1/4', 'Общая информация'),
            'products': ('2/4', 'Сбор данных о товарах'),
            'verification': ('3/4', 'Проверка данных'),
            'generation': ('4/4', 'Готово к генерации')
        }
        
        stage_num, stage_name = stage_map.get(self.stage, ('?/4', 'Неизвестный этап'))
        return f"📋 <b>Этап {stage_num}: {stage_name}</b>"
    
    async def _call_llm_for_dialogue(self, messages: List[Dict], system_prompt: str) -> str:
        """Вызов LLM для диалога (не для генерации кода) с таймаутом"""
        import asyncio
        
        # Таймаут для диалога (меньше, чем для генерации кода)
        timeout = min(Config.LLM_TIMEOUT, 60)  # Максимум 60 секунд для диалога
        
        try:
            if Config.LLM_PROVIDER == 'openai':
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY, timeout=timeout)
                
                # Формируем сообщения с системным промптом
                llm_messages = [{"role": "system", "content": system_prompt}]
                llm_messages.extend(messages)
                
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=Config.LLM_MODEL,
                        messages=llm_messages,
                        temperature=0.7,  # Немного выше для более естественного диалога
                        max_tokens=500  # Ограничиваем длину ответа
                    ),
                    timeout=timeout
                )
                return response.choices[0].message.content.strip()
            
            elif Config.LLM_PROVIDER == 'anthropic':
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY, timeout=timeout)
                
                # Anthropic использует другой формат
                response = await asyncio.wait_for(
                    client.messages.create(
                        model=Config.LLM_MODEL,
                        max_tokens=500,
                        system=system_prompt,
                        messages=messages
                    ),
                    timeout=timeout
                )
                return response.content[0].text.strip()
            
            elif Config.LLM_PROVIDER == 'google':
                import google.generativeai as genai
                genai.configure(api_key=Config.GOOGLE_API_KEY)
                model = genai.GenerativeModel(Config.LLM_MODEL)
                
                # Формируем промпт для Google
                prompt_parts = [system_prompt]
                for msg in messages:
                    prompt_parts.append(f"{msg['role']}: {msg['content']}")
                prompt_parts.append("assistant:")
                
                response = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, "\n".join(prompt_parts)),
                    timeout=timeout
                )
                return response.text.strip()
            
            else:
                raise ValueError(f"Unsupported LLM provider: {Config.LLM_PROVIDER}")
        except asyncio.TimeoutError:
            logger.error(f"LLM dialogue timeout after {timeout} seconds")
            raise Exception(f"Превышено время ожидания ответа ({timeout} сек). Попробуйте еще раз.")
        except Exception as e:
            logger.error(f"Error calling LLM for dialogue: {e}", exc_info=True)
            raise
    
    def _get_collected_summary(self) -> str:
        """Получить краткую сводку собранных данных"""
        summary = []
        
        if self.collected_data['general_info']:
            summary.append(f"Общая информация: {len(self.collected_data['general_info'])} полей")
        
        if self.collected_data['products']:
            summary.append(f"Товары: {len(self.collected_data['products'])}")
        
        if self.collected_data['files']:
            summary.append(f"Файлы: {len(self.collected_data['files'])}")
        
        return "; ".join(summary) if summary else "Данные еще не собраны"
    
    async def _check_stage_transition(self):
        """Проверить, нужно ли перейти к следующему этапу"""
        if self.stage == 'general_info':
            # Проверяем, собрана ли общая информация
            required_fields = ['goal', 'target_audience', 'style']
            general_info = self.collected_data.get('general_info', {})
            collected_fields = [field for field in required_fields if field in general_info]
            missing_fields = [field for field in required_fields if field not in general_info]
            
            logger.info(f"Stage transition check (general_info): required={required_fields}, collected={collected_fields}, missing={missing_fields}")
            logger.info(f"General info keys: {list(general_info.keys())}")
            
            if all(field in general_info for field in required_fields):
                self.stage = 'products'
                self.collected_data['stage'] = 'products'
                logger.info("Transitioned to products stage")
            else:
                logger.info(f"Not transitioning: missing fields {missing_fields}")
        
        elif self.stage == 'products':
            # Проверяем, собраны ли данные о товарах
            if self.mode == 'SINGLE':
                required_fields = ['product_name', 'product_description', 'new_price']
                if self.collected_data['products'] and all(
                    field in self.collected_data['products'][0] 
                    for field in required_fields
                ):
                    self.stage = 'verification'
                    self.collected_data['stage'] = 'verification'
                    logger.info("Transitioned to verification stage")
            else:  # MULTI
                # Проверяем, что все товары собраны
                if (self.collected_data.get('products_count') and 
                    len(self.collected_data['products']) >= self.collected_data['products_count']):
                    self.stage = 'verification'
                    self.collected_data['stage'] = 'verification'
                    logger.info("Transitioned to verification stage")
        
        elif self.stage == 'verification':
            # Проверяем, все ли данные собраны перед переходом к генерации
            is_complete, missing = self.check_completeness()
            if is_complete:
                # После проверки переходим к генерации
                self.stage = 'generation'
                self.collected_data['stage'] = 'generation'
                logger.info("Transitioned to generation stage - all data complete")
            else:
                logger.info(f"Verification stage: missing data - {missing}, staying in verification")
    
    def check_completeness(self) -> Tuple[bool, List[str]]:
        """
        Проверить, все ли данные собраны
        
        Returns:
            (полнота, список недостающих полей)
        """
        missing = []
        
        # Проверяем общую информацию
        required_general = ['goal', 'target_audience', 'style']
        # notification_type не обязателен - используем значение по умолчанию
        for field in required_general:
            if field not in self.collected_data['general_info']:
                missing.append(f"Общая информация: {field}")
        
        # Если notification_type не указан, используем значение по умолчанию
        if 'notification_type' not in self.collected_data['general_info']:
            self.collected_data['general_info']['notification_type'] = 'telegram'
        
        # Для лендинга одного товара обязательно хотя бы одно фото для главного изображения
        if self.mode == 'SINGLE':
            if not self.collected_data.get('files'):
                missing.append("Фото товара для лендинга (хотя бы одно изображение)")
        
        # Проверяем товары
        if self.mode == 'SINGLE':
            required_product = ['product_name', 'product_description', 'new_price']
            if not self.collected_data['products']:
                missing.append("Товар: все поля")
            else:
                for field in required_product:
                    if field not in self.collected_data['products'][0]:
                        missing.append(f"Товар: {field}")
        else:  # MULTI
            if not self.collected_data.get('products_count'):
                missing.append("Количество товаров")
            elif len(self.collected_data['products']) < self.collected_data['products_count']:
                missing.append(f"Данные о товарах ({len(self.collected_data['products'])}/{self.collected_data['products_count']})")
        
        return len(missing) == 0, missing
    
    def build_final_prompt(self) -> str:
        """
        Сформировать финальный структурированный промпт для gpt-4o
        
        Returns:
            Технический промпт для генерации
        """
        prompt = f"""Создай {'лендинг для одного товара' if self.mode == 'SINGLE' else 'многостраничный сайт для нескольких товаров'}.

=== ОБЩАЯ ИНФОРМАЦИЯ ===
Цель: {self.collected_data['general_info'].get('goal', 'продажа')}
Аудитория: {self.collected_data['general_info'].get('target_audience', 'не указана')}
Стиль: {self.collected_data['general_info'].get('style', 'современный')}
Язык: {self.collected_data['general_info'].get('language', 'ru')}
Уведомления: {self.collected_data['general_info'].get('notification_type', 'telegram')}

=== ТОВАРЫ ===
"""
        
        if self.mode == 'SINGLE':
            product = self.collected_data['products'][0] if self.collected_data['products'] else {}
            prompt += f"""
Товар 1:
- Название: {product.get('product_name', 'Товар')}
- Описание: {product.get('product_description', '')}
- Боль клиента: {product.get('customer_pain', '')}
- Решение: {product.get('solution', '')}
- Цена: {product.get('new_price', '')} (было: {product.get('old_price', '')})
- УТП: {product.get('utp', '')}
- Характеристики: {', '.join(product.get('characteristics', []))}
"""
        else:
            for i, product in enumerate(self.collected_data['products'], 1):
                prompt += f"""
Товар {i}:
- Название: {product.get('product_name', 'Товар')}
- Описание: {product.get('product_description', '')}
- Цена: {product.get('new_price', '')}
"""
        
        prompt += f"""
=== ФАЙЛЫ ===
"""
        for file_info in self.collected_data['files']:
            prompt += f"- {file_info.get('type', 'photo')}: {file_info.get('original_name', 'file')}\n"
        
        prompt += """
=== ТРЕБОВАНИЯ ===
- Адаптивный дизайн
- HTML5, CSS3, vanilla JavaScript
- Оптимизация для конверсии
- SEO база
"""
        
        return prompt
    
    def convert_to_user_data(self) -> Dict[str, Any]:
        """
        Преобразовать данные агента в формат user_data для CodeGenerator
        
        Returns:
            Данные в формате user_data
        """
        user_data = {
            'landing_type': 'single_product' if self.mode == 'SINGLE' else 'multi_product',
        }
        
        # Общая информация
        general = self.collected_data['general_info']
        user_data['design_style'] = general.get('style', 'vibrant')
        user_data['notification_type'] = general.get('notification_type', 'telegram')
        user_data['notification_email'] = general.get('notification_email', '')
        user_data['notification_telegram_token'] = general.get('notification_telegram_token', '')
        user_data['notification_telegram_chat_id'] = general.get('notification_telegram_chat_id', '')
        user_data['preferred_colors'] = general.get('preferred_colors', '')
        # Подвал (ИП/ООО)
        user_data['footer_info'] = {
            'type': general.get('type', 'ip'),
            'fio': general.get('fio', ''),
            'company_name': general.get('company_name', ''),
            'unp': general.get('unp', ''),
            'address': general.get('address', ''),
            'phone': general.get('phone', ''),
            'email': general.get('email', ''),
            'schedule': general.get('schedule', ''),
        }
        
        # Товары
        if self.mode == 'SINGLE':
            if self.collected_data.get('products') and len(self.collected_data['products']) > 0:
                product = self.collected_data['products'][0]
                user_data['product_name'] = product.get('product_name', 'Товар')
                user_data['description_text'] = product.get('product_description', '')
                user_data['new_price'] = product.get('new_price', '')
                user_data['old_price'] = product.get('old_price', '')
                user_data['characteristics'] = product.get('characteristics', [])
                user_data['hero_discount'] = product.get('hero_discount') or general.get('hero_discount', '')
                user_data['hero_discount_position'] = product.get('hero_discount_position') or general.get('hero_discount_position', 'top_right')
                # Определяем текст с Wildberries — в промпте уберём воду и усилим маркетинг
                desc = user_data.get('description_text', '') or ''
                try:
                    from backend.utils.text_processor import TextProcessor
                    user_data['description_is_wildberries'] = TextProcessor.is_wildberries_text(desc)
                except Exception:
                    user_data['description_is_wildberries'] = False
            else:
                # Если товар не собран, используем значения по умолчанию
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("Products not collected, using default values")
                user_data['product_name'] = 'Товар'
                user_data['description_text'] = 'Описание товара'
                user_data['new_price'] = '99'
                user_data['old_price'] = ''
                user_data['characteristics'] = []
                user_data['description_is_wildberries'] = False
                user_data['hero_discount'] = ''
                user_data['hero_discount_position'] = 'top_right'
        else:
            user_data['description_is_wildberries'] = False

        # Файлы: первое = hero, остальные распределяем по блокам (описание, галерея, отзывы)
        files = self.collected_data['files']
        if files:
            hero_file = next((f for f in files if f.get('block') == 'hero'), files[0] if files else None)
            if hero_file:
                user_data['hero_media'] = hero_file['path']
                user_data['hero_media_type'] = 'photo' if hero_file.get('type') == 'photo' else 'video'
                user_data['hero_media_format'] = os.path.splitext(hero_file['path'])[1][1:] or 'jpg'
                user_data['hero_media_filename'] = hero_file.get('original_name') or hero_file.get('filename') or os.path.basename(hero_file['path']) or 'hero.jpg'

            middle_video = next((f for f in files if f.get('block') == 'middle_video'), None)
            if middle_video:
                user_data['middle_video'] = middle_video['path']

            # Распределение остальных фото по блокам из мини-опроса (если заданы счётчики)
            desc_count = general.get('photo_description_count')
            gallery_count = general.get('photo_gallery_count')
            reviews_count = general.get('photo_reviews_count')
            non_hero = [f for f in files if f.get('block') != 'hero' and f.get('type') == 'photo']
            if desc_count is not None or gallery_count is not None or reviews_count is not None:
                try:
                    d = int(desc_count) if desc_count is not None else 0
                    g = int(gallery_count) if gallery_count is not None else 0
                    r = int(reviews_count) if reviews_count is not None else 0
                    idx = 0
                    if d > 0 and idx + d <= len(non_hero):
                        user_data['description_photos'] = [f['path'] for f in non_hero[idx:idx + d]]
                        idx += d
                    if g > 0 and idx + g <= len(non_hero):
                        user_data['middle_gallery'] = [f['path'] for f in non_hero[idx:idx + g]]
                        idx += g
                    if r > 0 and idx + r <= len(non_hero):
                        user_data['reviews'] = [{'photo': f['path'], 'name': '', 'text': ''} for f in non_hero[idx:idx + r]]
                except (TypeError, ValueError):
                    pass
            # Если счётчики не заданы — используем текущее распределение по block
            if 'description_photos' not in user_data:
                description_files = [f for f in files if f.get('block') == 'description']
                if description_files:
                    user_data['description_photos'] = [f['path'] for f in description_files]
            if 'middle_gallery' not in user_data:
                gallery_files = [f for f in files if f.get('block') == 'gallery']
                if gallery_files:
                    user_data['middle_gallery'] = [f['path'] for f in gallery_files]
            if 'reviews' not in user_data:
                review_files = [f for f in files if f.get('block') == 'review']
                if review_files:
                    user_data['reviews'] = [{'photo': f['path'], 'name': '', 'text': ''} for f in review_files]

        return user_data
    
    def validate_data(self) -> List[str]:
        """
        Валидация собранных данных
        
        Returns:
            Список ошибок валидации (пустой, если все ОК)
        """
        errors = []
        
        # Валидация общей информации
        general = self.collected_data.get('general_info', {})
        
        # Проверка notification_type (необязательная - можно использовать значения по умолчанию)
        notification_type = general.get('notification_type', 'telegram')
        if notification_type == 'email':
            contact = general.get('contact_info', '')
            if contact and '@' not in str(contact):
                errors.append("Для email уведомлений нужен корректный email адрес")
            # Если contact_info не указан, используем значение по умолчанию
        elif notification_type == 'telegram':
            contact = general.get('contact_info', '')
            # Если contact_info не указан, это не критично - можно использовать значение по умолчанию
            if contact and not contact.startswith('@') and not contact.isdigit():
                errors.append("Для telegram уведомлений нужен username (@username) или ID")
        
        # Валидация товаров
        if self.mode == 'SINGLE':
            products = self.collected_data.get('products', [])
            if products:
                product = products[0]
                
                # Проверка цены
                new_price = product.get('new_price', '')
                if new_price:
                    import re
                    price_match = re.search(r'(\d+)', str(new_price))
                    if not price_match or int(price_match.group(1)) <= 0:
                        errors.append("Цена должна быть положительным числом")
                
                # Проверка старой цены (если указана)
                old_price = product.get('old_price', '')
                if old_price and new_price:
                    new_price_num = int(re.search(r'(\d+)', str(new_price)).group(1)) if re.search(r'(\d+)', str(new_price)) else 0
                    old_price_num = int(re.search(r'(\d+)', str(old_price)).group(1)) if re.search(r'(\d+)', str(old_price)) else 0
                    if old_price_num <= new_price_num:
                        errors.append("Старая цена должна быть больше новой")
        else:  # MULTI
            products = self.collected_data.get('products', [])
            products_count = self.collected_data.get('products_count', 0)
            if products_count > 0 and len(products) < products_count:
                errors.append(f"Не хватает данных о товарах ({len(products)}/{products_count})")
        
        return errors
    
    def serialize_state(self) -> Dict[str, Any]:
        """
        Сериализовать состояние агента для сохранения в БД
        
        Returns:
            Словарь с состоянием агента
        """
        return {
            'mode': self.mode,
            'stage': self.stage,
            'collected_data': self.collected_data,
            'conversation_history': self.conversation_history[-self.max_history_length:]  # Сохраняем только последние N сообщений
        }
    
    @classmethod
    def from_serialized_state(cls, state: Dict[str, Any]) -> 'LandingAIAgent':
        """
        Восстановить агента из сериализованного состояния
        
        Args:
            state: Словарь с состоянием агента
            
        Returns:
            Восстановленный экземпляр LandingAIAgent
        """
        agent = cls(state['mode'])
        agent.stage = state.get('stage', 'general_info')
        agent.collected_data = state.get('collected_data', {
            'mode': state['mode'],
            'general_info': {},
            'products': [],
            'current_product_index': 0,
            'stage': agent.stage,
            'files': []
        })
        agent.conversation_history = state.get('conversation_history', [])
        
        logger.info(f"AI Agent restored from state: mode={agent.mode}, stage={agent.stage}")
        return agent

