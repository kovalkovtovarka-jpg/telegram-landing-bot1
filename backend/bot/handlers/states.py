"""
Константы состояний для обработчиков
"""
# Состояния диалога для /create (новая структура по 17 пунктам)
(
    SELECTING_LANDING_TYPE,           # 1. Выбор типа лендинга (10 вариантов)
    COLLECTING_PRODUCT_NAME,          # 2. Название товара
    COLLECTING_HERO_MEDIA,            # 3. Hero блок: фото/видео (п.1 структуры)
    COLLECTING_HERO_DISCOUNT,         # 4. Скидка в hero блоке
    COLLECTING_CHARACTERISTICS,       # 5. 3 яркие характеристики (п.3)
    COLLECTING_TIMER_SETTINGS,        # 6. Настройки таймера (п.4)
    COLLECTING_PRICES,                # 7. Цены (п.5)
    COLLECTING_FORM_OPTIONS,           # 8. Опции формы заказа (п.6)
    COLLECTING_MIDDLE_BLOCK,          # 9. Средний блок: видео/галерея/описание (п.7)
    COLLECTING_DESCRIPTION,           # 10. Описание с фото (п.8)
    COLLECTING_REVIEWS_BLOCK,         # 11. Блок отзывов (п.12)
    COLLECTING_FOOTER_INFO,           # 12. Информация для подвала (п.17)
    COLLECTING_NOTIFICATION_TYPE,     # 13. Тип уведомлений
    COLLECTING_NOTIFICATION_DATA,     # 14. Данные уведомлений
    CONFIRMING,                       # 15. Подтверждение
    GENERATING                        # 16. Генерация
) = range(16)

