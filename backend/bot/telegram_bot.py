"""
Telegram бот для генерации лендингов
"""
import asyncio
import logging
import os
import warnings
import re
import shutil
from typing import Dict, Any, Optional
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChatMember,
    MenuButtonCommands,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from backend.config import Config
from backend.generator.code_generator import CodeGenerator
from backend.generator.template_loader import TemplateLoader
from backend.utils.text_processor import TextProcessor
try:
    from template_selector import TemplateSelector
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from template_selector import TemplateSelector
from backend.database.database import SessionLocal, init_db
from backend.database.models import User, Project, Generation, UserState
from backend.utils.rate_limiter import rate_limiter

# Импорт обработчиков (используются только для notification_handler в _handle_notification_data)
from backend.bot.handlers import (
    HeroHandler,
    ProductHandler,
    TimerHandler,
    PriceHandler,
    FormHandler,
    MiddleBlockHandler,
    DescriptionHandler,
    ReviewsHandler,
    FooterHandler,
    NotificationHandler
)

# Логирование (уровень для внешних библиотек — чтобы не писать токен бота в URL в логах)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Состояния для AI-агента
AI_MODE_SELECTION = 1
AI_CONVERSATION = 2
AI_GENERATING = 3


# Форматы файлов с вариациями для надежности
FILE_FORMATS = {
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

# Соотношения сторон для медиа
ASPECT_RATIOS = {
    '3:4': {'name': '3:4', 'description': 'Стандартное соотношение'},
    '9:16': {'name': '9:16', 'description': 'Вертикальное (как в телефоне)'},
    'custom': {'name': 'Другое', 'description': 'Укажите своё соотношение'}
}


class LandingBot:
    """Telegram бот для генерации лендингов"""
    
    def __init__(self):
        """Инициализация бота"""
        self.config = Config
        self.app = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        # Компоненты
        templates = self._load_json('landing-templates.json')
        logic = self._load_json('template-selection-logic.json')
        
        self.template_selector = TemplateSelector(templates, logic)
        self.code_generator = CodeGenerator()
        self.template_loader = TemplateLoader()
        
        # Инициализация обработчиков
        self.hero_handler = HeroHandler(self)
        self.product_handler = ProductHandler(self)
        self.timer_handler = TimerHandler(self)
        self.price_handler = PriceHandler(self)
        self.form_handler = FormHandler(self)
        self.middle_block_handler = MiddleBlockHandler(self)
        self.description_handler = DescriptionHandler(self)
        self.reviews_handler = ReviewsHandler(self)
        self.footer_handler = FooterHandler(self)
        self.notification_handler = NotificationHandler(self)
        
        # AI-агенты для пользователей (user_id -> agent)
        self.ai_agents = {}
        # Время последней активности для каждого агента (user_id -> timestamp)
        self.ai_agents_last_activity = {}
        
        # Регистрация handlers
        self._register_handlers()
        
        # Запускаем периодическую очистку неактивных агентов
        self._start_ai_agents_cleanup_task()
        
        # Установка меню команд (будет вызвана при запуске)
        self._setup_menu_commands()
        
        # Главное меню клавиатуры
        self.main_keyboard = self._create_main_keyboard()
    
    def _load_json(self, path: str) -> Dict:
        """Загрузка JSON файла"""
        import json
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    # ==================== Работа с UserState в БД ====================
    
    def _save_user_data(self, user_id: int, data: Dict[str, Any], state: Optional[str] = None, conversation_type: Optional[str] = None):
        """Сохранение данных пользователя в БД"""
        db = SessionLocal()
        try:
            user_id_str = str(user_id)
            user_state = db.query(UserState).filter(
                UserState.user_id == user_id_str
            ).first()
            
            if user_state:
                user_state.data = data
                if state is not None:
                    user_state.state = state
                if conversation_type is not None:
                    user_state.conversation_type = conversation_type
                user_state.updated_at = datetime.utcnow()
            else:
                user_state = UserState(
                    user_id=user_id_str,
                    data=data,
                    state=state,
                    conversation_type=conversation_type
                )
                db.add(user_state)
            
            db.commit()
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получение данных пользователя из БД"""
        db = SessionLocal()
        try:
            user_id_str = str(user_id)
            user_state = db.query(UserState).filter(
                UserState.user_id == user_id_str
            ).first()
            
            if user_state:
                return user_state.data.copy() if user_state.data else {}
            return {}
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return {}
        finally:
            db.close()
    
    def _clear_user_data(self, user_id: int):
        """Очистка данных пользователя из БД"""
        db = SessionLocal()
        try:
            user_id_str = str(user_id)
            user_state = db.query(UserState).filter(
                UserState.user_id == user_id_str
            ).first()
            
            if user_state:
                db.delete(user_state)
                db.commit()
        except Exception as e:
            logger.error(f"Error clearing user data: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _update_user_data(self, user_id: int, **kwargs):
        """Обновление конкретных полей данных пользователя"""
        data = self._get_user_data(user_id)
        data.update(kwargs)
        self._save_user_data(user_id, data)
    
    def _save_ai_agent_state(self, user_id: int, agent):
        """
        Сохранить состояние AI-агента в БД
        
        Args:
            user_id: ID пользователя
            agent: Экземпляр LandingAIAgent
        """
        try:
            agent_state = agent.serialize_state()
            # Сохраняем состояние агента в данных пользователя
            user_data = self._get_user_data(user_id)
            user_data['ai_agent_state'] = agent_state
            user_data['ai_agent_active'] = True
            
            # Сохраняем в БД с состоянием ConversationHandler
            self._save_user_data(
                user_id, 
                user_data, 
                state='AI_CONVERSATION',
                conversation_type='ai_agent'
            )
            logger.debug(f"AI agent state saved for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving AI agent state for user {user_id}: {e}", exc_info=True)
    
    async def _restore_ai_agents_from_db(self):
        """
        Восстановить AI-агентов из БД при старте бота
        Отправляет уведомление пользователям о восстановлении диалога
        """
        db = SessionLocal()
        try:
            from backend.bot.ai_agent import LandingAIAgent
            
            # Находим всех пользователей с активными AI-агентами
            active_agents = db.query(UserState).filter(
                UserState.conversation_type == 'ai_agent',
                UserState.state == 'AI_CONVERSATION'
            ).all()
            
            restored_count = 0
            for user_state in active_agents:
                try:
                    user_id = int(user_state.user_id)
                    user_data = user_state.data or {}
                    
                    if 'ai_agent_state' in user_data:
                        agent_state = user_data['ai_agent_state']
                        agent = LandingAIAgent.from_serialized_state(agent_state)
                        
                        # Восстанавливаем агента
                        self.ai_agents[user_id] = agent
                        
                        # Восстанавливаем время последней активности (если есть)
                        if 'last_activity' in user_data:
                            import time
                            self.ai_agents_last_activity[user_id] = user_data['last_activity']
                        else:
                            # Если нет времени активности, ставим текущее время минус 5 минут
                            # чтобы не удалить сразу при очистке
                            import time
                            self.ai_agents_last_activity[user_id] = time.time() - 300
                        
                        restored_count += 1
                        logger.info(f"Restored AI agent for user {user_id}, stage: {agent.stage}")
                        
                        # Отправляем уведомление пользователю о восстановлении диалога
                        try:
                            # Получаем chat_id из user_data или из UserState
                            chat_id = user_data.get('chat_id')
                            if not chat_id:
                                # Пытаемся получить из User модели
                                db_user = db.query(User).filter(User.telegram_id == str(user_id)).first()
                                if db_user:
                                    chat_id = int(db_user.telegram_id)
                            
                            if chat_id:
                                stage_info = agent._get_stage_info()
                                await self.app.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"✅ Диалог восстановлен. Продолжаем с этапа: {stage_info}\n\n"
                                         f"Вы можете продолжить работу с AI-ассистентом.",
                                    parse_mode='HTML'
                                )
                                logger.info(f"Sent restoration notification to user {user_id}")
                        except Exception as notify_error:
                            logger.warning(f"Could not send restoration notification to user {user_id}: {notify_error}")
                    else:
                        # Если нет состояния агента, но есть запись - очищаем
                        logger.warning(f"User {user_id} has ai_agent conversation_type but no agent state, clearing")
                        self._clear_user_data(user_id)
                except Exception as e:
                    logger.error(f"Error restoring AI agent for user {user_state.user_id}: {e}", exc_info=True)
                    # Очищаем некорректное состояние
                    try:
                        self._clear_user_data(int(user_state.user_id))
                    except Exception:
                        pass
            
            if restored_count > 0:
                logger.info(f"Restored {restored_count} AI agents from database")
        except Exception as e:
            logger.error(f"Error restoring AI agents from database: {e}", exc_info=True)
        finally:
            db.close()
    
    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        # Команда /start
        self.app.add_handler(CommandHandler("start", self.start_command))
        
        # Команда /help
        self.app.add_handler(CommandHandler("help", self.help_command))
        
        # Команда /myid - узнать свой Telegram ID
        self.app.add_handler(CommandHandler("myid", self.myid_command))
        
        # Команда /stats (только для админов)
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        # Команда /admin — панель администратора
        self.app.add_handler(CommandHandler("admin", self.admin_command))
        # Обработчик кнопок админ-панели
        self.app.add_handler(CallbackQueryHandler(self.handle_admin_callback, pattern="^admin_"))
        # Обработка текста рассылки (когда админ ввёл сообщение для рассылки)
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_admin_broadcast_message
        ), group=0)
        # Команда отмены AI-режима
        self.app.add_handler(CommandHandler("cancel_ai", self.cancel_ai_command))
        
        # Подавляем предупреждение PTB: при per_message=False CallbackQueryHandler не привязан к сообщению (приемлемо для нашего flow)
        warnings.filterwarnings("ignore", message=".*per_message.*CallbackQueryHandler.*", category=UserWarning)
        # ConversationHandler для AI-агента (группа 1 - приоритет)
        ai_agent_handler = ConversationHandler(
            entry_points=[
                CommandHandler("ai", self.create_mode_selection_command),
                CommandHandler("create_ai", self.create_mode_selection_command),
                MessageHandler(filters.TEXT & filters.Regex("^🤖 AI-ассистент$"), self.create_mode_selection_command),
                MessageHandler(filters.TEXT & filters.Regex("^🤖 Создать лендинг$"), self.create_mode_selection_command)
            ],
            states={
                AI_MODE_SELECTION: [
                    CallbackQueryHandler(self.handle_mode_selection, pattern="^mode_")
                ],
                AI_CONVERSATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_ai_message),
                    MessageHandler(filters.PHOTO | filters.VIDEO, self.handle_ai_media),
                    CommandHandler("cancel_ai", self.cancel_ai_command),
                    MessageHandler(filters.TEXT & filters.Regex(re.compile("^(отмена|отменить)$", re.IGNORECASE)), self.cancel_ai_command)
                    # Обработчики кнопок генерации вынесены в fallbacks и вне ConversationHandler
                ],
                AI_GENERATING: [
                    MessageHandler(filters.TEXT, self.handle_generating)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.handle_ai_generate, pattern="^ai_generate$"),
                CallbackQueryHandler(self.handle_ai_edit, pattern="^ai_edit$"),
                CommandHandler("cancel_ai", self.cancel_ai_command)
            ],
            per_user=True,
            per_chat=True,
            per_message=False,
            allow_reentry=True
            # conversation_timeout убран, так как требует JobQueue
            # Таймаут обрабатывается через _cleanup_inactive_ai_agents
        )
        self.app.add_handler(ai_agent_handler, group=1)
        
        # Обработчики кнопок генерации также вне ConversationHandler как fallback
        # (на случай, если ConversationHandler не активен или не обработает callback)
        # Проверяем наличие AI-агента перед обработкой
        async def handle_ai_generate_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Fallback обработчик для кнопки генерации вне ConversationHandler"""
            if not update.callback_query:
                return
            if update.callback_query.data != "ai_generate":
                return
            
            user_id = update.callback_query.from_user.id
            if user_id in self.ai_agents:
                logger.info(f"Fallback handler (group=0): User {user_id} clicked generate button")
                # Вызываем основной обработчик
                result = await self.handle_ai_generate(update, context)
                return result
            else:
                logger.warning(f"Fallback handler: AI agent not found for user {user_id}")
        
        async def handle_ai_edit_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Fallback обработчик для кнопки редактирования вне ConversationHandler"""
            if not update.callback_query:
                return
            if update.callback_query.data != "ai_edit":
                return
            
            user_id = update.callback_query.from_user.id
            if user_id in self.ai_agents:
                logger.info(f"Fallback handler (group=0): User {user_id} clicked edit button")
                # Вызываем основной обработчик
                result = await self.handle_ai_edit(update, context)
                return result
            else:
                logger.warning(f"Fallback handler: AI agent not found for user {user_id}")
        
        self.app.add_handler(CallbackQueryHandler(handle_ai_generate_fallback, pattern="^ai_generate$"), group=0)
        self.app.add_handler(CallbackQueryHandler(handle_ai_edit_fallback, pattern="^ai_edit$"), group=0)
        
        # Обработка остальных кнопок меню (помощь, отмена) - после ConversationHandler
        self.app.add_handler(MessageHandler(
            filters.TEXT & filters.Regex("^(📚 Помощь|❌ Отмена)$"),
            self.handle_main_menu_button
        ))
        
        # Обработка неизвестных команд
        self.app.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
    
    # ==================== Главное меню ====================
    
    def _create_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Создание главной клавиатуры"""
        keyboard = [
            [
                KeyboardButton("🤖 Создать лендинг")
            ],
            [
                KeyboardButton("📚 Помощь"),
                KeyboardButton("❌ Отмена")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    # ==================== Обработка кнопок главного меню ====================
    
    async def handle_main_menu_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки главного меню"""
        text = update.message.text
        user_id = update.effective_user.id
        logger.info(f"User {user_id} pressed button: {text}")
        
        if text == "🤖 Создать лендинг":
            # Кнопка теперь обрабатывается через entry_points ConversationHandler
            # Но оставляем здесь для совместимости
            await self.create_mode_selection_command(update, context)
        elif text == "📚 Помощь":
            await self.help_command(update, context)
        elif text == "❌ Отмена":
            await self.cancel_ai_command(update, context)
    
    # ==================== /start и /help ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        
        # Сохраняем пользователя в БД
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
            if not db_user:
                db_user = User(
                    telegram_id=str(user.id),
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                db.add(db_user)
                db.commit()
        finally:
            db.close()
        
        welcome_text = f"""👋 Привет, {user.first_name}!

Я помогу тебе создать лендинг для продажи товаров.

🤖 <b>Создание лендинга:</b>
/ai - Создать лендинг с AI-ассистентом

📚 <b>Помощь:</b>
/help - Показать помощь"""
        
        try:
            await update.message.reply_text(
                welcome_text,
                parse_mode='HTML',
                reply_markup=self.main_keyboard
            )
        except Exception as e:
            logger.warning(f"HTML parse error in start command, sending plain text: {e}")
            plain_text = welcome_text.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            await update.message.reply_text(
                plain_text,
                reply_markup=self.main_keyboard
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_text = """📚 <b>Команды бота:</b>

/start - Начать работу
/ai - Создать лендинг с AI-ассистентом
/myid - Узнать свой Telegram ID
/help - Эта помощь
/cancel_ai - Отменить AI-режим

🤖 <b>Как работает AI-ассистент:</b>

1. Выберите режим: один товар или несколько товаров
2. AI-ассистент задаст вопросы в формате диалога
3. Отвечайте на вопросы и отправляйте фото/видео
4. После сбора всех данных AI создаст лендинг

📋 <b>Что собирает AI-ассистент:</b>

• Общая информация (цель сайта, аудитория, стиль)
• Данные о товарах (название, описание, цена, фото)
• Настройки уведомлений (email или Telegram)
• Дополнительные материалы (видео, галереи, отзывы)

⏱ <b>Время генерации:</b> 30-60 секунд

💡 <b>Совет:</b> Отвечайте подробно - это поможет создать более качественный лендинг!"""
        
        try:
            await update.message.reply_text(
                help_text,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.warning(f"HTML parse error in help command, sending plain text: {e}")
            # Убираем HTML теги для plain text
            plain_text = help_text.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            await update.message.reply_text(plain_text)
    
    # ==================== Генерация ====================
    
    async def _start_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Запуск генерации лендинга"""
        logger.info(f"Starting generation for user {user_id}")
        
        # Определяем chat_id и bot
        if hasattr(update, 'callback_query') and update.callback_query:
            chat_id = update.callback_query.message.chat_id
            bot = update.callback_query.message.get_bot()
        else:
            chat_id = update.effective_chat.id
            bot = context.bot
        
        try:
            data = self._get_user_data(user_id)
            
            # Проверяем, используется ли новая структура (17 пунктов)
            landing_type = data.get('landing_type')
            
            if landing_type:
                # НОВАЯ СТРУКТУРА (17 пунктов) - собираем ВСЕ данные
                user_data_for_gen = {
                    # Пункт 1: Тип лендинга
                    'landing_type': landing_type,
                    
                    # Пункт 2: Название товара
                    'product_name': data.get('product_name', 'Товар'),
                    
                    # Пункт 1: Hero блок
                    'hero_media': data.get('hero_media'),
                    'hero_media_type': data.get('hero_media_type', 'photo'),
                    'hero_media_format': data.get('hero_media_format', 'jpeg'),
                    'hero_aspect_ratio': data.get('hero_aspect_ratio', '3:4'),
                    'hero_discount': data.get('hero_discount'),
                    'hero_discount_position': data.get('hero_discount_position'),
                    
                    # Пункт 3: 3 яркие характеристики
                    'characteristics': data.get('characteristics', []),
                    
                    # Пункт 4: Таймер
                    'timer_enabled': data.get('timer_enabled', False),
                    'timer_type': data.get('timer_type'),
                    'timer_date': data.get('timer_date'),
                    
                    # Пункт 5: Цены
                    'old_price': data.get('old_price', '152 BYN'),
                    'new_price': data.get('new_price', '99 BYN'),
                    
                    # Пункт 6: Опции формы
                    'sizes': data.get('sizes', []),
                    'colors': data.get('colors', []),
                    'characteristics_list': data.get('characteristics_list', []),
                    'form_has_sizes': data.get('form_has_sizes', False),
                    'form_has_colors': data.get('form_has_colors', False),
                    'form_has_characteristics': data.get('form_has_characteristics', False),
                    'form_has_quantity': data.get('form_has_quantity', False),
                    
                    # Пункт 7: Средний блок
                    'middle_block_type': data.get('middle_block_type'),
                    'middle_video': data.get('middle_video'),
                    'middle_video_format': data.get('middle_video_format'),
                    'middle_video_aspect_ratio': data.get('middle_video_aspect_ratio'),
                    'middle_gallery': data.get('middle_gallery', []),  # Могут быть словари с filename
                    
                    # Пункт 8: Описание
                    'description_text': data.get('description_text', ''),
                    'description_photos': data.get('description_photos', []),  # Могут быть словари с filename
                    'description_is_wildberries': data.get('description_is_wildberries', False),
                    
                    # Пункт 12: Отзывы
                    'reviews': data.get('reviews', []),
                    'reviews_type': data.get('reviews_type'),
                    'reviews_aspect_ratio': data.get('reviews_aspect_ratio', '3:4'),
                    'reviews_photo_format': data.get('reviews_photo_format', 'jpeg'),
                    
                    # Пункт 17: Подвал
                    'footer_info': data.get('footer_info', {}),
                    
                    # Уведомления
                    'notification_type': data.get('notification_type', 'telegram'),
                    'notification_email': data.get('notification_email', ''),
                    'notification_telegram_token': data.get('notification_telegram_token', ''),
                    'notification_telegram_chat_id': data.get('notification_telegram_chat_id', ''),
                    
                    # Дополнительные данные
                    'photos_dir': data.get('photos_dir', ''),
                    'videos_dir': data.get('videos_dir', ''),
                }
                
                # Для обратной совместимости добавляем старые поля
                user_data_for_gen['product_description'] = user_data_for_gen['description_text']
                user_data_for_gen['benefits'] = user_data_for_gen['characteristics']
                
                # Обрабатываем фото (могут быть словарями или строками)
                photos_list = []
                for photo in user_data_for_gen.get('middle_gallery', []):
                    if isinstance(photo, dict):
                        photos_list.append(photo.get('path', photo))
                    else:
                        photos_list.append(photo)
                for photo in user_data_for_gen.get('description_photos', []):
                    if isinstance(photo, dict):
                        photos_list.append(photo.get('path', photo))
                    else:
                        photos_list.append(photo)
                user_data_for_gen['photos'] = photos_list
                
                template_id = landing_type
            else:
                # СТАРАЯ СТРУКТУРА - для обратной совместимости
                product_type = data.get('product_type', 'physical_product')
                
                # Определяем шаблон на основе типа товара
                template_map = {
                    'physical_product': 'physical_single',
                    'service': 'service_consultation',
                    'digital_product': 'digital_course'
                }
                template_id = template_map.get(product_type, 'physical_single')
                
                # Подготавливаем данные для генератора
                user_data_for_gen = {
                    'product_name': data.get('product_name', 'Товар'),
                    'product_description': data.get('product_description', ''),
                    'old_price': data.get('old_price', '152 BYN'),
                    'new_price': data.get('new_price', '99 BYN'),
                    'benefits': data.get('benefits', []),
                    'photos': data.get('photos', []),
                    'photos_dir': data.get('photos_dir', ''),
                    'product_type': product_type,
                    'design_style': data.get('design_style', 'vibrant'),
                    **data.get('extra_fields', {})
                }
                
                # Добавляем информацию для подвала, если есть
                footer_info = data.get('footer_info', {})
                if footer_info:
                    user_data_for_gen['footer_info'] = footer_info
                else:
                    # Пробуем получить из extra_fields или напрямую из data
                    footer_fields = ['company_name', 'ip_name', 'unp', 'ogrn', 'inn', 'address', 'phone', 'email']
                    footer_data = {}
                    for field in footer_fields:
                        if field in data:
                            footer_data[field] = data[field]
                        elif 'extra_fields' in data and field in data['extra_fields']:
                            footer_data[field] = data['extra_fields'][field]
                    
                    if footer_data:
                        user_data_for_gen['footer_info'] = footer_data
                        # Также добавляем поля напрямую для обратной совместимости
                        for key, value in footer_data.items():
                            user_data_for_gen[key] = value
            
            # Вычисляем скидку
            try:
                old = float(str(user_data_for_gen['old_price']).replace('BYN', '').replace('RUB', '').replace('USD', '').strip())
                new = float(str(user_data_for_gen['new_price']).replace('BYN', '').replace('RUB', '').replace('USD', '').strip())
                discount = int(((old - new) / old) * 100)
                user_data_for_gen['discount_percent'] = discount
            except Exception:
                user_data_for_gen['discount_percent'] = 35
            
            logger.info(f"Generating with template: {template_id}, data keys: {list(user_data_for_gen.keys())}")
            logger.info(f"Sample data: product_name={user_data_for_gen.get('product_name')}, old_price={user_data_for_gen.get('old_price')}, new_price={user_data_for_gen.get('new_price')}")
            logger.info(f"Characteristics: {user_data_for_gen.get('characteristics')}, Footer: {user_data_for_gen.get('footer_info')}")
            
            # Генерируем лендинг
            result = await self.code_generator.generate(template_id, user_data_for_gen)
            
            # Сохраняем запись Generation для rate limiting
            db = SessionLocal()
            try:
                # Используем транзакцию для атомарности
                # Получаем или создаем пользователя
                db_user = db.query(User).filter(User.telegram_id == str(user_id)).first()
                if not db_user:
                    user_obj = update.effective_user
                    db_user = User(
                        telegram_id=str(user_id),
                        username=user_obj.username,
                        first_name=user_obj.first_name,
                        last_name=user_obj.last_name
                    )
                    db.add(db_user)
                    db.commit()
                    db.refresh(db_user)
                
                # Создаем проект
                project = Project(
                    user_id=db_user.id,
                    template_id=template_id,
                    template_name=template_id,
                    user_data=user_data_for_gen,
                    status='completed' if result.get('success') else 'failed',
                    generation_time=result.get('generation_time', 0),
                    files_path=result.get('files', {}).get('project_dir', ''),
                    zip_file=result.get('files', {}).get('zip_file', '')
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                
                # Создаем запись Generation для rate limiting
                generation = Generation(
                    user_id=str(user_id),
                    project_id=project.id,
                    prompt=f"Template: {template_id}",
                    response="Success" if result.get('success') else result.get('error', ''),
                    tokens_used=result.get('tokens_used', 0),
                    generation_time=result.get('generation_time', 0),
                    success=result.get('success', False),
                    error_message=result.get('error') if not result.get('success') else None
                )
                db.add(generation)
                db.commit()
                logger.info(f"Saved generation record for user {user_id}")
            except Exception as e:
                logger.error(f"Error saving generation record: {e}")
                db.rollback()
            finally:
                db.close()
            
            if result.get('success'):
                logger.info(f"Generation successful for user {user_id}")
                
                # Копируем фото в папку проекта
                files_info = result.get('files', {})
                project_dir = files_info.get('project_dir', '')
                
                if project_dir and data.get('photos'):
                    img_dir = os.path.join(project_dir, 'img')
                    os.makedirs(img_dir, exist_ok=True)
                    
                    for i, photo_path in enumerate(data.get('photos', [])):
                        if os.path.exists(photo_path):
                            dest_path = os.path.join(img_dir, f'product_{i+1}.jpg')
                            shutil.copy2(photo_path, dest_path)
                            logger.info(f"Copied photo to {dest_path}")
                
                zip_path = files_info.get('zip_file', '')
                
                if zip_path and os.path.exists(zip_path):
                    # Отправляем ZIP
                    # Экранируем спецсимволы Markdown в template_id
                    safe_template_id = template_id.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ *Лендинг успешно создан!*\n\n"
                             f"📁 Шаблон: {safe_template_id}\n"
                             f"⏱ Время генерации: {result.get('generation_time', 0)} сек\n\n"
                             f"Отправляю архив с файлами...",
                        parse_mode='Markdown'
                    )
                    
                    with open(zip_path, 'rb') as f:
                        await bot.send_document(
                            chat_id=chat_id,
                            document=f,
                            filename=f"landing_{user_data_for_gen.get('product_name', 'товар')[:20]}.zip",
                            caption="📦 Ваш лендинг готов!\n\n"
                                    "В архиве:\n"
                                    "• index.html - главная страница\n"
                                    "• css/styles.css - стили\n"
                                    "• js/script.js - скрипты\n"
                                    "• sendCPA.php - обработчик формы\n\n"
                                    "Выберите действие из меню:",
                            reply_markup=self.main_keyboard
                        )
                    logger.info(f"ZIP sent to user {user_id}")
                else:
                    logger.error(f"ZIP file not found: {zip_path}")
                    await bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Лендинг создан, но возникла проблема с архивом.\n"
                             "Попробуйте снова через /quick или /create",
                        reply_markup=self.main_keyboard
                    )
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                logger.error(f"Generation failed for user {user_id}: {error_msg}")
                
                # Улучшенные сообщения об ошибках для пользователя
                user_friendly_msg = self._format_error_message(error_msg)
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=user_friendly_msg,
                    reply_markup=self.main_keyboard
                )
        
        except Exception as e:
            logger.error(f"Exception in generation for user {user_id}: {str(e)}", exc_info=True)
            try:
                user_friendly_msg = self._format_error_message(str(e))
                await bot.send_message(
                    chat_id=chat_id,
                    text=user_friendly_msg,
                    reply_markup=self.main_keyboard
                )
            except Exception:
                pass
        
        finally:
            # Очищаем данные пользователя
            self._cleanup_user_data(user_id)
    
    def _cleanup_user_data(self, user_id: int):
        """Очистка данных пользователя"""
        data = self._get_user_data(user_id)
        if data:
            # Удаляем временную папку с фото
            photos_dir = data.get('photos_dir')
            if photos_dir and os.path.exists(photos_dir):
                try:
                    shutil.rmtree(photos_dir)
                    logger.info(f"Cleaned up photos dir for user {user_id}")
                except Exception:
                    pass
            
            # Очищаем данные из БД
            self._clear_user_data(user_id)
            logger.info(f"Cleaned up user data for {user_id}")
    
    async def myid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /myid - показать свой Telegram ID"""
        user = update.effective_user
        
        message = (
            f"🆔 **Ваш Telegram ID:**\n\n"
            f"`{user.id}`\n\n"
            f"📝 **Дополнительная информация:**\n"
            f"• Username: @{user.username if user.username else 'не указан'}\n"
            f"• Имя: {user.first_name or 'не указано'}\n"
            f"• Фамилия: {user.last_name or 'не указана'}\n\n"
            f"💡 **Для чего это нужно?**\n"
            f"Этот ID можно использовать для настройки администраторов бота "
            f"в переменной окружения `BOT_ADMIN_IDS`."
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    def _is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором."""
        admin_ids = [aid.strip() for aid in Config.BOT_ADMIN_IDS if aid.strip()]
        return not admin_ids or str(user_id) in admin_ids

    async def notify_admins(self, text: str, parse_mode: Optional[str] = None) -> None:
        """
        Отправить сообщение всем администраторам (для алертов и мониторинга).
        Ошибки отправки логируются, но не прерывают выполнение.
        """
        admin_ids = [aid.strip() for aid in Config.BOT_ADMIN_IDS if aid.strip()]
        if not admin_ids:
            return
        for uid_str in admin_ids:
            try:
                uid = int(uid_str)
                await self.app.bot.send_message(
                    chat_id=uid,
                    text=text,
                    parse_mode=parse_mode,
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить алерт админу {uid_str}: {e}")

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin — панель администратора (меню с кнопками)."""
        user_id = update.effective_user.id
        context.user_data.pop('admin_waiting_broadcast', None)
        if not self._is_admin(user_id):
            await update.message.reply_text(
                "❌ У вас нет прав. Эта команда только для администраторов."
            )
            return
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔐 **Панель администратора**\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_admin_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий кнопок админ-панели."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await query.edit_message_text("❌ Нет прав.")
            return
        data = query.data
        if data == "admin_close":
            await query.edit_message_text("Панель закрыта.")
            return
        if data == "admin_stats":
            try:
                from backend.utils.metrics import MetricsCollector
                stats = MetricsCollector.get_all_stats()
                msg = "📊 **Статистика бота**\n\n"
                users = stats.get('users', {})
                msg += f"👥 Пользователи: всего {users.get('total_users', 0)}, за 24ч: {users.get('new_users_24h', 0)}\n\n"
                projects = stats.get('projects', {})
                msg += f"📁 Проекты: всего {projects.get('total_projects', 0)}, успешных: {projects.get('completed', 0)}\n\n"
                gens = stats.get('generations', {})
                msg += f"⚡ Генерации: всего {gens.get('total_generations', 0)}, успешных: {gens.get('successful', 0)}"
                await query.edit_message_text(msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error in admin stats: {e}", exc_info=True)
                await query.edit_message_text(f"❌ Ошибка: {e}")
            return
        if data == "admin_broadcast":
            context.user_data['admin_waiting_broadcast'] = True
            await query.edit_message_text(
                "📢 **Рассылка**\n\n"
                "Отправьте текст сообщения одним сообщением.\n"
                "Оно будет отправлено всем пользователям бота.\n\n"
                "Отмена: отправьте /admin\n"
                "Если включён AI-режим — лучше сначала /cancel_ai.",
                parse_mode='Markdown'
            )
            return

    async def handle_admin_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текста рассылки от админа (когда ждём текст после нажатия «Рассылка»)."""
        if not update.message or not update.message.text:
            return
        user_id = update.effective_user.id
        if not self._is_admin(user_id) or not context.user_data.pop('admin_waiting_broadcast', False):
            return
        text = update.message.text
        from backend.utils.metrics import MetricsCollector
        chat_ids = MetricsCollector.get_all_telegram_user_ids()
        sent = 0
        failed = 0
        for cid in chat_ids:
            try:
                await context.bot.send_message(chat_id=cid, text=text)
                sent += 1
            except Exception as e:
                failed += 1
                logger.warning(f"Broadcast to {cid} failed: {e}")
        await update.message.reply_text(
            f"📢 Рассылка завершена.\nОтправлено: {sent}, не доставлено: {failed}."
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика бота (только для админов)"""
        user_id = update.effective_user.id
        user_id_str = str(user_id)
        
        # Проверка прав администратора
        admin_ids = [aid.strip() for aid in Config.BOT_ADMIN_IDS if aid.strip()]
        if admin_ids and user_id_str not in admin_ids:
            await update.message.reply_text(
                "❌ У вас нет прав для выполнения этой команды.\n\n"
                "Эта команда доступна только администраторам."
            )
            return
        
        try:
            from backend.utils.metrics import MetricsCollector
            
            # Получаем статистику
            stats = MetricsCollector.get_all_stats()
            
            # Форматируем сообщение
            message = "📊 **Статистика бота**\n\n"
            
            # Статистика пользователей
            users = stats.get('users', {})
            message += "👥 **Пользователи:**\n"
            message += f"• Всего: {users.get('total_users', 0)}\n"
            message += f"• Активных: {users.get('active_users', 0)}\n"
            message += f"• Новых за 24ч: {users.get('new_users_24h', 0)}\n"
            message += f"• Новых за 7д: {users.get('new_users_7d', 0)}\n\n"
            
            # Статистика проектов
            projects = stats.get('projects', {})
            message += "📁 **Проекты:**\n"
            message += f"• Всего: {projects.get('total_projects', 0)}\n"
            message += f"• Успешных: {projects.get('completed', 0)}\n"
            message += f"• Ошибок: {projects.get('failed', 0)}\n"
            message += f"• За 24ч: {projects.get('projects_24h', 0)}\n"
            message += f"• За 7д: {projects.get('projects_7d', 0)}\n"
            message += f"• Успешность: {projects.get('success_rate', 0)}%\n"
            message += f"• Среднее время: {projects.get('avg_generation_time_sec', 0)} сек\n\n"
            
            # Статистика генераций
            generations = stats.get('generations', {})
            message += "⚡ **Генерации:**\n"
            message += f"• Всего: {generations.get('total_generations', 0)}\n"
            message += f"• Успешных: {generations.get('successful', 0)}\n"
            message += f"• Ошибок: {generations.get('failed', 0)}\n"
            message += f"• За 24ч: {generations.get('generations_24h', 0)}\n"
            message += f"• Успешность: {generations.get('success_rate', 0)}%\n"
            message += f"• Среднее токенов: {generations.get('avg_tokens', 0)}\n"
            message += f"• Всего токенов: {generations.get('total_tokens', 0):,}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Ошибка при получении статистики:\n\n{str(e)}"
            )
    
    def _format_error_message(self, error_msg: str) -> str:
        """
        Форматирование технического сообщения об ошибке в понятное для пользователя
        
        Args:
            error_msg: Техническое сообщение об ошибке
            
        Returns:
            Понятное сообщение для пользователя
        """
        error_lower = error_msg.lower()
        
        # Таймаут
        if 'timeout' in error_lower or 'таймаут' in error_lower:
            return (
                "⏱️ **Превышено время ожидания**\n\n"
                "Генерация заняла слишком много времени.\n\n"
            "💡 **Что делать:**\n"
            "• Попробуйте снова через /create\n"
            "• Уменьшите количество данных (меньше фото, короче описание)\n"
            "• Проверьте интернет-соединение"
            )
        
        # Rate limit
        if 'rate limit' in error_lower or '429' in error_lower or 'лимит' in error_lower:
            return (
                "⏸️ **Превышен лимит запросов**\n\n"
                "Слишком много запросов к сервису генерации.\n\n"
            "💡 **Что делать:**\n"
            "• Подождите несколько минут\n"
            "• Попробуйте снова через /create"
            )
        
        # Ошибка сети
        if 'network' in error_lower or 'connection' in error_lower or 'сеть' in error_lower:
            return (
                "🌐 **Проблема с подключением**\n\n"
                "Не удалось подключиться к сервису генерации.\n\n"
            "💡 **Что делать:**\n"
            "• Проверьте интернет-соединение\n"
            "• Подождите минуту и попробуйте снова\n"
            "• Используйте /create для повторной попытки"
            )
        
        # Ошибка API ключа
        if 'api key' in error_lower or 'ключ' in error_lower or 'unauthorized' in error_lower:
            return (
                "🔑 **Проблема с настройками**\n\n"
                "Ошибка конфигурации сервиса генерации.\n\n"
                "💡 **Что делать:**\n"
                "• Обратитесь к администратору бота\n"
                "• Попробуйте позже"
            )
        
        # Исчерпаны попытки / сервис временно недоступен
        if 'попыток' in error_lower or 'attempts' in error_lower or 'retries' in error_lower:
            return (
                "⏳ **Сервис временно перегружен**\n\n"
                "Не удалось сгенерировать лендинг после нескольких попыток.\n\n"
                "💡 **Что делать:**\n"
                "• Подождите 1–2 минуты и нажмите «Да, генерировать» снова\n"
                "• Или начните заново: /ai"
            )
        
        # Общая ошибка
        return (
            "❌ **Ошибка при генерации**\n\n"
            "Не удалось создать лендинг.\n\n"
            "💡 **Что делать:**\n"
            "• Попробуйте снова через /create\n"
            "• Убедитесь, что все данные введены корректно\n"
            "• Если проблема повторяется, обратитесь к администратору"
        )
    
    # ==================== Общие методы ====================
    
    async def _handle_notification_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Диспетчер для обработки данных уведомлений"""
        user_id = update.effective_user.id
        data = self._get_user_data(user_id)
        notification_type = data.get('notification_type')
        
        # Проверяем, есть ли уже токен (для Telegram)
        if notification_type == 'telegram' and data.get('notification_telegram_token'):
            # Если токен уже есть, значит собираем Chat ID
            return await self.notification_handler.collect_telegram_chat_id(update, context)
        else:
            # Иначе собираем данные (email или токен)
            return await self.notification_handler.collect_data(update, context)
    
    async def handle_generating(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений во время генерации"""
        await update.message.reply_text(
            "⏳ Генерация в процессе, пожалуйста подождите..."
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена создания"""
        user_id = update.effective_user.id
        self._cleanup_user_data(user_id)
        
        await update.message.reply_text(
            "❌ Создание лендинга отменено.\n\nВыберите действие из меню:",
            reply_markup=self.main_keyboard
        )
        return ConversationHandler.END
    
    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неизвестных команд"""
        # Если пользователь ввёл /admin — показываем админ-панель (на случай, если основной обработчик не сработал)
        if update.message and update.message.text:
            cmd = (update.message.text.split()[0] or "").lstrip("/").split("@")[0].lower()
            if cmd == "admin":
                return await self.admin_command(update, context)
        await update.message.reply_text(
            "❓ Неизвестная команда. Используй /help для списка команд."
        )
    
    async def handle_unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неизвестных сообщений (когда состояние потеряно)"""
        user_id = update.effective_user.id
        
        # Этот обработчик вызывается через fallbacks ConversationHandler
        # Но нужно проверить, действительно ли ConversationHandler не активен
        # или просто не может обработать это конкретное сообщение
        
        # Проверяем состояние через context.user_data (внутреннее состояние ConversationHandler)
        # Если есть ключи состояния, значит ConversationHandler активен
        if context.user_data and len(context.user_data) > 0:
            # ConversationHandler активен, просто не может обработать это сообщение
            # Не показываем приветственное сообщение, просто игнорируем
            return ConversationHandler.END
        
        # Проверяем, есть ли незавершенное создание лендинга в БД
        user_data = self._get_user_data(user_id)
        state = user_data.get('state') if user_data else None
        
        # Если есть активное состояние в БД, значит ConversationHandler должен быть активен
        # Но если его нет в context.user_data, значит состояние потеряно
        if state and state not in [None, '']:
            # Есть состояние в БД, но нет в context - состояние потеряно
            if user_data and user_data.get('conversation_type') == 'create':
                # Предлагаем продолжить или начать сначала
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Продолжить создание", callback_data="resume_create")],
                    [InlineKeyboardButton("🆕 Начать сначала", callback_data="restart_create")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="cancel_create")]
                ])
                await update.message.reply_text(
                    "⚠️ Похоже, создание лендинга было прервано.\n\n"
                    "Что вы хотите сделать?",
                    reply_markup=keyboard
                )
                return ConversationHandler.END
        
        # Если нет активного состояния, просто игнорируем сообщение
        # Не показываем приветственное сообщение, чтобы избежать дублирования
        return ConversationHandler.END
    
    def _setup_menu_commands(self):
        """Настройка меню команд: для всех — без /admin, для админов — с /admin."""
        default_commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("ai", "Создать лендинг с AI-ассистентом"),
            BotCommand("create_ai", "Создать лендинг с AI-ассистентом"),
            BotCommand("myid", "Узнать свой Telegram ID"),
            BotCommand("help", "Помощь и инструкции"),
            BotCommand("cancel_ai", "Отменить AI-режим"),
        ]
        admin_commands = default_commands + [
            BotCommand("admin", "Панель администратора"),
        ]

        async def setup_commands():
            try:
                await self.app.bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())
                logger.info("✓ Меню команд по умолчанию установлено")
                admin_ids = [aid.strip() for aid in Config.BOT_ADMIN_IDS if aid.strip()]
                for uid_str in admin_ids:
                    try:
                        uid = int(uid_str)
                        await self.app.bot.set_my_commands(
                            admin_commands,
                            scope=BotCommandScopeChatMember(chat_id=uid, user_id=uid),
                        )
                        logger.info(f"✓ Команды для админа {uid} установлены")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Неверный BOT_ADMIN_IDS элемент '{uid_str}': {e}")
                try:
                    menu_button = MenuButtonCommands()
                    await self.app.bot.set_chat_menu_button(menu_button=menu_button)
                    logger.info("✓ Кнопка меню установлена")
                except Exception as e:
                    logger.debug(f"Кнопка меню не установлена (может не поддерживаться): {e}")
            except Exception as e:
                logger.warning(f"Не удалось установить меню команд: {e}")
        
        # Сохраняем задачу для выполнения при запуске
        self._menu_setup_task = setup_commands
    
    async def start_polling(self):
        """Запуск бота"""
        logger.info("Запуск Telegram бота...")
        await self.app.initialize()
        await self.app.start()
        
        # Восстанавливаем AI-агентов из БД
        await self._restore_ai_agents_from_db()
        
        # Устанавливаем меню команд
        if hasattr(self, '_menu_setup_task'):
            await self._menu_setup_task()
        
        await self.app.updater.start_polling()
        logger.info("Бот запущен и готов к работе")
        if Config.NOTIFY_ADMINS_ON_STARTUP:
            from datetime import datetime
            await self.notify_admins(
                f"✅ Бот запущен (polling)\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
    
    async def stop(self):
        """Остановка бота"""
        # Очищаем все AI-агенты перед остановкой
        self.ai_agents.clear()
        self.ai_agents_last_activity.clear()
        
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
    
    # ==================== AI-ассистент ====================
    
    async def create_mode_selection_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для выбора режима работы (SINGLE/MULTI) - ДО запуска AI-ассистента"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} started mode selection")
        
        try:
            keyboard = [
                [InlineKeyboardButton("📄 Лендинг (1 товар)", callback_data="mode_single")],
                [InlineKeyboardButton("🌐 Сайт (несколько товаров)", callback_data="mode_multi")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Проверяем, есть ли message (для команд и текстовых сообщений)
            if update.message:
                await update.message.reply_text(
                    "Выберите формат проекта:\n\n"
                    "• 📄 **Лендинг** - для одного товара\n"
                    "• 🌐 **Сайт** - для нескольких товаров\n\n"
                    "_После выбора запустится AI-ассистент для сбора данных_",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            # Если это callback_query (например, из другого обработчика)
            elif update.callback_query:
                await update.callback_query.message.reply_text(
                    "Выберите формат проекта:\n\n"
                    "• 📄 **Лендинг** - для одного товара\n"
                    "• 🌐 **Сайт** - для нескольких товаров\n\n"
                    "_После выбора запустится AI-ассистент для сбора данных_",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            logger.info(f"Mode selection message sent to user {user_id}")
            return AI_MODE_SELECTION
        except Exception as e:
            logger.error(f"Error in create_mode_selection_command for user {user_id}: {e}", exc_info=True)
            if update.message:
                await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
            return ConversationHandler.END
    
    async def handle_mode_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора режима и запуска AI-ассистента"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        mode = 'SINGLE' if 'single' in query.data else 'MULTI'
        mode_text = "Лендинг (1 товар)" if mode == 'SINGLE' else "Сайт (несколько товаров)"
        
        # Сохраняем выбор режима
        context.user_data['selected_mode'] = mode
        self._update_user_data(user_id, ai_mode=mode)
        
        logger.info(f"User {user_id} selected mode: {mode}")
        
        try:
            await query.edit_message_text(
                f"✅ Режим выбран: **{mode_text}**\n\n"
                "🤖 Запускаю AI-ассистента для сбора данных...",
                parse_mode='Markdown'
            )
            # Запускаем AI-ассистента заново (пользователь явно выбрал режим — не восстанавливать старый диалог)
            result = await self.start_ai_agent(user_id, mode, query.message.chat.id, context, force_new=True)
            
            # Возвращаем состояние для ConversationHandler
            if result == AI_CONVERSATION:
                return AI_CONVERSATION
            else:
                logger.warning(f"AI agent did not return AI_CONVERSATION state, got: {result}")
                return AI_CONVERSATION  # Все равно переходим в состояние разговора
        except Exception as e:
            logger.error(f"Error in handle_mode_selection for user {user_id}: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Произошла ошибка. Попробуйте еще раз, используя команду /ai"
            )
            return ConversationHandler.END
    
    async def start_ai_agent(self, user_id: int, mode: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE = None, force_new: bool = False):
        """Запуск AI-ассистента. Если force_new=True (выбор режима из меню), всегда создаём нового агента и показываем приветствие."""
        try:
            from backend.bot.ai_agent import LandingAIAgent
            
            logger.info(f"Starting AI agent for user {user_id} with mode {mode} (force_new={force_new})")
            
            # Восстанавливаем из БД только если не явный старт с выбором режима
            user_data = self._get_user_data(user_id)
            if not force_new and 'ai_agent_state' in user_data and user_data.get('ai_agent_active'):
                try:
                    # Восстанавливаем агента из сохраненного состояния
                    agent = LandingAIAgent.from_serialized_state(user_data['ai_agent_state'])
                    self.ai_agents[user_id] = agent
                    
                    # Восстанавливаем время последней активности
                    import time
                    self.ai_agents_last_activity[user_id] = user_data.get('last_activity', time.time())
                    
                    logger.info(f"AI agent restored from DB for user {user_id}, stage: {agent.stage}")
                    
                    # Отправляем сообщение о продолжении диалога
                    await self.app.bot.send_message(
                        chat_id=chat_id,
                        text=f"✅ Диалог восстановлен. Продолжаем с этапа: {agent._get_stage_info()}",
                        parse_mode='HTML'
                    )
                    
                    # Устанавливаем состояние
                    if context:
                        context.user_data['ai_agent_active'] = True
                    return AI_CONVERSATION
                except Exception as restore_error:
                    logger.warning(f"Failed to restore AI agent from DB for user {user_id}: {restore_error}, creating new")
                    # Если восстановление не удалось, создаем нового агента
            
            # Создаем нового агента
            agent = LandingAIAgent(mode=mode)
            self.ai_agents[user_id] = agent
            import time
            self.ai_agents_last_activity[user_id] = time.time()
            
            # Сохраняем состояние агента в БД
            self._save_ai_agent_state(user_id, agent)
            
            # Начинаем диалог
            greeting = await agent.start_conversation()
            
            # Отправляем приветственное сообщение
            # Используем HTML для более надежной работы
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=greeting,
                parse_mode='HTML'
            )
            
            # Устанавливаем состояние AI_CONVERSATION для ConversationHandler
            # Используем context.user_data для установки состояния
            if context:
                context.user_data['ai_agent_active'] = True
            
            logger.info(f"AI agent started successfully for user {user_id} with mode {mode}")
            return AI_CONVERSATION
        except Exception as e:
            logger.error(f"Error starting AI agent for user {user_id}: {e}", exc_info=True)
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Произошла ошибка при запуске AI-ассистента. Попробуйте позже."
                )
            except Exception as send_error:
                logger.error(f"Error sending error message: {send_error}")
            return ConversationHandler.END
    
    async def handle_ai_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка сообщений в AI-режиме"""
        user_id = update.effective_user.id
        
        # Проверяем команды отмены
        if update.message.text and update.message.text.lower() in ['/cancel_ai', '/cancel', 'отмена', 'отменить']:
            await self.cancel_ai_mode(user_id, update.message.chat.id)
            return ConversationHandler.END
        
        # Проверяем, есть ли активный AI-агент для пользователя
        if user_id not in self.ai_agents:
            return ConversationHandler.END  # Не обрабатываем, если нет активного агента
        
        agent = self.ai_agents[user_id]
        message_text = update.message.text
        
        # Проверяем команды запуска генерации (если агент в стадии generation)
        if agent.stage == 'generation':
            generation_commands = [
                'начинай генерацию', 'начни генерацию', 'генерируй', 'генерировать',
                'готов', 'да', 'давай', 'начинай', 'начни', 'создавай', 'создай',
                'да, генерировать', 'да генерировать', 'давай генерировать'
            ]
            if message_text.lower().strip() in generation_commands or any(cmd in message_text.lower() for cmd in ['генерир', 'создай', 'готов', 'давай']):
                logger.info(f"User {user_id} confirmed generation via text command: {message_text}")
                
                # Создаем классы-обертки для имитации callback_query
                class FakeCallbackQuery:
                    def __init__(self, msg, user):
                        self.data = 'ai_generate'
                        self.from_user = user
                        self.message = msg
                        self.id = f'fake_{int(time.time() * 1000)}'
                    
                    async def answer(self, text=None, show_alert=False):
                        pass
                    
                    async def edit_message_text(self, text, **kwargs):
                        await self.message.reply_text(text, **kwargs)
                
                class FakeUpdate:
                    def __init__(self, original_update):
                        self.callback_query = FakeCallbackQuery(original_update.message, original_update.effective_user)
                        self.effective_user = original_update.effective_user
                
                import time
                FakeUpdate(update)  # конструктор для совместимости, результат не используется
                
                # Вызываем обработчик генерации напрямую, передавая нужные параметры
                try:
                    # Проверка rate limit
                    allowed, remaining = await rate_limiter.check_db_rate_limit(user_id)
                    if not allowed:
                        await update.message.reply_text(
                            f"⏸️ Превышен лимит запросов\n\n"
                            f"Вы можете создать максимум {rate_limiter.max_requests} "
                            f"лендингов в час.\n\n"
                            f"Попробуйте позже."
                        )
                        return AI_CONVERSATION
                    
                    await update.message.reply_text("🔄 Генерирую лендинг... Это может занять несколько минут.")
                    
                    # Преобразуем данные агента в формат user_data
                    logger.info(f"Converting AI agent data to user_data for user {user_id}")
                    user_data = agent.convert_to_user_data()
                    
                    # Валидация данных
                    validation_errors = agent.validate_data()
                    if validation_errors:
                        error_msg = "❌ Обнаружены ошибки в данных:\n\n" + "\n".join([f"• {e}" for e in validation_errors])
                        await update.message.reply_text(error_msg + "\n\nПожалуйста, исправьте данные и попробуйте снова.")
                        return AI_CONVERSATION
                    
                    # Генерируем лендинг
                    template_id = 'single_product' if agent.mode == 'SINGLE' else 'multi_product'
                    logger.info(f"Starting generation for user {user_id}, template_id: {template_id}")
                    
                    result = await self.code_generator.generate(template_id, user_data)
                    
                    if result.get('success'):
                        files_info = result.get('files', {})
                        zip_file = files_info.get('zip_file')
                        
                        if zip_file and os.path.exists(zip_file):
                            with open(zip_file, 'rb') as f:
                                await self.app.bot.send_document(
                                    chat_id=update.message.chat.id,
                                    document=f,
                                    filename=os.path.basename(zip_file),
                                    caption="✅ Лендинг успешно сгенерирован!"
                                )
                        else:
                            await update.message.reply_text("✅ Лендинг сгенерирован, но файл не найден.")
                        # Очищаем агента
                        await self._cleanup_ai_agent_files(user_id)
                        if user_id in self.ai_agents:
                            del self.ai_agents[user_id]
                        if user_id in self.ai_agents_last_activity:
                            del self.ai_agents_last_activity[user_id]
                        user_data_db = self._get_user_data(user_id)
                        user_data_db.pop('ai_agent_state', None)
                        user_data_db.pop('ai_agent_active', None)
                        user_data_db.pop('last_activity', None)
                        self._save_user_data(user_id, user_data_db, state=None, conversation_type=None)
                        return ConversationHandler.END
                    else:
                        error = result.get('error', 'Неизвестная ошибка')
                        formatted_error = self._format_error_message(error)
                        await update.message.reply_text(f"❌ Ошибка генерации:\n\n{formatted_error}")
                        return AI_CONVERSATION
                except Exception as e:
                    logger.error(f"Error generating from text command for user {user_id}: {e}", exc_info=True)
                    formatted_error = self._format_error_message(str(e))
                    await update.message.reply_text(f"❌ Произошла ошибка:\n\n{formatted_error}")
                    return AI_CONVERSATION
        
        # Обновляем время последней активности
        import time
        self.ai_agents_last_activity[user_id] = time.time()
        
        try:
            # Обрабатываем сообщение через агента
            response = await agent.process_message(message_text, user_id)
            
            # Проверяем: если после обработки появилось описание товара и есть hero-фото - запускаем vision-анализ
            products = agent.collected_data.get('products', [])
            files = agent.collected_data.get('files', [])
            hero_file = next((f for f in files if f.get('block') == 'hero'), None)
            
            if products and products[0].get('product_description') and hero_file and hero_file.get('type') == 'photo':
                # Проверяем, не запускали ли уже анализ
                if 'vision_style_suggestion' not in agent.collected_data:
                    product_name = products[0].get('product_name', '')
                    description = products[0].get('product_description', '')
                    hero_path = hero_file.get('path')
                    
                    if hero_path and os.path.exists(hero_path):
                        # Запускаем vision-анализ в фоне
                        import asyncio
                        asyncio.create_task(
                            self._analyze_hero_image_async(user_id, hero_path, product_name, description, agent)
                        )
                        logger.info(f"Started background vision analysis after description received: {hero_path}")
            
            # Сохраняем состояние агента после обработки сообщения
            self._save_ai_agent_state(user_id, agent)
            
            # Проверяем длину ответа (Telegram ограничивает до 4096 символов)
            max_length = 4000  # Оставляем запас
            if len(response) > max_length:
                logger.warning(f"Response too long ({len(response)} chars), truncating to {max_length}")
                response = response[:max_length] + "\n\n... (сообщение обрезано)"
            
            # Отправляем ответ с обработкой ошибок парсинга
            try:
                await update.message.reply_text(response, parse_mode='HTML')
            except Exception as parse_error:
                # Если HTML не работает, пробуем Markdown
                try:
                    await update.message.reply_text(response, parse_mode='Markdown')
                except Exception:
                    # Если и Markdown не работает, отправляем без разметки
                    logger.warning(f"Parse error, sending plain text: {parse_error}")
                    plain_response = response.replace('*', '').replace('_', '').replace('`', '').replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
                    await update.message.reply_text(plain_response)
            
            # Проверяем, готовы ли данные для генерации (после обработки сообщения и перехода стадий)
            logger.info(f"Current agent stage after processing: {agent.stage}")
            
            # Проверяем полноту данных и переходим в стадию generation, если все готово
            is_complete, missing = agent.check_completeness()
            logger.info(f"Completeness check: is_complete={is_complete}, missing={missing}, current_stage={agent.stage}")
            
            # Если данные собраны и мы еще не в стадии generation, переходим
            if is_complete:
                if agent.stage == 'products':
                    # Переходим в verification
                    agent.stage = 'verification'
                    agent.collected_data['stage'] = 'verification'
                    logger.info("Auto-transitioned to verification stage - products complete")
                elif agent.stage == 'verification':
                    # Переходим в generation
                    agent.stage = 'generation'
                    agent.collected_data['stage'] = 'generation'
                    logger.info("Auto-transitioned to generation stage - all data complete")
                # Сохраняем состояние после перехода
                self._save_ai_agent_state(user_id, agent)
            
            # Если агент в стадии generation, показываем кнопки (даже если LLM уже ответил)
            if agent.stage == 'generation':
                is_complete, missing = agent.check_completeness()
                if is_complete:
                    # Проверяем, не были ли уже отправлены кнопки в этом сообщении
                    # (чтобы не дублировать, если LLM уже упомянул генерацию)
                    if not hasattr(agent, '_summary_sent') or not agent._summary_sent:
                        summary = self._format_ai_summary(agent.collected_data)
                        keyboard = [
                            [InlineKeyboardButton("✅ Да, генерировать", callback_data="ai_generate")],
                            [InlineKeyboardButton("❌ Нет, исправить", callback_data="ai_edit")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Отправляем сводку с обработкой ошибок парсинга
                        summary_text = f"📋 <b>Сводка собранных данных:</b>\n\n{summary}\n\nВсё верно? Готов сгенерировать лендинг!"
                        try:
                            await update.message.reply_text(
                                summary_text,
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                            logger.info(f"Summary with buttons sent to user {user_id}")
                            agent._summary_sent = True
                        except Exception as parse_error:
                            logger.warning(f"HTML parse error for summary, sending plain text: {parse_error}")
                            plain_summary = summary_text.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
                            await update.message.reply_text(
                                plain_summary,
                                reply_markup=reply_markup
                            )
                            logger.info(f"Summary with buttons sent (plain text) to user {user_id}")
                            agent._summary_sent = True
                else:
                    logger.warning(f"Generation stage but data incomplete: {missing}")
                    if not hasattr(agent, '_missing_data_sent') or not agent._missing_data_sent:
                        await update.message.reply_text(
                            f"⚠️ Не хватает данных:\n" + "\n".join([f"- {m}" for m in missing])
                        )
                        agent._missing_data_sent = True
        except Exception as e:
            logger.error(f"Error handling AI message: {e}", exc_info=True)
            
            # При критических ошибках очищаем агента
            if "timeout" in str(e).lower() or "critical" in str(e).lower():
                logger.warning(f"Critical error for user {user_id}, cleaning up agent")
                await self.cancel_ai_mode(user_id, update.message.chat.id)
                await update.message.reply_text(
                    "❌ Произошла критическая ошибка. AI-режим был отменен.\n\n"
                    "Используйте /ai для нового создания."
                )
            else:
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке сообщения. Попробуйте еще раз."
                )
        
        return AI_CONVERSATION
    
    async def handle_ai_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фото/видео в AI-режиме"""
        user_id = update.effective_user.id
        
        # Проверяем, есть ли активный AI-агент
        if user_id not in self.ai_agents:
            return ConversationHandler.END
        
        agent = self.ai_agents[user_id]
        
        # Обновляем время последней активности
        import time
        self.ai_agents_last_activity[user_id] = time.time()
        
        try:
            # Определяем тип медиа
            if update.message.photo:
                file_obj = update.message.photo[-1]  # Берем самое большое фото
                file_type = 'photo'
            elif update.message.video:
                file_obj = update.message.video
                file_type = 'video'
            else:
                return
            
            # Проверка размера файла
            file_size = file_obj.file_size or 0
            if file_size > Config.MAX_FILE_SIZE:
                await update.message.reply_text(
                    f"❌ Файл слишком большой ({file_size / 1024 / 1024:.1f} MB). "
                    f"Максимальный размер: {Config.MAX_FILE_SIZE / 1024 / 1024:.1f} MB"
                )
                return
            
            # Добавляем расширение к пути ДО скачивания, чтобы файл сохранялся с расширением
            # (иначе генератор не находит файл при копировании в проект)
            ext = 'jpg' if file_type == 'photo' else (getattr(file_obj, 'mime_type', '') or 'mp4').split('/')[-1]
            if ext not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'webm'):
                ext = 'jpg' if file_type == 'photo' else 'mp4'
            file_path = os.path.join(Config.FILES_DIR, f'temp_{user_id}_{file_obj.file_unique_id}.{ext}')
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file_path = os.path.abspath(file_path)

            file = await self.app.bot.get_file(file_obj.file_id)
            await file.download_to_drive(file_path)

            file_info = {
                'path': file_path,
                'type': file_type,
                'filename': f"photo_{file_obj.file_unique_id[:8]}.{ext}",
                'original_name': f"photo_{file_obj.file_unique_id[:8]}.{ext}",
                'block': None  # Будет определено в диалоге
            }
            files_list = [file_info]
            caption = (update.message.caption or '').strip()

            # Только фото без подписи — короткое подтверждение без вызова LLM
            if not caption:
                total = await agent.add_files_only(files_list)
                ordinals = ('Первое', 'Второе', 'Третье', 'Четвёртое', 'Пятое', 'Шестое', 'Седьмое', 'Восьмое', 'Девятое', 'Десятое')
                which = ordinals[total - 1] if 1 <= total <= 10 else f'{total}-е'
                await update.message.reply_text(f"✅ {which} фото получил.")
                # Vision для hero-фото по возможности
                files_after = agent.collected_data.get('files', [])
                hero_file = next((f for f in files_after if f.get('block') == 'hero' and f.get('path') == file_path), None)
                if hero_file and file_type == 'photo':
                    products = agent.collected_data.get('products', [])
                    has_description = bool(products and products[0].get('product_description'))
                    if has_description and 'vision_style_suggestion' not in agent.collected_data:
                        import asyncio
                        asyncio.create_task(
                            self._analyze_hero_image_async(user_id, file_path, products[0].get('product_name', ''), products[0].get('product_description', ''), agent)
                        )
                self._save_ai_agent_state(user_id, agent)
            else:
                # Фото с подписью — полная обработка через агента
                response = await agent.process_message(caption, user_id, files=files_list)
                files_after = agent.collected_data.get('files', [])
                hero_file = next((f for f in files_after if f.get('block') == 'hero' and f.get('path') == file_path), None)
                if hero_file and file_type == 'photo':
                    products = agent.collected_data.get('products', [])
                    has_description = bool(products and products[0].get('product_description'))
                    if has_description and 'vision_style_suggestion' not in agent.collected_data:
                        import asyncio
                        asyncio.create_task(
                            self._analyze_hero_image_async(user_id, file_path, products[0].get('product_name', ''), products[0].get('product_description', ''), agent)
                        )
                try:
                    await update.message.reply_text(
                        f"✅ Файл получен!\n\n{response}",
                        parse_mode='HTML'
                    )
                except Exception:
                    await update.message.reply_text(
                        "✅ Файл получен!\n\n" + response.replace('<b>', '').replace('</b>', ''),
                    )
                self._save_ai_agent_state(user_id, agent)
        except Exception as e:
            logger.error(f"Error handling AI media: {e}", exc_info=True)
            
            # При критических ошибках очищаем агента
            if "timeout" in str(e).lower() or "critical" in str(e).lower():
                logger.warning(f"Critical error handling media for user {user_id}, cleaning up agent")
                await self.cancel_ai_mode(user_id, update.message.chat.id)
                await update.message.reply_text(
                    "❌ Произошла критическая ошибка при обработке файла. AI-режим был отменен.\n\n"
                    "Используйте /ai для нового создания."
                )
            else:
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке файла. Попробуйте еще раз."
                )
        
        return AI_CONVERSATION
    
    async def _analyze_hero_image_async(self, user_id: int, image_path: str, product_name: str, description: str, agent):
        """
        Асинхронный анализ hero-фото через Vision API (выполняется в фоне, не блокирует диалог)
        
        Args:
            user_id: ID пользователя
            image_path: Путь к hero-изображению
            product_name: Название товара
            description: Описание товара
            agent: Экземпляр LandingAIAgent
        """
        try:
            logger.info(f"Starting vision analysis for user {user_id}, image: {image_path}")
            
            # Используем LLM клиент из code_generator (или создаем новый)
            from backend.generator.llm_client import LLMClient
            llm_client = LLMClient()
            
            vision_result = await llm_client.analyze_image_style(image_path, product_name, description)
            
            if vision_result and 'colors' in vision_result and 'fonts' in vision_result:
                # Сохраняем результат в агента
                agent.collected_data['vision_style_suggestion'] = vision_result
                
                # Сохраняем состояние агента в БД
                self._save_ai_agent_state(user_id, agent)
                
                logger.info(
                    f"✓ Vision analysis completed for user {user_id}: "
                    f"primary={vision_result['colors'].get('primary')}, "
                    f"fonts={vision_result['fonts']}"
                )
                
                # Опционально: можно отправить уведомление пользователю
                # await self.app.bot.send_message(
                #     chat_id=user_id,
                #     text=f"🎨 Стиль и цвета подобраны на основе фото: {vision_result['colors'].get('primary')}"
                # )
            else:
                logger.warning(f"Vision analysis returned no valid result for user {user_id}, will use text-based analysis")
                
        except Exception as e:
            logger.error(f"Error in background vision analysis for user {user_id}: {e}", exc_info=True)
            # Не прерываем диалог при ошибке vision-анализа - используем текстовый fallback
    
    def _format_ai_summary(self, collected_data: Dict[str, Any]) -> str:
        """Форматирование сводки собранных данных"""
        summary = []
        
        mode_text = "Лендинг (1 товар)" if collected_data['mode'] == 'SINGLE' else "Сайт (несколько товаров)"
        summary.append(f"**Режим:** {mode_text}")
        
        general = collected_data.get('general_info', {})
        if general:
            summary.append(f"**Цель:** {general.get('goal', '-')}")
            summary.append(f"**Аудитория:** {general.get('target_audience', '-')}")
            summary.append(f"**Стиль:** {general.get('style', '-')}")
        
        products = collected_data.get('products', [])
        if products:
            if collected_data['mode'] == 'SINGLE':
                product = products[0]
                summary.append(f"**Товар:** {product.get('product_name', '-')}")
                summary.append(f"**Цена:** {product.get('new_price', '-')}")
        else:
                summary.append(f"**Товаров:** {len(products)}")
        
        files = collected_data.get('files', [])
        if files:
            summary.append(f"**Файлов (фото/видео):** {len(files)}")
        else:
            summary.append("**Фото товара:** ⚠️ не добавлено (нужно хотя бы одно)")
        
        return "\n".join(summary)
    
    async def cancel_ai_mode(self, user_id: int, chat_id: int):
        """Отмена AI-режима"""
        if user_id in self.ai_agents:
            # Очищаем временные файлы
            await self._cleanup_ai_agent_files(user_id)
            del self.ai_agents[user_id]
            if user_id in self.ai_agents_last_activity:
                del self.ai_agents_last_activity[user_id]
            logger.info(f"AI agent cancelled for user {user_id}")
        
        # Очищаем состояние агента из БД
        user_data = self._get_user_data(user_id)
        user_data.pop('ai_agent_state', None)
        user_data.pop('ai_agent_active', None)
        user_data.pop('last_activity', None)
        self._save_user_data(user_id, user_data, state=None, conversation_type=None)
        
        await self.app.bot.send_message(
            chat_id=chat_id,
            text="❌ AI-режим отменен.\n\nИспользуйте /ai для нового создания."
        )
    
    async def cancel_ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для отмены AI-режима"""
        user_id = update.effective_user.id
        await self.cancel_ai_mode(user_id, update.message.chat.id)
        return ConversationHandler.END
    
    async def handle_ai_generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения генерации в AI-режиме"""
        logger.info("=" * 80)
        logger.info("handle_ai_generate CALLED")
        logger.info("=" * 80)
        
        if not update.callback_query:
            logger.error("handle_ai_generate called without callback_query")
            return ConversationHandler.END
        
        query = update.callback_query
        user_id = query.from_user.id
        
        logger.info(f"User {user_id} clicked generate button (callback_data: {query.data})")
        logger.info(f"Current conversation state: {context.user_data.get('_conversation_state')}")
        logger.info(f"AI agents available: {list(self.ai_agents.keys())}")
        
        try:
            await query.answer()
            logger.info("Callback query answered successfully")
        except Exception as e:
            logger.error(f"Error answering callback query: {e}", exc_info=True)
        
        if user_id not in self.ai_agents:
            logger.warning(f"AI agent not found for user {user_id}")
            await query.edit_message_text("❌ AI-агент не найден. Начните заново с /ai")
            return ConversationHandler.END
        
        agent = self.ai_agents[user_id]
        
        try:
            # Проверка rate limit перед генерацией
            logger.info(f"Checking rate limit for user {user_id}")
            allowed, remaining = await rate_limiter.check_db_rate_limit(user_id)
            if not allowed:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await query.edit_message_text(
                    f"⏸️ Превышен лимит запросов\n\n"
                    f"Вы можете создать максимум {rate_limiter.max_requests} "
                    f"лендингов в час.\n\n"
                    f"Попробуйте позже."
                )
                return ConversationHandler.END
            logger.info(f"Rate limit OK for user {user_id}, starting generation")
            await query.edit_message_text("🔄 Генерирую лендинг... Это может занять несколько минут.")
            
            # Преобразуем данные агента в формат user_data
            logger.info(f"Converting AI agent data to user_data for user {user_id}")
            logger.info(f"Agent collected_data keys: {list(agent.collected_data.keys())}")
            logger.info(f"Agent products count: {len(agent.collected_data.get('products', []))}")
            if agent.collected_data.get('products'):
                logger.info(f"First product keys: {list(agent.collected_data['products'][0].keys())}")
            
            user_data = agent.convert_to_user_data()
            logger.info(f"Converted user_data keys: {list(user_data.keys())}")
            logger.info(f"Converted user_data values: {user_data}")
            
            # Без фото лендинг будет без главного изображения — требуем хотя бы одно
            has_photo = bool(user_data.get('hero_media') or user_data.get('photos') or agent.collected_data.get('files'))
            if not has_photo:
                await query.edit_message_text(
                    "📷 Чтобы лендинг выглядел привлекательно, нужна хотя бы одна фотография товара.\n\n"
                    "Отправьте фото в чат (оно будет главным изображением на странице), "
                    "затем снова нажмите «Да, генерировать»."
                )
                return AI_CONVERSATION
            # Валидация данных перед генерацией
            logger.info(f"Validating data for user {user_id}")
            validation_errors = agent.validate_data()
            logger.info(f"Validation result: errors={validation_errors}")
            
            if validation_errors:
                logger.warning(f"Validation errors for user {user_id}: {validation_errors}")
                error_msg = "❌ Обнаружены ошибки в данных:\n\n" + "\n".join([f"• {e}" for e in validation_errors])
                await query.edit_message_text(error_msg + "\n\nПожалуйста, исправьте данные и попробуйте снова.")
                return AI_CONVERSATION
            
            # Генерируем лендинг
            template_id = 'single_product' if agent.mode == 'SINGLE' else 'multi_product'
            logger.info(f"Starting generation for user {user_id}, template_id: {template_id}, landing_type: {user_data.get('landing_type')}")
            
            result = await self.code_generator.generate(template_id, user_data)
            
            logger.info(f"Generation result for user {user_id}: success={result.get('success')}, error={result.get('error', 'None')}")
            
            if result.get('success'):
                # Отправляем результат
                files_info = result.get('files', {})
                zip_file = files_info.get('zip_file')
                
                logger.info(f"Generation successful for user {user_id}, zip_file: {zip_file}")
                
                if zip_file and os.path.exists(zip_file):
                    logger.info(f"Sending zip file to user {user_id}: {zip_file}")
                    try:
                        with open(zip_file, 'rb') as f:
                            await self.app.bot.send_document(
                                chat_id=query.message.chat.id,
                                document=f,
                                filename=os.path.basename(zip_file),
                                caption="✅ Лендинг успешно сгенерирован!"
                            )
                        logger.info(f"Zip file sent successfully to user {user_id}")
                        try:
                            await query.edit_message_text(
                                "✅ Готово! Лендинг отправлен в чат.\n\nЧтобы создать новый — отправьте /ai"
                            )
                        except Exception:
                            pass
                    except Exception as send_error:
                        logger.error(f"Error sending zip file to user {user_id}: {send_error}", exc_info=True)
                        await query.edit_message_text(f"✅ Лендинг сгенерирован, но произошла ошибка при отправке: {str(send_error)}")
                else:
                    logger.error(f"Zip file not found for user {user_id}: {zip_file}")
                    await query.edit_message_text("✅ Лендинг сгенерирован, но файл не найден.")
                
                # Очищаем агента и временные файлы после успешной генерации
                logger.info(f"Cleaning up AI agent for user {user_id}")
                await self._cleanup_ai_agent_files(user_id)
                if user_id in self.ai_agents:
                    del self.ai_agents[user_id]
                if user_id in self.ai_agents_last_activity:
                    del self.ai_agents_last_activity[user_id]
                
                # Очищаем состояние агента из БД
                user_data = self._get_user_data(user_id)
                user_data.pop('ai_agent_state', None)
                user_data.pop('ai_agent_active', None)
                user_data.pop('last_activity', None)
                self._save_user_data(user_id, user_data, state=None, conversation_type=None)
                
                # Завершаем ConversationHandler
                return ConversationHandler.END
            else:
                error = result.get('error', 'Неизвестная ошибка')
                logger.error(f"Generation failed for user {user_id}: {error}")
                formatted_error = self._format_error_message(error)
                await query.edit_message_text(f"❌ Ошибка генерации:\n\n{formatted_error}")
                return AI_CONVERSATION  # Возвращаемся в состояние разговора для повторной попытки
        except Exception as e:
            logger.error(f"Error generating from AI agent for user {user_id}: {e}", exc_info=True)
            formatted_error = self._format_error_message(str(e))
            await query.edit_message_text(f"❌ Произошла ошибка:\n\n{formatted_error}")
            return AI_CONVERSATION  # Возвращаемся в состояние разговора
    
    async def handle_ai_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка запроса на редактирование данных в AI-режиме"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id not in self.ai_agents:
            await query.edit_message_text("❌ AI-агент не найден.")
            return
        
        try:
            await query.edit_message_text(
                "📝 Что хотите изменить?\n\n"
                "Напишите, какие данные нужно исправить, и я помогу вам их обновить."
            )
        except Exception as e:
            # Если сообщение не может быть отредактировано (например, содержимое не изменилось),
            # просто отправляем новое сообщение
            logger.warning(f"Could not edit message, sending new one: {e}")
            await query.message.reply_text(
                "📝 Что хотите изменить?\n\n"
                "Напишите, какие данные нужно исправить, и я помогу вам их обновить."
            )
            await query.answer()
    
    def _start_ai_agents_cleanup_task(self):
        """Запуск периодической очистки неактивных AI-агентов"""
        async def cleanup_task():
            import time
            while True:
                try:
                    await asyncio.sleep(300)  # Проверяем каждые 5 минут
                    current_time = time.time()
                    inactive_timeout = 1800  # 30 минут неактивности
                    
                    # Находим неактивных агентов
                    inactive_users = []
                    for user_id, last_activity in list(self.ai_agents_last_activity.items()):
                        if current_time - last_activity > inactive_timeout:
                            inactive_users.append(user_id)
                    
                    # Очищаем неактивных агентов
                    for user_id in inactive_users:
                        if user_id in self.ai_agents:
                            logger.info(f"Cleaning up inactive AI agent for user {user_id}")
                            # Очищаем временные файлы агента
                            await self._cleanup_ai_agent_files(user_id)
                            del self.ai_agents[user_id]
                            del self.ai_agents_last_activity[user_id]
                            
                            # Очищаем состояние агента из БД
                            user_data = self._get_user_data(user_id)
                            user_data.pop('ai_agent_state', None)
                            user_data.pop('ai_agent_active', None)
                            user_data.pop('last_activity', None)
                            self._save_user_data(user_id, user_data, state=None, conversation_type=None)
                    
                    if inactive_users:
                        logger.info(f"Cleaned up {len(inactive_users)} inactive AI agents")
                except Exception as e:
                    logger.error(f"Error in AI agents cleanup task: {e}", exc_info=True)
        
        # Запускаем задачу в фоне
        asyncio.create_task(cleanup_task())
        logger.info("AI agents cleanup task started")
    
    async def _cleanup_ai_agent_files(self, user_id: int):
        """Очистка временных файлов AI-агента"""
        try:
            import glob
            temp_pattern = os.path.join(Config.FILES_DIR, f'temp_{user_id}_*')
            temp_files = glob.glob(temp_pattern)
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"Removed temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning up AI agent files: {e}", exc_info=True)
