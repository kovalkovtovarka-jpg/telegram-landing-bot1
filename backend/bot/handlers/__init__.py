"""
Обработчики этапов сбора данных для создания лендинга
"""
from .base_handler import BaseHandler
from .hero_handler import HeroHandler
from .product_handler import ProductHandler
from .timer_handler import TimerHandler
from .price_handler import PriceHandler
from .form_handler import FormHandler
from .middle_block_handler import MiddleBlockHandler
from .description_handler import DescriptionHandler
from .reviews_handler import ReviewsHandler
from .footer_handler import FooterHandler
from .notification_handler import NotificationHandler
from .states import (
    SELECTING_LANDING_TYPE,
    COLLECTING_PRODUCT_NAME,
    COLLECTING_HERO_MEDIA,
    COLLECTING_HERO_DISCOUNT,
    COLLECTING_CHARACTERISTICS,
    COLLECTING_TIMER_SETTINGS,
    COLLECTING_PRICES,
    COLLECTING_FORM_OPTIONS,
    COLLECTING_MIDDLE_BLOCK,
    COLLECTING_DESCRIPTION,
    COLLECTING_REVIEWS_BLOCK,
    COLLECTING_FOOTER_INFO,
    COLLECTING_NOTIFICATION_TYPE,
    COLLECTING_NOTIFICATION_DATA,
    CONFIRMING,
    GENERATING
)

__all__ = [
    'BaseHandler',
    'HeroHandler',
    'ProductHandler',
    'TimerHandler',
    'PriceHandler',
    'FormHandler',
    'MiddleBlockHandler',
    'DescriptionHandler',
    'ReviewsHandler',
    'FooterHandler',
    'NotificationHandler',
    # States
    'SELECTING_LANDING_TYPE',
    'COLLECTING_PRODUCT_NAME',
    'COLLECTING_HERO_MEDIA',
    'COLLECTING_HERO_DISCOUNT',
    'COLLECTING_CHARACTERISTICS',
    'COLLECTING_TIMER_SETTINGS',
    'COLLECTING_PRICES',
    'COLLECTING_FORM_OPTIONS',
    'COLLECTING_MIDDLE_BLOCK',
    'COLLECTING_DESCRIPTION',
    'COLLECTING_REVIEWS_BLOCK',
    'COLLECTING_FOOTER_INFO',
    'COLLECTING_NOTIFICATION_TYPE',
    'COLLECTING_NOTIFICATION_DATA',
    'CONFIRMING',
    'GENERATING',
]

