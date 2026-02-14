"""
Генератор кода лендингов
"""
import os
import json
import shutil
import logging
from typing import Dict, Any, Optional
from backend.generator.llm_client import LLMClient
from backend.generator.prompt_builder import PromptBuilder
from backend.generator.template_loader import TemplateLoader
from backend.generator.code_validator import CodeValidator
from backend.config import Config

logger = logging.getLogger(__name__)

class CodeGenerator:
    """Генератор HTML/CSS/JS кода для лендингов"""
    
    def __init__(self, templates_path: str = 'landing-templates.json'):
        """
        Инициализация генератора
        
        Args:
            templates_path: Путь к файлу с шаблонами
        """
        self.llm_client = LLMClient()
        self.prompt_builder = PromptBuilder(templates_path)
        self.template_loader = TemplateLoader(templates_path)
        self.validator = CodeValidator()
        
        # Создаем директорию для файлов если не существует
        os.makedirs(Config.FILES_DIR, exist_ok=True)
    
    async def generate(self, template_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Генерация кода лендинга
        
        Args:
            template_id: ID шаблона
            user_data: Данные пользователя
            
        Returns:
            Словарь с путями к файлам и метаданными
        """
        import time
        start_time = time.time()
        
        try:
            # Для новой структуры используем landing_type как template_id
            if user_data.get('landing_type'):
                template_id = user_data.get('landing_type', 'single_product')
            
            # Получаем информацию о шаблоне (может быть None для новой структуры)
            template_info = self.template_loader.get_template(template_id)
            if not template_info and not user_data.get('landing_type'):
                raise ValueError(f"Шаблон {template_id} не найден")
            
            # Проверяем кэш промптов
            from backend.utils.cache import prompt_cache
            prompt = prompt_cache.get(user_data)
            
            if not prompt:
                # Сжимаем данные пользователя для оптимизации промпта
                from backend.utils.prompt_compressor import PromptCompressor
                compressed_data = PromptCompressor.compress_user_data(user_data)
                
                # Строим промпт, если нет в кэше
                prompt = self.prompt_builder.build_prompt(template_id, compressed_data)
                
                # Проверяем и сжимаем промпт при необходимости
                prompt, was_compressed = PromptCompressor.check_and_compress_prompt(prompt)
                if was_compressed:
                    logger.warning("Prompt was compressed due to length")
                
                # Сохраняем в кэш
                prompt_cache.set(user_data, prompt)
            else:
                logger.info("Using cached prompt")
            
            # Логируем промпт для отладки
            logger.info(f"Generated prompt length: {len(prompt)} characters")
            logger.debug(f"Prompt preview (first 2000 chars):\n{prompt[:2000]}")
            
            # Сохраняем полный промпт в файл для отладки
            import os
            from datetime import datetime
            prompts_dir = os.path.join(Config.FILES_DIR, 'prompts')
            os.makedirs(prompts_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            product_name = user_data.get('product_name', 'unknown').replace('/', '_').replace('\\', '_')[:50]
            prompt_file = os.path.join(prompts_dir, f"prompt_{timestamp}_{product_name}.txt")
            try:
                with open(prompt_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== PROMPT FOR LLM ===\n")
                    f.write(f"Generated at: {datetime.now().isoformat()}\n")
                    f.write(f"Product: {user_data.get('product_name', 'Unknown')}\n")
                    f.write(f"Landing type: {user_data.get('landing_type', 'Unknown')}\n")
                    f.write(f"Length: {len(prompt)} characters\n")
                    f.write(f"\n{'='*80}\n\n")
                    f.write(prompt)
                logger.info(f"Full prompt saved to: {prompt_file}")
            except Exception as e:
                logger.warning(f"Failed to save prompt to file: {e}")
            
            # Логируем часть промпта с цветами и шрифтами (если есть)
            if 'ЦВЕТОВАЯ СХЕМА' in prompt or 'РЕКОМЕНДУЕМАЯ ЦВЕТОВАЯ СХЕМА' in prompt:
                color_section_start = prompt.find('ЦВЕТОВАЯ СХЕМА') or prompt.find('РЕКОМЕНДУЕМАЯ ЦВЕТОВАЯ СХЕМА')
                if color_section_start > 0:
                    color_section = prompt[color_section_start:color_section_start+1000]
                    logger.info(f"Color and font recommendations in prompt:\n{color_section}")
            
            logger.info(f"User data keys: {list(user_data.keys())}")
            logger.info(f"Form data - sizes: {user_data.get('sizes')}, colors: {user_data.get('colors')}, characteristics: {user_data.get('characteristics_list')}")
            logger.info(f"Landing type: {user_data.get('landing_type')}, Product name: {user_data.get('product_name')}")
            
            # Генерируем код через LLM
            generated_code = await self.llm_client.generate_landing(prompt)
            
            # Валидируем код
            validation_result = self.validator.validate(generated_code)
            
            # Проверяем данные пользователя
            if user_data:
                user_data_errors, user_data_warnings = self.validator._check_user_data(
                    generated_code.get('html', ''), user_data
                )
                validation_result['errors'].extend(user_data_errors)
                validation_result['warnings'].extend(user_data_warnings)
                validation_result['valid'] = len(validation_result['errors']) == 0
            
            # Если код невалиден или слишком короткий - используем fallback
            html = generated_code.get('html', '')
            css = generated_code.get('css', '')
            js = generated_code.get('js', '')
            
            # Проверяем качество CSS
            css_lines = len(css.split('\n')) if css else 0
            css_has_styles = bool(css and '{' in css and '}' in css and ':' in css)
            css_has_colors = bool(css and ('color' in css.lower() or 'background' in css.lower() or 'gradient' in css.lower()))
            css_has_variables = bool(css and ':root' in css and '--primary-color' in css)
            css_has_fonts = bool(css and ('font-family' in css.lower() or '@import' in css.lower() or 'googleapis.com' in css.lower()))
            
            logger.info(f"Generated code lengths: HTML={len(html)}, CSS={len(css)} ({css_lines} lines), JS={len(js)}")
            logger.info(f"CSS quality: has_styles={css_has_styles}, has_colors={css_has_colors}, has_variables={css_has_variables}, has_fonts={css_has_fonts}")
            
            # Проверяем, содержит ли CSS рекомендуемые цвета (если есть анализ товара)
            css_has_recommended_colors = True
            if user_data.get('landing_type'):
                from backend.generator.prompt_builder_new import NewPromptBuilder
                prompt_builder = NewPromptBuilder()
                product_name = user_data.get('product_name', 'Товар')
                description = user_data.get('description_text', '')
                style_suggestion = prompt_builder._analyze_product_and_suggest_style(product_name, description)
                recommended_primary = style_suggestion['colors']['primary']
                # Проверяем, есть ли рекомендуемый цвет в CSS
                css_has_recommended_colors = recommended_primary in css
                if not css_has_recommended_colors:
                    logger.warning(f"CSS не содержит рекомендуемый цвет {recommended_primary}. CSS snippet: {css[:500]}")
            
            # Более строгая проверка CSS
            css_is_valid = (css_has_styles and css_has_colors and css_has_variables and css_lines >= 300)
            
            if not validation_result['valid'] or len(html) < 200 or len(css) < 100 or len(js) < 50 or not css_is_valid:
                logger.warning(f"LLM вернул неполный код или CSS недостаточно детальный. HTML={len(html)}, CSS={len(css)} ({css_lines} lines), valid={css_is_valid}")
                if not css_is_valid:
                    logger.warning(f"CSS не соответствует требованиям: lines={css_lines} (min 300), has_styles={css_has_styles}, has_colors={css_has_colors}, has_variables={css_has_variables}. Используем fallback-шаблон.")
                generated_code = self._create_fallback_code(template_id, user_data)
                validation_result = self.validator.validate(generated_code)
            elif not css_has_recommended_colors and user_data.get('landing_type'):
                logger.warning(f"CSS не содержит рекомендуемые цвета. Заменяем на fallback с правильными цветами.")
                generated_code = self._create_fallback_code(template_id, user_data)
                validation_result = self.validator.validate(generated_code)
            
            # Добавляем необходимые элементы
            generated_code = self._add_required_elements(generated_code, template_id, user_data)
            
            # Сохраняем файлы
            files_info = await self._save_files(generated_code, template_id, user_data)
            
            # Копируем медиа файлы пользователя в проект
            if files_info.get('project_dir'):
                await self._copy_user_media(files_info.get('project_dir', ''), user_data)
            
            generation_time = int(time.time() - start_time)
            
            return {
                'success': True,
                'files': files_info,
                'template_id': template_id,
                'template_name': template_info.get('name', '') if template_info else user_data.get('landing_type', ''),
                'generation_time': generation_time,
                'tokens_used': generated_code.get('tokens_used', 0),
                'validation': validation_result
            }
            
        except Exception as e:
            logger.error(f"Ошибка при генерации: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'generation_time': int(time.time() - start_time)
            }
    
    async def _fix_errors(self, code: Dict[str, str], errors: list) -> Dict[str, str]:
        """
        Попытка исправить ошибки в коде
        
        Args:
            code: Сгенерированный код
            errors: Список ошибок
            
        Returns:
            Исправленный код
        """
        # Простые исправления можно сделать здесь
        # Для сложных - повторный запрос к LLM
        
        fixed_html = code.get('html', '')
        fixed_css = code.get('css', '')
        fixed_js = code.get('js', '')
        
        # Добавляем недостающие элементы
        if '</body>' in fixed_html and 'TikTok Pixel' not in fixed_html:
            # TikTok Pixel будет добавлен в _add_required_elements
            pass
        
        return {
            'html': fixed_html,
            'css': fixed_css,
            'js': fixed_js,
            'tokens_used': code.get('tokens_used', 0)
        }
    
    def _add_required_elements(self, code: Dict[str, str], template_id: str, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Добавление обязательных элементов (TikTok Pixel, интеграции)
        
        Args:
            code: Сгенерированный код
            template_id: ID шаблона
            user_data: Данные пользователя
            
        Returns:
            Код с добавленными элементами
        """
        html = code.get('html', '')
        
        # Добавляем TikTok Pixel если его нет
        if '</body>' in html and 'TikTok Pixel' not in html:
            tiktok_pixel = user_data.get('tiktok_pixel_id', Config.OPENAI_API_KEY[:20] if Config.OPENAI_API_KEY else 'DEFAULT_ID')
            
            pixel_code = f"""
  <!-- TikTok Pixel Code Start -->
  <script>
  !function (w, d, t) {{
    w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie","holdConsent","revokeConsent","grantConsent"],ttq.setAndDefer=function(t,e){{t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}};for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);ttq.instance=function(t){{for(
  var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e}},ttq.load=function(e,n){{var r="https://analytics.tiktok.com/i18n/pixel/events.js",o=n&&n.partner;ttq._i=ttq._i||{{}},ttq._i[e]=[],ttq._i[e]._u=r,ttq._t=ttq._t||{{}},ttq._t[e]=+new Date,ttq._o=ttq._o||{{}},ttq._o[e]=n||{{}};n=document.createElement("script")
  ;n.type="text/javascript",n.async=!0,n.src=r+"?sdkid="+e+"&lib="+t;e=document.getElementsByTagName("script")[0];e.parentNode.insertBefore(n,e)}};


    ttq.load('{tiktok_pixel}');
    ttq.page();
  }}(window, document, 'ttq');
  </script>
  <!-- TikTok Pixel Code End -->"""
            
            html = html.replace('</body>', pixel_code + '\n</body>')
        
        # Убеждаемся что формы ведут на send.php
        html = html.replace('action=""', 'action="send.php"')
        html = html.replace("action=''", "action='send.php'")
        # Исправляем sendCPA.php на send.php
        html = html.replace('action="sendCPA.php"', 'action="send.php"')
        html = html.replace("action='sendCPA.php'", "action='send.php'")
        
        # Исправляем абсолютные пути к медиа файлам на относительные
        import re
        # Паттерн для поиска абсолютных путей к фото отзывов
        html = re.sub(
            r'src="generated_landings/[^"]+/photos/review_(\d+)\.(jpg|jpeg|png)"',
            r'src="img/review_\1.\2"',
            html
        )
        # Также исправляем пути с одинарными кавычками
        html = re.sub(
            r"src='generated_landings/[^']+/photos/review_(\d+)\.(jpg|jpeg|png)'",
            r"src='img/review_\1.\2'",
            html
        )
        
        # Исправляем пути к hero медиа
        html = re.sub(
            r'src="[^"]*hero\.(jpg|jpeg|png|mp4|webm)"',
            r'src="img/hero.\1"',
            html
        )
        html = re.sub(
            r"src='[^']*hero\.(jpg|jpeg|png|mp4|webm)'",
            r"src='img/hero.\1'",
            html
        )
        
        # Исправляем пути к галерее
        html = re.sub(
            r'src="[^"]*gallery_(\d+)\.(jpg|jpeg|png)"',
            r'src="img/gallery_\1.\2"',
            html
        )
        html = re.sub(
            r"src='[^']*gallery_(\d+)\.(jpg|jpeg|png)'",
            r"src='img/gallery_\1.\2'",
            html
        )
        
        # Исправляем пути к фото описания
        html = re.sub(
            r'src="[^"]*description_(\d+)\.(jpg|jpeg|png)"',
            r'src="img/description_\1.\2"',
            html
        )
        html = re.sub(
            r"src='[^']*description_(\d+)\.(jpg|jpeg|png)'",
            r"src='img/description_\1.\2'",
            html
        )
        
        # Исправляем пути к среднему видео
        html = re.sub(
            r'src="[^"]*middle\.(mp4|webm|ogg)"',
            r'src="img/middle.\1"',
            html
        )
        html = re.sub(
            r"src='[^']*middle\.(mp4|webm|ogg)'",
            r"src='img/middle.\1'",
            html
        )
        
        code['html'] = html
        return code
    
    async def _save_files(self, code: Dict[str, str], template_id: str, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Сохранение файлов на диск
        
        Args:
            code: Сгенерированный код
            template_id: ID шаблона
            user_data: Данные пользователя
            
        Returns:
            Словарь с путями к файлам
        """
        import uuid
        from datetime import datetime
        
        # Создаем уникальную папку для проекта
        from backend.utils.path_validator import get_safe_path
        
        project_id = str(uuid.uuid4())[:8]
        project_dir = get_safe_path(f"project_{project_id}", Config.FILES_DIR)
        os.makedirs(project_dir, exist_ok=True)
        
        # Создаем подпапки с валидацией
        css_dir = get_safe_path('css', project_dir)
        js_dir = get_safe_path('js', project_dir)
        img_dir = get_safe_path('img', project_dir)
        os.makedirs(css_dir, exist_ok=True)
        os.makedirs(js_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)
        
        # Определяем имена файлов с валидацией
        html_file = get_safe_path('index.html', project_dir)
        css_file = get_safe_path('style.css', css_dir)
        js_file = get_safe_path('script.js', js_dir)
        
            # Проверяем, используется ли новая структура (для товарщиков)
        is_new_structure = user_data.get('landing_type') is not None
        
        # Сохраняем HTML (index.html)
        with open(html_file, 'w', encoding='utf-8') as f:
            # Заменяем пути к CSS и JS если нужно
            html = code.get('html', '')
            html = html.replace('href="css/pillow.css"', 'href="css/style.css"')
            html = html.replace('href="css/styles.css"', 'href="css/style.css"')
            html = html.replace('src="js/pillow.js"', 'src="js/script.js"')
            html = html.replace('src="js/script.js"', 'src="js/script.js"')
            
            # Исправляем абсолютные пути к фото отзывов на относительные
            import re
            # Паттерн для поиска абсолютных путей к фото отзывов
            html = re.sub(
                r'src="generated_landings/[^"]+/photos/review_(\d+)\.jpg"',
                r'src="img/review_\1.jpg"',
                html
            )
            # Также исправляем пути с одинарными кавычками
            html = re.sub(
                r"src='generated_landings/[^']+/photos/review_(\d+)\.jpg'",
                r"src='img/review_\1.jpg'",
                html
            )
            
            f.write(html)
        
        # Сохраняем CSS
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(code.get('css', ''))
        
        # Сохраняем JS
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(code.get('js', ''))
        
        # Создаем страницу благодарности good.html
        good_html = self._create_good_page(user_data, code.get('css', ''))
        good_file = os.path.join(project_dir, 'good.html')
        with open(good_file, 'w', encoding='utf-8') as f:
            f.write(good_html)
        
        # Для новой структуры создаем дополнительные файлы
        if is_new_structure:
            # oferta.html - публичная оферта
            oferta_html = code.get('oferta_html', self._create_default_oferta(user_data, code.get('css', '')))
            oferta_file = os.path.join(project_dir, 'oferta.html')
            with open(oferta_file, 'w', encoding='utf-8') as f:
                f.write(oferta_html)
            
            # obmen.html - возврат и обмен
            obmen_html = code.get('obmen_html', self._create_default_obmen(user_data, code.get('css', '')))
            obmen_file = os.path.join(project_dir, 'obmen.html')
            with open(obmen_file, 'w', encoding='utf-8') as f:
                f.write(obmen_html)
            
            # politics.html - политика конфиденциальности
            politics_html = code.get('politics_html', self._create_default_politics(user_data, code.get('css', '')))
            politics_file = os.path.join(project_dir, 'politics.html')
            with open(politics_file, 'w', encoding='utf-8') as f:
                f.write(politics_html)
            
            # send.php - обработчик отправки (обновляем для новой структуры)
            send_php = code.get('send_php', '')
            if send_php:
                php_file = os.path.join(project_dir, 'send.php')
                with open(php_file, 'w', encoding='utf-8') as f:
                    f.write(send_php)
            else:
                # Используем метод создания send.php
                await self._create_send_php(project_dir, user_data)
        
        # Создаем ZIP архив
        zip_path = await self._create_zip(project_dir, project_id)
        
        return {
            'project_dir': project_dir,
            'project_id': project_id,
            'html_file': html_file,
            'css_file': css_file,
            'js_file': js_file,
            'zip_file': zip_path,
            'files_path': project_dir
        }
    
    def _create_default_oferta(self, user_data: Dict[str, Any], main_css: str) -> str:
        """Создание страницы публичной оферты"""
        footer_info = user_data.get('footer_info', {})
        company_name = footer_info.get('company_name', '') if footer_info.get('type') == 'ul' else footer_info.get('fio', '')
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Публичная оферта</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <h1>Публичная оферта</h1>
        <div class="content">
            <p>Настоящая публичная оферта является официальным предложением {company_name if company_name else "продавца"} о продаже товаров через интернет-магазин.</p>
            <h2>1. Общие положения</h2>
            <p>Настоящая публичная оферта определяет условия продажи товаров через интернет-магазин.</p>
            <h2>2. Предмет договора</h2>
            <p>Продавец обязуется передать в собственность Покупателю товар, а Покупатель обязуется принять и оплатить товар на условиях настоящей оферты.</p>
            <h2>3. Цена товара</h2>
            <p>Цена товара указана на сайте интернет-магазина. Продавец имеет право в одностороннем порядке изменить цену товара.</p>
            <h2>4. Порядок оформления заказа</h2>
            <p>Заказ оформляется путем заполнения формы на сайте интернет-магазина.</p>
            <h2>5. Оплата товара</h2>
            <p>Оплата товара производится способами, указанными на сайте интернет-магазина.</p>
            <h2>6. Доставка товара</h2>
            <p>Доставка товара осуществляется способами, указанными на сайте интернет-магазина.</p>
            <h2>7. Возврат товара</h2>
            <p>Возврат товара осуществляется в соответствии с законодательством Республики Беларусь.</p>
            <p><a href="index.html">Вернуться на главную</a></p>
        </div>
    </div>
</body>
</html>'''
    
    def _create_default_obmen(self, user_data: Dict[str, Any], main_css: str) -> str:
        """Создание страницы возврата и обмена"""
        return '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Возврат и обмен</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <h1>Возврат и обмен товара</h1>
        <div class="content">
            <h2>Условия возврата</h2>
            <p>Вы можете вернуть товар в течение 14 дней с момента покупки при условии сохранения товарного вида, потребительских свойств и упаковки.</p>
            <h2>Условия обмена</h2>
            <p>Обмен товара возможен в течение 14 дней с момента покупки при условии сохранения товарного вида и упаковки.</p>
            <h2>Порядок возврата</h2>
            <ol>
                <li>Свяжитесь с нами по указанным контактам</li>
                <li>Укажите причину возврата</li>
                <li>Отправьте товар по указанному адресу</li>
                <li>После проверки товара мы вернем вам деньги</li>
            </ol>
            <h2>Порядок обмена</h2>
            <ol>
                <li>Свяжитесь с нами по указанным контактам</li>
                <li>Укажите желаемый товар для обмена</li>
                <li>Отправьте товар по указанному адресу</li>
                <li>После проверки мы отправим вам новый товар</li>
            </ol>
            <p><a href="index.html">Вернуться на главную</a></p>
        </div>
    </div>
</body>
</html>'''
    
    def _create_default_politics(self, user_data: Dict[str, Any], main_css: str) -> str:
        """Создание страницы политики конфиденциальности"""
        return '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Политика конфиденциальности</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <h1>Политика конфиденциальности</h1>
        <div class="content">
            <h2>1. Общие положения</h2>
            <p>Настоящая Политика конфиденциальности определяет порядок обработки и защиты персональных данных пользователей сайта.</p>
            <h2>2. Сбор персональных данных</h2>
            <p>Мы собираем следующие персональные данные:</p>
            <ul>
                <li>Имя</li>
                <li>Номер телефона</li>
                <li>Адрес доставки</li>
            </ul>
            <h2>3. Использование персональных данных</h2>
            <p>Персональные данные используются исключительно для:</p>
            <ul>
                <li>Обработки заказов</li>
                <li>Связи с клиентом</li>
                <li>Доставки товара</li>
            </ul>
            <h2>4. Защита персональных данных</h2>
            <p>Мы принимаем все необходимые меры для защиты персональных данных от несанкционированного доступа, изменения, раскрытия или уничтожения.</p>
            <h2>5. Передача персональных данных третьим лицам</h2>
            <p>Мы не передаем персональные данные третьим лицам без согласия пользователя, за исключением случаев, предусмотренных законодательством.</p>
            <h2>6. Изменения в Политике конфиденциальности</h2>
            <p>Мы оставляем за собой право вносить изменения в настоящую Политику конфиденциальности. Все изменения вступают в силу с момента их публикации на сайте.</p>
            <p><a href="index.html">Вернуться на главную</a></p>
        </div>
    </div>
</body>
</html>'''
    
    async def _create_send_php(self, project_dir: str, user_data: Dict[str, Any]):
        """Создание send.php для новой структуры"""
        product_name = user_data.get('product_name', 'Товар')
        product_price = user_data.get('new_price', user_data.get('price', '99 BYN'))
        
        notification_type = user_data.get('notification_type', 'telegram')
        notification_email = user_data.get('notification_email', '')
        notification_telegram_token = user_data.get('notification_telegram_token', '')
        notification_telegram_chat_id = user_data.get('notification_telegram_chat_id', '')
        
        # Формируем сообщение с данными формы
        php_content = f'''<?php
// Обработчик отправки заявок с лендинга
// Товар: {product_name}
// Цена: {product_price}

// Получаем данные из формы
$name = isset($_POST['name']) ? htmlspecialchars($_POST['name']) : '';
$phone = isset($_POST['phone']) ? htmlspecialchars($_POST['phone']) : '';
$address = isset($_POST['address']) ? htmlspecialchars($_POST['address']) : '';

// Опциональные поля
$size = isset($_POST['size']) ? htmlspecialchars($_POST['size']) : '';
$color = isset($_POST['color']) ? htmlspecialchars($_POST['color']) : '';
$characteristic = isset($_POST['characteristic']) ? htmlspecialchars($_POST['characteristic']) : '';

// Формируем сообщение
$message = "Новый заказ:\\n\\n";
$message .= "Товар: {product_name}\\n";
$message .= "Цена: {product_price}\\n";
$message .= "Имя: " . $name . "\\n";
$message .= "Телефон: " . $phone . "\\n";
if ($address) $message .= "Адрес: " . $address . "\\n";
if ($size) $message .= "Размер: " . $size . "\\n";
if ($color) $message .= "Цвет: " . $color . "\\n";
if ($characteristic) $message .= "Характеристика: " . $characteristic . "\\n";

'''
        
        if notification_type == 'telegram' and notification_telegram_token and notification_telegram_chat_id:
            php_content += f'''// Отправка в Telegram
$telegramBotToken = '{notification_telegram_token}';
$telegramChatId = '{notification_telegram_chat_id}';

$url = "https://api.telegram.org/bot" . $telegramBotToken . "/sendMessage";
$data = [
    'chat_id' => $telegramChatId,
    'text' => $message,
    'parse_mode' => 'HTML'
];

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($data));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode == 200) {{
    header('Location: good.html');
    exit;
}} else {{
    echo "Ошибка отправки заявки";
}}
'''
        elif notification_type == 'email' and notification_email:
            php_content += f'''// Отправка на email
$to = '{notification_email}';
$subject = "Новый заказ: {product_name}";
$headers = "From: noreply@landing.com\\r\\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\\r\\n";

$mailSent = mail($to, $subject, $message, $headers);

if ($mailSent) {{
    header('Location: good.html');
    exit;
}} else {{
    echo "Ошибка отправки заявки";
}}
'''
        else:
            php_content += '''// Уведомления не настроены
echo "Ошибка: уведомления не настроены";
'''
        
        php_file = os.path.join(project_dir, 'send.php')
        with open(php_file, 'w', encoding='utf-8') as f:
            f.write(php_content)
    
    async def _create_zip(self, project_dir: str, project_id: str) -> str:
        """
        Создание ZIP архива с файлами проекта
        
        Args:
            project_dir: Директория проекта
            project_id: ID проекта
            
        Returns:
            Путь к ZIP файлу
        """
        import zipfile
        import os
        
        zip_path = os.path.join(Config.FILES_DIR, f"project_{project_id}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, project_dir)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def _create_fallback_code(self, template_id: str, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Создание базового шаблона если LLM вернул неполный код
        
        Args:
            template_id: ID шаблона
            user_data: Данные пользователя
            
        Returns:
            Базовый код с данными пользователя
        """
        html = self._create_base_html(user_data)
        
        # Для новой структуры используем анализ товара для подбора цветов
        if user_data.get('landing_type'):
            from backend.generator.prompt_builder_new import NewPromptBuilder
            prompt_builder = NewPromptBuilder()
            product_name = user_data.get('product_name', 'Товар')
            description = user_data.get('description_text', '')
            style_suggestion = prompt_builder._analyze_product_and_suggest_style(product_name, description)
            suggested_colors = style_suggestion['colors']
            suggested_fonts = style_suggestion['fonts']
            
            # Создаем CSS с рекомендуемыми цветами и шрифтами
            css = self._create_base_css_with_colors(suggested_colors, suggested_fonts)
            logger.info(f"Using fallback CSS with analyzed colors: {suggested_colors['primary']}, fonts: {suggested_fonts}")
        else:
            design_style = user_data.get('design_style', 'vibrant')
            css = self._create_base_css(design_style)
        
        js = self._create_base_js()
        
        return {
            'html': html,
            'css': css,
            'js': js,
            'tokens_used': 0
        }
    
    def _create_base_html(self, user_data: Dict[str, Any]) -> str:
        """Создание базового HTML с данными пользователя"""
        product_name = user_data.get('product_name', 'Товар')
        product_description = user_data.get('product_description', 'Описание товара')
        old_price = user_data.get('old_price', '152 BYN')
        new_price = user_data.get('new_price', '99 BYN')
        benefits = user_data.get('benefits', [])
        
        # Данные для формы
        sizes = user_data.get('sizes', [])
        colors = user_data.get('colors', [])
        characteristics_list = user_data.get('characteristics_list', [])
        
        # Формируем дополнительные поля формы
        form_fields_html = ''
        if sizes:
            form_fields_html += '                    <select name="size" class="form-input" required>\n'
            form_fields_html += '                        <option value="">Выберите размер</option>\n'
            for size in sizes:
                form_fields_html += f'                        <option value="{size}">{size}</option>\n'
            form_fields_html += '                    </select>\n'
        
        if colors:
            form_fields_html += '                    <div class="color-selector">\n'
            for color in colors:
                form_fields_html += f'                        <label class="color-option"><input type="radio" name="color" value="{color}" required> {color}</label>\n'
            form_fields_html += '                    </div>\n'
        
        if characteristics_list:
            form_fields_html += '                    <select name="characteristic" class="form-input" required>\n'
            form_fields_html += '                        <option value="">Выберите характеристику</option>\n'
            for char in characteristics_list:
                form_fields_html += f'                        <option value="{char}">{char}</option>\n'
            form_fields_html += '                    </select>\n'
        
        benefits_html = ''
        if isinstance(benefits, list):
            benefits_html = '\n'.join([f'                <li><span class="check-icon">✓</span>{b}</li>' for b in benefits])
        else:
            benefits_html = f'                <li><span class="check-icon">✓</span>{benefits}</li>'
        
        # Карусель изображений
        photos_html = ''
        photos = user_data.get('photos', [])
        if photos:
            photos_html += '                <div class="carousel-container">\n'
            photos_html += '                    <div class="carousel-wrapper">\n'
            photos_html += '                        <div class="carousel-track" id="imageCarousel">\n'
            for i, photo_path in enumerate(photos):
                photo_name = f'photo_{i+1}.jpg'
                photos_html += f'                            <div class="carousel-slide"><img src="img/{photo_name}" alt="{product_name}" class="product-image"></div>\n'
            photos_html += '                        </div>\n'
            photos_html += '                        <button class="carousel-btn carousel-btn-prev" id="prevBtn" aria-label="Предыдущее фото">‹</button>\n'
            photos_html += '                        <button class="carousel-btn carousel-btn-next" id="nextBtn" aria-label="Следующее фото">›</button>\n'
            photos_html += '                    </div>\n'
            photos_html += '                    <div class="carousel-dots" id="carouselDots"></div>\n'
            photos_html += '                </div>\n'
        else:
            photos_html = f'                <div class="carousel-container">\n'
            photos_html += f'                    <div class="carousel-wrapper">\n'
            photos_html += f'                        <div class="carousel-track"><div class="carousel-slide"><img src="img/photo_1.jpg" alt="{product_name}" class="product-image"></div></div>\n'
            photos_html += '                    </div>\n'
            photos_html += '                </div>\n'
        
        # Карусель отзывов
        reviews_html = ''
        reviews = user_data.get('reviews', [])
        if reviews and isinstance(reviews, list) and len(reviews) > 0:
            reviews_html = '        <section class="reviews-section">\n'
            reviews_html += '            <h2 class="reviews-title">Отзывы покупателей</h2>\n'
            reviews_html += '            <div class="reviews-carousel-container">\n'
            reviews_html += '                <div class="reviews-carousel-wrapper">\n'
            reviews_html += '                    <div class="reviews-carousel-track" id="reviewsCarousel">\n'
            for review in reviews:
                if isinstance(review, dict):
                    review_name = review.get('name', 'Покупатель')
                    review_text = review.get('text', '')
                    review_photo = review.get('photo', '')
                    review_rating = review.get('rating', 5)
                else:
                    review_name = 'Покупатель'
                    review_text = str(review)
                    review_photo = ''
                    review_rating = 5
                
                reviews_html += '                        <div class="review-slide">\n'
                reviews_html += '                            <div class="review-card">\n'
                if review_photo:
                    reviews_html += f'                                <img src="{review_photo}" alt="{review_name}" class="review-photo">\n'
                reviews_html += f'                                <div class="review-rating">{"★" * review_rating}</div>\n'
                reviews_html += f'                                <p class="review-text">"{review_text}"</p>\n'
                reviews_html += f'                                <p class="review-author">— {review_name}</p>\n'
                reviews_html += '                            </div>\n'
                reviews_html += '                        </div>\n'
            reviews_html += '                    </div>\n'
            reviews_html += '                    <button class="reviews-carousel-btn reviews-carousel-btn-prev" id="reviewsPrevBtn" aria-label="Предыдущий отзыв">‹</button>\n'
            reviews_html += '                    <button class="reviews-carousel-btn reviews-carousel-btn-next" id="reviewsNextBtn" aria-label="Следующий отзыв">›</button>\n'
            reviews_html += '                </div>\n'
            reviews_html += '            </div>\n'
            reviews_html += '        </section>\n'
        
        # Подвал с информацией о компании
        footer_html = ''
        footer_info = user_data.get('footer_info', {})
        if not footer_info:
            # Пробуем получить из extra_fields или других полей
            footer_info = {
                'company_name': user_data.get('company_name', ''),
                'ip_name': user_data.get('ip_name', ''),
                'unp': user_data.get('unp', ''),
                'ogrn': user_data.get('ogrn', ''),
                'inn': user_data.get('inn', ''),
                'address': user_data.get('address', ''),
                'phone': user_data.get('phone', ''),
                'email': user_data.get('email', '')
            }
        
        # Формируем подвал, если есть хотя бы одно поле
        if any(footer_info.values()):
            footer_html = '    <footer class="footer">\n'
            footer_html += '        <div class="footer-content">\n'
            
            if footer_info.get('company_name'):
                footer_html += f'            <p class="footer-company">{footer_info["company_name"]}</p>\n'
            
            if footer_info.get('ip_name'):
                footer_html += f'            <p class="footer-ip">ИП {footer_info["ip_name"]}</p>\n'
            
            footer_items = []
            if footer_info.get('unp'):
                footer_items.append(f'УНП: {footer_info["unp"]}')
            if footer_info.get('ogrn'):
                footer_items.append(f'ОГРН: {footer_info["ogrn"]}')
            if footer_info.get('inn'):
                footer_items.append(f'ИНН: {footer_info["inn"]}')
            
            if footer_items:
                footer_html += f'            <p class="footer-legal">{" | ".join(footer_items)}</p>\n'
            
            if footer_info.get('address'):
                footer_html += f'            <p class="footer-address">{footer_info["address"]}</p>\n'
            
            contact_items = []
            if footer_info.get('phone'):
                contact_items.append(f'Тел: {footer_info["phone"]}')
            if footer_info.get('email'):
                contact_items.append(f'Email: {footer_info["email"]}')
            
            if contact_items:
                footer_html += f'            <p class="footer-contact">{" | ".join(contact_items)}</p>\n'
            
            footer_html += '        </div>\n'
            footer_html += '    </footer>\n'
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="container">
        <section class="hero-section">
            <div class="product-visual">
{photos_html}            </div>
            
            <div class="product-content">
                <h1 class="product-title">{product_name.upper()}</h1>
                <p class="product-description">{product_description}</p>
                
                <div class="pricing-section">
                    <div class="prices">
                        <span class="old-price">{old_price}</span>
                        <span class="new-price">{new_price}</span>
                    </div>
                </div>
                
                <div class="countdown-section">
                    <p class="countdown-label">Акция закончится через:</p>
                    <div id="timer" class="timer">23:59:59</div>
                </div>
                
                <form action="send.php" method="POST" class="order-form" id="orderForm">
                    <input type="text" name="name" placeholder="Ваше имя" class="form-input" required>
                    <input type="tel" name="phone" id="phone" placeholder="+375 (__) ___-__-__" class="form-input" required>
{form_fields_html}                    <!-- Honeypot поле для защиты от спама -->
                    <input type="text" name="website" class="honeypot-field" tabindex="-1" autocomplete="off" aria-hidden="true">
                    <input type="hidden" name="form_start_time" id="formStartTime" value="">
                    <button type="submit" class="btn-order">Заказать</button>
                </form>
            </div>
        </section>
        
        <section class="benefits-section">
            <h2 class="benefits-title">Преимущества</h2>
            <ul class="benefits-list">
{benefits_html}            </ul>
        </section>
{reviews_html}    </div>
{footer_html}
    <script src="js/script.js"></script>
</body>
</html>'''
    
    def _create_good_page(self, user_data: Dict[str, Any], main_css: str) -> str:
        """Создание страницы благодарности good.html"""
        product_name = user_data.get('product_name', 'Товар')
        
        # Информация о связанном товаре
        related_product = user_data.get('related_product', {})
        related_html = ''
        
        if related_product and isinstance(related_product, dict):
            related_name = related_product.get('name', '')
            related_url = related_product.get('url', '#')
            related_image = related_product.get('image', '')
            related_price = related_product.get('price', '')
            
            if related_name:
                related_html = '''
        <section class="related-product-section">
            <h2 class="related-title">С этим также покупают</h2>
            <a href="''' + related_url + '''" class="related-product-card">
                <div class="related-product-image-wrapper">
                    <img src="''' + (related_image if related_image else 'img/photo_1.jpg') + '''" alt="''' + related_name + '''" class="related-product-image">
                </div>
                <div class="related-product-info">
                    <h3 class="related-product-name">''' + related_name + '''</h3>
                    ''' + (f'<p class="related-product-price">{related_price}</p>' if related_price else '') + '''
                </div>
            </a>
        </section>'''
        
        # Подвал
        footer_html = ''
        footer_info = user_data.get('footer_info', {})
        if not footer_info:
            footer_info = {
                'company_name': user_data.get('company_name', ''),
                'ip_name': user_data.get('ip_name', ''),
                'unp': user_data.get('unp', ''),
                'ogrn': user_data.get('ogrn', ''),
                'inn': user_data.get('inn', ''),
                'address': user_data.get('address', ''),
                'phone': user_data.get('phone', ''),
                'email': user_data.get('email', '')
            }
        
        if any(footer_info.values()):
            footer_html = '    <footer class="footer">\n'
            footer_html += '        <div class="footer-content">\n'
            
            if footer_info.get('company_name'):
                footer_html += f'            <p class="footer-company">{footer_info["company_name"]}</p>\n'
            
            if footer_info.get('ip_name'):
                footer_html += f'            <p class="footer-ip">ИП {footer_info["ip_name"]}</p>\n'
            
            footer_items = []
            if footer_info.get('unp'):
                footer_items.append(f'УНП: {footer_info["unp"]}')
            if footer_info.get('ogrn'):
                footer_items.append(f'ОГРН: {footer_info["ogrn"]}')
            if footer_info.get('inn'):
                footer_items.append(f'ИНН: {footer_info["inn"]}')
            
            if footer_items:
                footer_html += f'            <p class="footer-legal">{" | ".join(footer_items)}</p>\n'
            
            if footer_info.get('address'):
                footer_html += f'            <p class="footer-address">{footer_info["address"]}</p>\n'
            
            contact_items = []
            if footer_info.get('phone'):
                contact_items.append(f'Тел: {footer_info["phone"]}')
            if footer_info.get('email'):
                contact_items.append(f'Email: {footer_info["email"]}')
            
            if contact_items:
                footer_html += f'            <p class="footer-contact">{" | ".join(contact_items)}</p>\n'
            
            footer_html += '        </div>\n'
            footer_html += '    </footer>\n'
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Спасибо за заказ - {product_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="css/style.css">
    <style>
        .thank-you-section {{
            min-height: 60vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 3rem 1.5rem;
        }}
        
        .thank-you-icon {{
            width: 120px;
            height: 120px;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 2rem;
            font-size: 4rem;
            box-shadow: 0 20px 60px rgba(255, 107, 157, 0.4);
            animation: scaleIn 0.5s ease-out;
        }}
        
        @keyframes scaleIn {{
            from {{
                transform: scale(0);
                opacity: 0;
            }}
            to {{
                transform: scale(1);
                opacity: 1;
            }}
        }}
        
        .thank-you-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 2.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, #60a5fa 0%, var(--primary-color) 50%, var(--secondary-color) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }}
        
        .thank-you-text {{
            font-size: 1.2rem;
            color: var(--text-gray);
            line-height: 1.8;
            max-width: 600px;
            margin: 0 auto 2rem;
        }}
        
        .related-product-section {{
            margin-top: 3rem;
            padding: 2rem 1.5rem;
        }}
        
        .related-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-light);
            text-align: center;
            margin-bottom: 2rem;
        }}
        
        .related-product-card {{
            display: flex;
            flex-direction: column;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 1.5rem;
            border: 2px solid rgba(255, 255, 255, 0.1);
            text-decoration: none;
            color: inherit;
            transition: all 0.3s ease;
            max-width: 400px;
            margin: 0 auto;
        }}
        
        .related-product-card:hover {{
            transform: translateY(-5px);
            border-color: var(--primary-color);
            box-shadow: 0 20px 60px rgba(255, 107, 157, 0.3);
        }}
        
        .related-product-image-wrapper {{
            width: 100%;
            height: 250px;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 1rem;
        }}
        
        .related-product-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        
        .related-product-info {{
            text-align: center;
        }}
        
        .related-product-name {{
            font-family: 'Montserrat', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--text-light);
            margin-bottom: 0.5rem;
        }}
        
        .related-product-price {{
            font-size: 1.5rem;
            font-weight: 900;
            color: var(--primary-color);
            font-family: 'Montserrat', sans-serif;
        }}
        
        @media (max-width: 768px) {{
            .thank-you-icon {{
                width: 100px;
                height: 100px;
                font-size: 3rem;
            }}
            
            .thank-you-title {{
                font-size: 2rem;
            }}
            
            .thank-you-text {{
                font-size: 1.1rem;
            }}
            
            .related-title {{
                font-size: 1.6rem;
            }}
            
            .related-product-card {{
                padding: 1rem;
            }}
            
            .related-product-image-wrapper {{
                height: 200px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <section class="thank-you-section">
            <div class="thank-you-icon">✓</div>
            <h1 class="thank-you-title">Спасибо за заказ!</h1>
            <p class="thank-you-text">
                Ваш заказ на <strong>{product_name}</strong> успешно оформлен.<br>
                Наш менеджер свяжется с вами в ближайшее время для подтверждения заказа.
            </p>
        </section>
{related_html}    </div>
{footer_html}
    <script src="js/script.js"></script>
</body>
</html>'''
    
    def _create_base_css(self, design_style: str = 'vibrant') -> str:
        """
        Создание базового CSS с современными стилями
        
        Args:
            design_style: Стиль дизайна ('minimalist', 'luxury', 'vibrant')
            
        Returns:
            CSS код в зависимости от выбранного стиля
        """
        if design_style == 'minimalist':
            return self._create_minimalist_css()
        elif design_style == 'luxury':
            return self._create_luxury_css()
        else:  # vibrant (по умолчанию)
            return self._create_vibrant_css()
    
    def _create_base_css_with_colors(self, colors: Dict[str, str], fonts: tuple) -> str:
        """
        Создание CSS с указанными цветами и шрифтами
        
        Args:
            colors: Словарь с цветами (primary, secondary, accent, bg_dark, bg_darker)
            fonts: Кортеж из двух шрифтов (заголовки, основной текст)
        """
        font1, font2 = fonts
        font1_url = font1.replace(' ', '+')
        font2_url = font2.replace(' ', '+')
        
        return f'''@import url('https://fonts.googleapis.com/css2?family={font1_url}:wght@400;600;700;800;900&family={font2_url}:wght@300;400;500;600&display=swap');

:root {{
    --primary-color: {colors['primary']};
    --secondary-color: {colors['secondary']};
    --accent-color: {colors['accent']};
    --dark-bg: {colors['bg_dark']};
    --darker-bg: {colors['bg_darker']};
    --text-light: #ffffff;
    --text-gray: #d1d5db;
    --text-dark: #1f2937;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: '{font2}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    color: var(--text-light);
    background: linear-gradient(135deg, var(--darker-bg) 0%, var(--dark-bg) 50%, #1a1f3a 100%);
    min-height: 100vh;
    line-height: 1.6;
    overflow-x: hidden;
}}

.container {{
    max-width: 600px;
    margin: 0 auto;
    padding: 1rem;
}}

.hero-section {{
    display: flex;
    flex-direction: column;
    gap: 2rem;
    padding: 1.5rem 0;
    position: relative;
}}

.product-title {{
    font-family: '{font1}', sans-serif;
    font-size: 2.2rem;
    font-weight: 900;
    background: linear-gradient(135deg, #60a5fa 0%, var(--primary-color) 50%, var(--secondary-color) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    margin-bottom: 1rem;
    text-transform: uppercase;
    letter-spacing: -0.02em;
    text-align: center;
}}

.product-description {{
    font-size: 1.15rem;
    color: var(--text-gray);
    line-height: 1.8;
    margin-bottom: 1rem;
}}

.pricing-section {{
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 1rem;
    margin: 2rem 0;
}}

.old-price {{
    text-decoration: line-through;
    color: #6b7280;
    font-size: 1.5rem;
    font-weight: 400;
}}

.new-price {{
    color: var(--primary-color);
    font-size: 2.5rem;
    font-weight: 900;
    font-family: '{font1}', sans-serif;
    text-shadow: 0 0 20px rgba(255, 107, 157, 0.5);
}}

.timer {{
    font-size: 2.2rem;
    font-weight: 900;
    font-family: '{font1}', monospace;
    color: var(--primary-color);
    text-shadow: 0 0 20px rgba(255, 107, 157, 0.5);
    letter-spacing: 0.05em;
    text-align: center;
}}

.form-input {{
    padding: 1.2rem 1.5rem;
    background: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    font-size: 1.1rem;
    color: var(--text-light);
    font-family: '{font2}', sans-serif;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}}

.form-input:focus {{
    outline: none;
    border-color: var(--primary-color);
    background: rgba(255, 255, 255, 0.15);
    box-shadow: 0 0 20px rgba(255, 107, 157, 0.3);
}}

.btn-order {{
    padding: 1.4rem 2rem;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1.3rem;
    font-weight: 700;
    font-family: '{font1}', sans-serif;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 10px 30px rgba(255, 107, 157, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

.btn-order:hover {{
    transform: translateY(-2px);
    box-shadow: 0 15px 40px rgba(255, 107, 157, 0.6);
}}

.benefits-section {{
    margin-top: 3rem;
    padding: 2rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}}

.reviews-section {{
    margin-top: 3rem;
    padding: 2rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}}

.footer {{
    margin-top: 4rem;
    padding: 2rem 1.5rem;
    background: rgba(0, 0, 0, 0.3);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}}

@media (max-width: 768px) {{
    .product-title {{
        font-size: 1.8rem;
    }}
    
    .new-price {{
        font-size: 2rem;
    }}
    
    .timer {{
        font-size: 1.8rem;
    }}
}}
'''
    
    def _create_vibrant_css(self) -> str:
        """Создание яркого стиля CSS"""
        return '''@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&family=Inter:wght@300;400;500;600&display=swap');

:root {
    --primary-color: #ff6b9d;
    --secondary-color: #c084fc;
    --accent-color: #f97316;
    --dark-bg: #0a0e27;
    --darker-bg: #050715;
    --text-light: #ffffff;
    --text-gray: #d1d5db;
    --text-dark: #1f2937;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    color: var(--text-light);
    background: linear-gradient(135deg, var(--darker-bg) 0%, var(--dark-bg) 50%, #1a1f3a 100%);
    min-height: 100vh;
    line-height: 1.6;
    overflow-x: hidden;
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 1rem;
}

.hero-section {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    padding: 1.5rem 0;
    position: relative;
}

.product-visual {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
}

/* Карусель изображений */
.carousel-container {
    position: relative;
    width: 100%;
    margin-bottom: 2rem;
}

.carousel-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
    border-radius: 20px;
}

.carousel-track {
    display: flex;
    transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform;
}

.carousel-slide {
    min-width: 100%;
    flex-shrink: 0;
    display: flex;
    justify-content: center;
    align-items: center;
}

.product-image {
    width: 100%;
    max-width: 100%;
    max-height: 400px;
    height: auto;
    object-fit: cover;
    border-radius: 20px;
    box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6),
                0 0 40px rgba(255, 107, 157, 0.2);
    border: 3px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.05);
    padding: 0.5rem;
    display: block;
}

.carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    width: 50px;
    height: 50px;
    font-size: 2rem;
    color: white;
    cursor: pointer;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    user-select: none;
}

.carousel-btn:hover {
    background: rgba(255, 107, 157, 0.8);
    border-color: var(--primary-color);
    transform: translateY(-50%) scale(1.1);
}

.carousel-btn:active {
    transform: translateY(-50%) scale(0.95);
}

.carousel-btn-prev {
    left: 10px;
}

.carousel-btn-next {
    right: 10px;
}

.carousel-dots {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 1rem;
}

.carousel-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    cursor: pointer;
    transition: all 0.3s ease;
    border: none;
    padding: 0;
}

.carousel-dot.active {
    background: var(--primary-color);
    width: 30px;
    border-radius: 5px;
    box-shadow: 0 0 15px rgba(255, 107, 157, 0.5);
}

.product-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.product-title {
    font-family: 'Montserrat', sans-serif;
    font-size: 2.2rem;
    font-weight: 900;
    background: linear-gradient(135deg, #60a5fa 0%, var(--primary-color) 50%, var(--secondary-color) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    margin-bottom: 1rem;
    text-transform: uppercase;
    letter-spacing: -0.02em;
    text-align: center;
}

.product-description {
    font-size: 1.15rem;
    color: var(--text-gray);
    line-height: 1.8;
    margin-bottom: 1rem;
}

.pricing-section {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 1rem;
    margin: 2rem 0;
}

.prices {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    flex-wrap: wrap;
}

.old-price {
    text-decoration: line-through;
    color: #6b7280;
    font-size: 1.5rem;
    font-weight: 400;
}

.new-price {
    color: var(--primary-color);
    font-size: 2.5rem;
    font-weight: 900;
    font-family: 'Montserrat', sans-serif;
    text-shadow: 0 0 20px rgba(255, 107, 157, 0.5);
}

.countdown-section {
    margin: 2rem 0;
    text-align: center;
}

.countdown-label {
    font-size: 1.1rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
}

.timer {
    font-size: 2.2rem;
    font-weight: 900;
    font-family: 'Montserrat', monospace;
    color: var(--primary-color);
    text-shadow: 0 0 20px rgba(255, 107, 157, 0.5);
    letter-spacing: 0.05em;
    text-align: center;
}

.order-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 2rem;
}

.form-input {
    padding: 1.2rem 1.5rem;
    background: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    font-size: 1.1rem;
    color: var(--text-light);
    font-family: 'Inter', sans-serif;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}

.form-input::placeholder {
    color: rgba(255, 255, 255, 0.5);
}

.form-input:focus {
    outline: none;
    border-color: var(--primary-color);
    background: rgba(255, 255, 255, 0.15);
    box-shadow: 0 0 20px rgba(255, 107, 157, 0.3);
}

/* Стили для select элементов (размеры, характеристики) */
select.form-input {
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23ffffff' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 1.5rem center;
    padding-right: 3rem;
    cursor: pointer;
}

select.form-input option {
    background: var(--dark-bg);
    color: var(--text-light);
    padding: 0.5rem;
}

/* Стили для выбора цвета */
.color-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin: 0.5rem 0;
}

.color-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 1rem;
    color: var(--text-light);
}

.color-option:hover {
    background: rgba(255, 255, 255, 0.15);
    border-color: var(--primary-color);
    transform: translateY(-2px);
}

.color-option input[type="radio"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
    accent-color: var(--primary-color);
}

.color-option input[type="radio"]:checked + label,
.color-option:has(input[type="radio"]:checked) {
    background: rgba(255, 107, 157, 0.2);
    border-color: var(--primary-color);
    box-shadow: 0 0 15px rgba(255, 107, 157, 0.3);
}

/* Honeypot поле - скрытое для защиты от спама */
.honeypot-field {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
    visibility: hidden;
}

.btn-order {
    padding: 1.4rem 2rem;
    background: linear-gradient(135deg, var(--primary-color) 0%, #ec4899 100%);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1.3rem;
    font-weight: 700;
    font-family: 'Montserrat', sans-serif;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 10px 30px rgba(255, 107, 157, 0.4);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.btn-order:hover {
    transform: translateY(-2px);
    box-shadow: 0 15px 40px rgba(255, 107, 157, 0.6);
}

.btn-order:active {
    transform: translateY(0);
}

.benefits-section {
    margin-top: 3rem;
    padding: 2rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.benefits-title {
    font-family: 'Montserrat', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-light);
    margin-bottom: 1.5rem;
    text-align: center;
}

.benefits-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.benefits-list li {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    font-size: 1.1rem;
    color: var(--text-gray);
    transition: all 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.benefits-list li:hover {
    background: rgba(255, 255, 255, 0.1);
    transform: translateX(5px);
}

.check-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: white;
    border-radius: 50%;
    font-weight: bold;
    font-size: 1rem;
    flex-shrink: 0;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

/* Карусель отзывов */
.reviews-section {
    margin-top: 3rem;
    padding: 2rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.reviews-title {
    font-family: 'Montserrat', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-light);
    margin-bottom: 2rem;
    text-align: center;
}

.reviews-carousel-container {
    position: relative;
    width: 100%;
}

.reviews-carousel-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
}

.reviews-carousel-track {
    display: flex;
    transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: transform;
}

.review-slide {
    min-width: 100%;
    flex-shrink: 0;
    padding: 0 1rem;
}

.review-card {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 2rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
    min-height: 250px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.review-photo {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 1rem;
    border: 3px solid var(--primary-color);
    box-shadow: 0 0 20px rgba(255, 107, 157, 0.4);
}

.review-rating {
    color: #fbbf24;
    font-size: 1.5rem;
    margin-bottom: 1rem;
    letter-spacing: 0.2em;
}

.review-text {
    font-size: 1.1rem;
    color: var(--text-gray);
    line-height: 1.8;
    margin-bottom: 1.5rem;
    font-style: italic;
}

.review-author {
    font-size: 1rem;
    color: var(--text-light);
    font-weight: 600;
    font-family: 'Montserrat', sans-serif;
}

.reviews-carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    width: 45px;
    height: 45px;
    font-size: 1.8rem;
    color: white;
    cursor: pointer;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    user-select: none;
}

.reviews-carousel-btn:hover {
    background: rgba(255, 107, 157, 0.8);
    border-color: var(--primary-color);
    transform: translateY(-50%) scale(1.1);
}

.reviews-carousel-btn:active {
    transform: translateY(-50%) scale(0.95);
}

.reviews-carousel-btn-prev {
    left: -20px;
}

.reviews-carousel-btn-next {
    right: -20px;
}

@media (max-width: 768px) {
    .container {
        padding: 0.75rem;
    }
    
    .hero-section {
        padding: 1rem 0;
        gap: 1.5rem;
    }
    
    .product-title {
        font-size: 1.8rem;
    }
    
    .product-description {
        font-size: 1rem;
    }
    
    .new-price {
        font-size: 2rem;
    }
    
    .old-price {
        font-size: 1.2rem;
    }
    
    .timer {
        font-size: 1.8rem;
    }
    
    .countdown-label {
        font-size: 1rem;
    }
    
    .benefits-section {
        padding: 1.5rem 1rem;
        margin-top: 2rem;
    }
    
    .benefits-title {
        font-size: 1.6rem;
    }
    
    .benefits-list li {
        font-size: 1rem;
        padding: 0.75rem;
    }
    
    .product-image {
        max-height: 300px;
    }
    
    .carousel-btn {
        width: 40px;
        height: 40px;
        font-size: 1.5rem;
    }
    
    .carousel-btn-prev {
        left: 5px;
    }
    
    .carousel-btn-next {
        right: 5px;
    }
    
    .reviews-carousel-btn {
        width: 40px;
        height: 40px;
        font-size: 1.5rem;
    }
    
    .reviews-carousel-btn-prev {
        left: -15px;
    }
    
    .reviews-carousel-btn-next {
        right: -15px;
    }
    
    .review-card {
        padding: 1.5rem;
        min-height: 200px;
    }
    
    .review-text {
        font-size: 1rem;
    }
    
    .form-input {
        padding: 1rem;
        font-size: 1rem;
    }
    
    .btn-order {
        padding: 1.2rem 1.5rem;
        font-size: 1.1rem;
    }
    
    .footer {
        padding: 1.5rem 1rem;
        margin-top: 2rem;
    }
    
    .footer-company {
        font-size: 1rem;
    }
    
    .footer-ip,
    .footer-legal,
    .footer-address,
    .footer-contact {
        font-size: 0.85rem;
    }
}

/* Подвал */
.footer {
    margin-top: 4rem;
    padding: 2rem 1.5rem;
    background: rgba(0, 0, 0, 0.3);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}

.footer-content {
    max-width: 600px;
    margin: 0 auto;
}

.footer-company {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-light);
    margin-bottom: 0.5rem;
    font-family: 'Montserrat', sans-serif;
}

.footer-ip {
    font-size: 1rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
}

.footer-legal {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
    line-height: 1.6;
}

.footer-address {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
}

.footer-contact {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-top: 0.5rem;
}

@media (max-width: 480px) {
    .product-title {
        font-size: 1.5rem;
    }
    
    .new-price {
        font-size: 1.8rem;
    }
    
    .timer {
        font-size: 1.5rem;
    }
    
    .product-image.main-image {
        max-height: 250px;
    }
}'''
    
    def _create_minimalist_css(self) -> str:
        """Создание минималистичного стиля CSS"""
        return '''@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    --accent-color: #0ea5e9;
    --bg-color: #ffffff;
    --bg-secondary: #f8fafc;
    --text-color: #1e293b;
    --text-gray: #64748b;
    --border-color: #e2e8f0;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-color);
    background-color: var(--bg-color);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 1rem;
}

.hero-section {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    padding: 2rem 0;
}

.product-visual {
    position: relative;
    width: 100%;
}

.carousel-container {
    position: relative;
    width: 100%;
    margin-bottom: 2rem;
}

.carousel-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
    border-radius: 12px;
    border: 1px solid var(--border-color);
}

.carousel-track {
    display: flex;
    transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.carousel-slide {
    min-width: 100%;
    flex-shrink: 0;
    display: flex;
    justify-content: center;
    align-items: center;
}

.product-image {
    width: 100%;
    max-width: 100%;
    max-height: 400px;
    height: auto;
    object-fit: cover;
    border-radius: 12px;
    display: block;
}

.carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid var(--border-color);
    border-radius: 50%;
    width: 44px;
    height: 44px;
    font-size: 1.5rem;
    color: var(--text-color);
    cursor: pointer;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.carousel-btn:hover {
    background: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-50%) scale(1.05);
}

.carousel-btn-prev {
    left: 10px;
}

.carousel-btn-next {
    right: 10px;
}

.carousel-dots {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 1rem;
}

.carousel-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--border-color);
    cursor: pointer;
    transition: all 0.3s ease;
    border: none;
    padding: 0;
}

.carousel-dot.active {
    background: var(--primary-color);
    width: 24px;
    border-radius: 4px;
}

.product-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.product-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-color);
    line-height: 1.2;
    margin-bottom: 0.5rem;
    text-align: center;
    letter-spacing: -0.01em;
}

.product-description {
    font-size: 1rem;
    color: var(--text-gray);
    line-height: 1.7;
    margin-bottom: 1rem;
}

.pricing-section {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 1rem;
    margin: 1.5rem 0;
}

.prices {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    flex-wrap: wrap;
}

.old-price {
    text-decoration: line-through;
    color: var(--text-gray);
    font-size: 1.2rem;
    font-weight: 400;
}

.new-price {
    color: var(--primary-color);
    font-size: 2rem;
    font-weight: 700;
    font-family: 'Space Grotesk', sans-serif;
}

.countdown-section {
    margin: 1.5rem 0;
    text-align: center;
    padding: 1.5rem;
    background: var(--bg-secondary);
    border-radius: 12px;
}

.countdown-label {
    font-size: 0.95rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
}

.timer {
    font-size: 1.8rem;
    font-weight: 700;
    font-family: 'Space Grotesk', monospace;
    color: var(--primary-color);
    letter-spacing: 0.05em;
}

.order-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 1.5rem;
}

.form-input {
    padding: 1rem 1.25rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    font-size: 1rem;
    color: var(--text-color);
    font-family: 'Inter', sans-serif;
    transition: all 0.2s ease;
}

.form-input::placeholder {
    color: var(--text-gray);
}

.form-input:focus {
    outline: none;
    border-color: var(--primary-color);
    background: white;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Honeypot поле - скрытое для защиты от спама */
.honeypot-field {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
    visibility: hidden;
}

.btn-order {
    padding: 1.2rem 2rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1.1rem;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-order:hover {
    background: #1d4ed8;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.btn-order:active {
    transform: translateY(0);
}

.benefits-section {
    margin-top: 3rem;
    padding: 2rem 1.5rem;
    background: var(--bg-secondary);
    border-radius: 12px;
}

.benefits-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-color);
    margin-bottom: 1.5rem;
    text-align: center;
}

.benefits-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.benefits-list li {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: white;
    border-radius: 8px;
    font-size: 1rem;
    color: var(--text-color);
    transition: all 0.2s ease;
    border: 1px solid var(--border-color);
}

.benefits-list li:hover {
    border-color: var(--primary-color);
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
}

.check-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    background: var(--primary-color);
    color: white;
    border-radius: 50%;
    font-weight: 600;
    font-size: 0.875rem;
    flex-shrink: 0;
}

.reviews-section {
    margin-top: 3rem;
    padding: 2rem 1.5rem;
    background: var(--bg-secondary);
    border-radius: 12px;
}

.reviews-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-color);
    margin-bottom: 2rem;
    text-align: center;
}

.reviews-carousel-container {
    position: relative;
    width: 100%;
}

.reviews-carousel-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
}

.reviews-carousel-track {
    display: flex;
    transition: transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.review-slide {
    min-width: 100%;
    flex-shrink: 0;
    padding: 0 1rem;
}

.review-card {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    border: 1px solid var(--border-color);
    text-align: center;
    min-height: 250px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.review-photo {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 1rem;
    border: 2px solid var(--primary-color);
}

.review-rating {
    color: #fbbf24;
    font-size: 1.25rem;
    margin-bottom: 1rem;
    letter-spacing: 0.1em;
}

.review-text {
    font-size: 1rem;
    color: var(--text-gray);
    line-height: 1.7;
    margin-bottom: 1.5rem;
    font-style: italic;
}

.review-author {
    font-size: 0.95rem;
    color: var(--text-color);
    font-weight: 600;
    font-family: 'Space Grotesk', sans-serif;
}

.reviews-carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid var(--border-color);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    font-size: 1.5rem;
    color: var(--text-color);
    cursor: pointer;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.reviews-carousel-btn:hover {
    background: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateY(-50%) scale(1.05);
}

.reviews-carousel-btn-prev {
    left: -15px;
}

.reviews-carousel-btn-next {
    right: -15px;
}

.footer {
    margin-top: 4rem;
    padding: 2rem 1.5rem;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    text-align: center;
}

.footer-content {
    max-width: 600px;
    margin: 0 auto;
}

.footer-company {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-color);
    margin-bottom: 0.5rem;
    font-family: 'Space Grotesk', sans-serif;
}

.footer-ip {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
}

.footer-legal {
    font-size: 0.85rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
    line-height: 1.6;
}

.footer-address {
    font-size: 0.85rem;
    color: var(--text-gray);
    margin-bottom: 0.5rem;
}

.footer-contact {
    font-size: 0.85rem;
    color: var(--text-gray);
    margin-top: 0.5rem;
}

@media (max-width: 768px) {
    .container {
        padding: 0.75rem;
    }
    
    .hero-section {
        padding: 1rem 0;
        gap: 1.5rem;
    }
    
    .product-title {
        font-size: 1.75rem;
    }
    
    .product-description {
        font-size: 0.95rem;
    }
    
    .new-price {
        font-size: 1.75rem;
    }
    
    .old-price {
        font-size: 1.1rem;
    }
    
    .timer {
        font-size: 1.5rem;
    }
    
    .benefits-section {
        padding: 1.5rem 1rem;
        margin-top: 2rem;
    }
    
    .benefits-title {
        font-size: 1.5rem;
    }
    
    .benefits-list li {
        font-size: 0.95rem;
        padding: 0.75rem;
    }
    
    .product-image {
        max-height: 300px;
    }
    
    .carousel-btn {
        width: 40px;
        height: 40px;
        font-size: 1.25rem;
    }
    
    .carousel-btn-prev {
        left: 5px;
    }
    
    .carousel-btn-next {
        right: 5px;
    }
    
    .reviews-carousel-btn {
        width: 36px;
        height: 36px;
        font-size: 1.25rem;
    }
    
    .reviews-carousel-btn-prev {
        left: -12px;
    }
    
    .reviews-carousel-btn-next {
        right: -12px;
    }
    
    .review-card {
        padding: 1.5rem;
        min-height: 200px;
    }
    
    .review-text {
        font-size: 0.95rem;
    }
    
    .form-input {
        padding: 0.875rem 1rem;
        font-size: 0.95rem;
    }
    
    .btn-order {
        padding: 1rem 1.5rem;
        font-size: 1rem;
    }
    
    .footer {
        padding: 1.5rem 1rem;
        margin-top: 2rem;
    }
    
    .footer-company {
        font-size: 0.95rem;
    }
    
    .footer-ip,
    .footer-legal,
    .footer-address,
    .footer-contact {
        font-size: 0.8rem;
    }
}

@media (max-width: 480px) {
    .product-title {
        font-size: 1.5rem;
    }
    
    .new-price {
        font-size: 1.5rem;
    }
    
    .timer {
        font-size: 1.25rem;
    }
    
    .product-image {
        max-height: 250px;
    }
}'''
    
    def _create_luxury_css(self) -> str:
        """Создание люксового стиля CSS"""
        return '''@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;900&family=Cormorant+Garamond:wght@300;400;500;600;700&display=swap');

:root {
    --primary-color: #d4af37;
    --secondary-color: #8b7355;
    --accent-color: #c9a961;
    --dark-bg: #1a1a1a;
    --darker-bg: #0f0f0f;
    --text-light: #f5f5f5;
    --text-gray: #d4d4d4;
    --gold-glow: rgba(212, 175, 55, 0.3);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Cormorant Garamond', serif;
    color: var(--text-light);
    background: linear-gradient(180deg, var(--darker-bg) 0%, var(--dark-bg) 100%);
    min-height: 100vh;
    line-height: 1.7;
    overflow-x: hidden;
}

.container {
    max-width: 600px;
    margin: 0 auto;
    padding: 1rem;
}

.hero-section {
    display: flex;
    flex-direction: column;
    gap: 2.5rem;
    padding: 2rem 0;
    position: relative;
}

.product-visual {
    position: relative;
    width: 100%;
}

.carousel-container {
    position: relative;
    width: 100%;
    margin-bottom: 2rem;
}

.carousel-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
    border-radius: 8px;
    border: 2px solid var(--primary-color);
    box-shadow: 0 0 30px var(--gold-glow);
}

.carousel-track {
    display: flex;
    transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.carousel-slide {
    min-width: 100%;
    flex-shrink: 0;
    display: flex;
    justify-content: center;
    align-items: center;
}

.product-image {
    width: 100%;
    max-width: 100%;
    max-height: 400px;
    height: auto;
    object-fit: cover;
    border-radius: 6px;
    display: block;
}

.carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(26, 26, 26, 0.9);
    border: 2px solid var(--primary-color);
    border-radius: 50%;
    width: 50px;
    height: 50px;
    font-size: 1.75rem;
    color: var(--primary-color);
    cursor: pointer;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    box-shadow: 0 0 20px var(--gold-glow);
}

.carousel-btn:hover {
    background: var(--primary-color);
    color: var(--dark-bg);
    box-shadow: 0 0 30px var(--primary-color);
    transform: translateY(-50%) scale(1.1);
}

.carousel-btn-prev {
    left: 10px;
}

.carousel-btn-next {
    right: 10px;
}

.carousel-dots {
    display: flex;
    justify-content: center;
    gap: 0.75rem;
    margin-top: 1.5rem;
}

.carousel-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--secondary-color);
    cursor: pointer;
    transition: all 0.3s ease;
    border: 2px solid transparent;
    padding: 0;
}

.carousel-dot.active {
    background: var(--primary-color);
    width: 32px;
    border-radius: 6px;
    border-color: var(--primary-color);
    box-shadow: 0 0 15px var(--gold-glow);
}

.product-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.product-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--primary-color);
    line-height: 1.2;
    margin-bottom: 1rem;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-shadow: 0 0 20px var(--gold-glow);
}

.product-description {
    font-size: 1.15rem;
    color: var(--text-gray);
    line-height: 1.8;
    margin-bottom: 1rem;
    font-style: italic;
}

.pricing-section {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 1.5rem;
    margin: 2rem 0;
    padding: 1.5rem;
    background: rgba(212, 175, 55, 0.1);
    border-radius: 8px;
    border: 1px solid var(--primary-color);
}

.prices {
    display: flex;
    align-items: baseline;
    gap: 1.5rem;
    flex-wrap: wrap;
}

.old-price {
    text-decoration: line-through;
    color: var(--text-gray);
    font-size: 1.3rem;
    font-weight: 400;
    opacity: 0.6;
}

.new-price {
    color: var(--primary-color);
    font-size: 3rem;
    font-weight: 900;
    font-family: 'Playfair Display', serif;
    text-shadow: 0 0 25px var(--gold-glow);
    letter-spacing: 0.02em;
}

.countdown-section {
    margin: 2rem 0;
    text-align: center;
    padding: 2rem;
    background: rgba(212, 175, 55, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(212, 175, 55, 0.3);
}

.countdown-label {
    font-size: 1.1rem;
    color: var(--text-gray);
    margin-bottom: 1rem;
    font-style: italic;
}

.timer {
    font-size: 2.5rem;
    font-weight: 900;
    font-family: 'Playfair Display', serif;
    color: var(--primary-color);
    text-shadow: 0 0 25px var(--gold-glow);
    letter-spacing: 0.1em;
}

.order-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    margin-top: 2rem;
}

.form-input {
    padding: 1.25rem 1.5rem;
    background: rgba(26, 26, 26, 0.8);
    border: 2px solid var(--secondary-color);
    border-radius: 8px;
    font-size: 1.1rem;
    color: var(--text-light);
    font-family: 'Cormorant Garamond', serif;
    transition: all 0.3s ease;
}

.form-input::placeholder {
    color: var(--text-gray);
    font-style: italic;
}

.form-input:focus {
    outline: none;
    border-color: var(--primary-color);
    background: rgba(26, 26, 26, 0.95);
    box-shadow: 0 0 20px var(--gold-glow);
}

/* Honeypot поле - скрытое для защиты от спама */
.honeypot-field {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
    visibility: hidden;
}

.btn-order {
    padding: 1.5rem 2.5rem;
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
    color: var(--dark-bg);
    border: 2px solid var(--primary-color);
    border-radius: 8px;
    font-size: 1.25rem;
    font-weight: 700;
    font-family: 'Playfair Display', serif;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 0 30px var(--gold-glow);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.btn-order:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 40px var(--primary-color);
}

.btn-order:active {
    transform: translateY(0);
}

.benefits-section {
    margin-top: 4rem;
    padding: 3rem 2rem;
    background: rgba(26, 26, 26, 0.6);
    border-radius: 12px;
    border: 1px solid var(--secondary-color);
}

.benefits-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.25rem;
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 2rem;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-shadow: 0 0 15px var(--gold-glow);
}

.benefits-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.benefits-list li {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 1.25rem;
    background: rgba(26, 26, 26, 0.8);
    border-radius: 8px;
    font-size: 1.15rem;
    color: var(--text-light);
    transition: all 0.3s ease;
    border: 1px solid var(--secondary-color);
}

.benefits-list li:hover {
    border-color: var(--primary-color);
    box-shadow: 0 0 20px var(--gold-glow);
    transform: translateX(5px);
}

.check-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--primary-color);
    color: var(--dark-bg);
    border-radius: 50%;
    font-weight: 700;
    font-size: 1.1rem;
    flex-shrink: 0;
    box-shadow: 0 0 15px var(--gold-glow);
}

.reviews-section {
    margin-top: 4rem;
    padding: 3rem 2rem;
    background: rgba(26, 26, 26, 0.6);
    border-radius: 12px;
    border: 1px solid var(--secondary-color);
}

.reviews-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.25rem;
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 2rem;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-shadow: 0 0 15px var(--gold-glow);
}

.reviews-carousel-container {
    position: relative;
    width: 100%;
}

.reviews-carousel-wrapper {
    position: relative;
    width: 100%;
    overflow: hidden;
}

.reviews-carousel-track {
    display: flex;
    transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.review-slide {
    min-width: 100%;
    flex-shrink: 0;
    padding: 0 1rem;
}

.review-card {
    background: rgba(26, 26, 26, 0.9);
    border-radius: 12px;
    padding: 2.5rem;
    border: 2px solid var(--secondary-color);
    text-align: center;
    min-height: 280px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.review-photo {
    width: 90px;
    height: 90px;
    border-radius: 50%;
    object-fit: cover;
    margin-bottom: 1.25rem;
    border: 3px solid var(--primary-color);
    box-shadow: 0 0 20px var(--gold-glow);
}

.review-rating {
    color: var(--primary-color);
    font-size: 1.75rem;
    margin-bottom: 1.25rem;
    letter-spacing: 0.2em;
    text-shadow: 0 0 10px var(--gold-glow);
}

.review-text {
    font-size: 1.15rem;
    color: var(--text-gray);
    line-height: 1.8;
    margin-bottom: 1.5rem;
    font-style: italic;
}

.review-author {
    font-size: 1.1rem;
    color: var(--primary-color);
    font-weight: 600;
    font-family: 'Playfair Display', serif;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.reviews-carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(26, 26, 26, 0.9);
    border: 2px solid var(--primary-color);
    border-radius: 50%;
    width: 48px;
    height: 48px;
    font-size: 1.75rem;
    color: var(--primary-color);
    cursor: pointer;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    box-shadow: 0 0 20px var(--gold-glow);
}

.reviews-carousel-btn:hover {
    background: var(--primary-color);
    color: var(--dark-bg);
    box-shadow: 0 0 30px var(--primary-color);
    transform: translateY(-50%) scale(1.1);
}

.reviews-carousel-btn-prev {
    left: -20px;
}

.reviews-carousel-btn-next {
    right: -20px;
}

.footer {
    margin-top: 4rem;
    padding: 2.5rem 1.5rem;
    background: rgba(15, 15, 15, 0.8);
    border-top: 2px solid var(--secondary-color);
    text-align: center;
}

.footer-content {
    max-width: 600px;
    margin: 0 auto;
}

.footer-company {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--primary-color);
    margin-bottom: 0.75rem;
    font-family: 'Playfair Display', serif;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.footer-ip {
    font-size: 1rem;
    color: var(--text-gray);
    margin-bottom: 0.75rem;
    font-style: italic;
}

.footer-legal {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-bottom: 0.75rem;
    line-height: 1.7;
}

.footer-address {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-bottom: 0.75rem;
    font-style: italic;
}

.footer-contact {
    font-size: 0.9rem;
    color: var(--text-gray);
    margin-top: 0.75rem;
}

@media (max-width: 768px) {
    .container {
        padding: 0.75rem;
    }
    
    .hero-section {
        padding: 1.5rem 0;
        gap: 2rem;
    }
    
    .product-title {
        font-size: 2rem;
    }
    
    .product-description {
        font-size: 1.05rem;
    }
    
    .new-price {
        font-size: 2.25rem;
    }
    
    .old-price {
        font-size: 1.2rem;
    }
    
    .timer {
        font-size: 2rem;
    }
    
    .benefits-section {
        padding: 2rem 1.5rem;
        margin-top: 3rem;
    }
    
    .benefits-title {
        font-size: 1.75rem;
    }
    
    .benefits-list li {
        font-size: 1.05rem;
        padding: 1rem;
    }
    
    .product-image {
        max-height: 300px;
    }
    
    .carousel-btn {
        width: 44px;
        height: 44px;
        font-size: 1.5rem;
    }
    
    .carousel-btn-prev {
        left: 5px;
    }
    
    .carousel-btn-next {
        right: 5px;
    }
    
    .reviews-carousel-btn {
        width: 44px;
        height: 44px;
        font-size: 1.5rem;
    }
    
    .reviews-carousel-btn-prev {
        left: -15px;
    }
    
    .reviews-carousel-btn-next {
        right: -15px;
    }
    
    .review-card {
        padding: 2rem;
        min-height: 240px;
    }
    
    .review-text {
        font-size: 1.05rem;
    }
    
    .form-input {
        padding: 1.1rem 1.25rem;
        font-size: 1.05rem;
    }
    
    .btn-order {
        padding: 1.25rem 2rem;
        font-size: 1.15rem;
    }
    
    .footer {
        padding: 2rem 1rem;
        margin-top: 3rem;
    }
    
    .footer-company {
        font-size: 1.05rem;
    }
    
    .footer-ip,
    .footer-legal,
    .footer-address,
    .footer-contact {
        font-size: 0.85rem;
    }
}

@media (max-width: 480px) {
    .product-title {
        font-size: 1.75rem;
    }
    
    .new-price {
        font-size: 1.75rem;
    }
    
    .timer {
        font-size: 1.75rem;
    }
    
    .product-image {
        max-height: 250px;
    }
}'''
    
    def _create_base_js(self) -> str:
        """Создание базового JavaScript с таймером и форматированием телефона"""
        return r'''// Таймер обратного отсчета до конца дня
function startCountdown() {
    const timerElement = document.getElementById('timer');
    if (!timerElement) return;
    
    function updateTimer() {
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        
        const timeLeft = tomorrow - now;
        
        if (timeLeft <= 0) {
            timerElement.textContent = '00:00:00';
            return;
        }
        
        const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
        
        const h = String(hours).padStart(2, '0');
        const m = String(minutes).padStart(2, '0');
        const s = String(seconds).padStart(2, '0');
        
        timerElement.textContent = `${h}:${m}:${s}`;
        
        setTimeout(updateTimer, 1000);
    }
    
    updateTimer();
}

// Форматирование телефона
function formatPhone(input) {
    let value = input.value.replace(/\D/g, '');
    
    if (value.startsWith('375')) {
        value = value.substring(3);
    }
    
    let formatted = '+375 (';
    
    if (value.length > 0) {
        formatted += value.substring(0, 2);
    }
    if (value.length > 2) {
        formatted += ') ' + value.substring(2, 5);
    }
    if (value.length > 5) {
        formatted += '-' + value.substring(5, 7);
    }
    if (value.length > 7) {
        formatted += '-' + value.substring(7, 9);
    }
    
    input.value = formatted;
}

// Валидация формы
function validateForm(form) {
    const name = form.querySelector('input[name="name"]');
    const phone = form.querySelector('input[name="phone"]');
    
    if (!name.value.trim()) {
        alert('Пожалуйста, введите ваше имя');
        return false;
    }
    
    if (!phone.value.trim() || phone.value.length < 17) {
        alert('Пожалуйста, введите корректный номер телефона');
        return false;
    }
    
    return true;
}

// Карусель изображений
function initImageCarousel() {
    const carousel = document.getElementById('imageCarousel');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const dotsContainer = document.getElementById('carouselDots');
    
    if (!carousel) return;
    
    const slides = carousel.querySelectorAll('.carousel-slide');
    if (slides.length <= 1) {
        if (prevBtn) prevBtn.style.display = 'none';
        if (nextBtn) nextBtn.style.display = 'none';
        if (dotsContainer) dotsContainer.style.display = 'none';
        return;
    }
    
    let currentIndex = 0;
    let autoPlayInterval = null;
    
    // Создаем точки навигации
    if (dotsContainer) {
        slides.forEach((_, index) => {
            const dot = document.createElement('button');
            dot.className = 'carousel-dot' + (index === 0 ? ' active' : '');
            dot.setAttribute('aria-label', `Перейти к слайду ${index + 1}`);
            dot.addEventListener('click', () => goToSlide(index));
            dotsContainer.appendChild(dot);
        });
    }
    
    function updateCarousel() {
        carousel.style.transform = `translateX(-${currentIndex * 100}%)`;
        
        // Обновляем точки
        if (dotsContainer) {
            const dots = dotsContainer.querySelectorAll('.carousel-dot');
            dots.forEach((dot, index) => {
                dot.classList.toggle('active', index === currentIndex);
            });
        }
    }
    
    function goToSlide(index) {
        currentIndex = index;
        if (currentIndex < 0) currentIndex = slides.length - 1;
        if (currentIndex >= slides.length) currentIndex = 0;
        updateCarousel();
        resetAutoPlay();
    }
    
    function nextSlide() {
        goToSlide(currentIndex + 1);
    }
    
    function prevSlide() {
        goToSlide(currentIndex - 1);
    }
    
    function startAutoPlay() {
        autoPlayInterval = setInterval(nextSlide, 4000); // Автопрокрутка каждые 4 секунды
    }
    
    function stopAutoPlay() {
        if (autoPlayInterval) {
            clearInterval(autoPlayInterval);
            autoPlayInterval = null;
        }
    }
    
    function resetAutoPlay() {
        stopAutoPlay();
        startAutoPlay();
    }
    
    // Обработчики кнопок
    if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); stopAutoPlay(); });
    if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); stopAutoPlay(); });
    
    // Свайп для мобильных
    let touchStartX = 0;
    let touchEndX = 0;
    
    carousel.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        stopAutoPlay();
    });
    
    carousel.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
        startAutoPlay();
    });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                nextSlide();
            } else {
                prevSlide();
            }
        }
    }
    
    // Пауза при наведении
    const carouselContainer = carousel.closest('.carousel-container');
    if (carouselContainer) {
        carouselContainer.addEventListener('mouseenter', stopAutoPlay);
        carouselContainer.addEventListener('mouseleave', startAutoPlay);
    }
    
    // Инициализация
    updateCarousel();
    startAutoPlay();
}

// Карусель отзывов
function initReviewsCarousel() {
    const carousel = document.getElementById('reviewsCarousel');
    const prevBtn = document.getElementById('reviewsPrevBtn');
    const nextBtn = document.getElementById('reviewsNextBtn');
    
    if (!carousel) return;
    
    const slides = carousel.querySelectorAll('.review-slide');
    if (slides.length <= 1) {
        if (prevBtn) prevBtn.style.display = 'none';
        if (nextBtn) nextBtn.style.display = 'none';
        return;
    }
    
    let currentIndex = 0;
    let autoPlayInterval = null;
    
    function updateCarousel() {
        carousel.style.transform = `translateX(-${currentIndex * 100}%)`;
    }
    
    function goToSlide(index) {
        currentIndex = index;
        if (currentIndex < 0) currentIndex = slides.length - 1;
        if (currentIndex >= slides.length) currentIndex = 0;
        updateCarousel();
        resetAutoPlay();
    }
    
    function nextSlide() {
        goToSlide(currentIndex + 1);
    }
    
    function prevSlide() {
        goToSlide(currentIndex - 1);
    }
    
    function startAutoPlay() {
        autoPlayInterval = setInterval(nextSlide, 5000); // Автопрокрутка каждые 5 секунд
    }
    
    function stopAutoPlay() {
        if (autoPlayInterval) {
            clearInterval(autoPlayInterval);
            autoPlayInterval = null;
        }
    }
    
    function resetAutoPlay() {
        stopAutoPlay();
        startAutoPlay();
    }
    
    // Обработчики кнопок
    if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); stopAutoPlay(); });
    if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); stopAutoPlay(); });
    
    // Свайп для мобильных
    let touchStartX = 0;
    let touchEndX = 0;
    
    carousel.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        stopAutoPlay();
    });
    
    carousel.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
        startAutoPlay();
    });
    
    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                nextSlide();
            } else {
                prevSlide();
            }
        }
    }
    
    // Пауза при наведении
    const reviewsContainer = carousel.closest('.reviews-carousel-container');
    if (reviewsContainer) {
        reviewsContainer.addEventListener('mouseenter', stopAutoPlay);
        reviewsContainer.addEventListener('mouseleave', startAutoPlay);
    }
    
    // Инициализация
    updateCarousel();
    startAutoPlay();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    startCountdown();
    initImageCarousel();
    initReviewsCarousel();
    
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            formatPhone(this);
        });
        
        phoneInput.addEventListener('focus', function() {
            if (!this.value) {
                this.value = '+375 (';
            }
        });
    }
    
    // Защита от спама: отслеживание времени начала заполнения формы
    const orderForm = document.querySelector('.order-form');
    if (orderForm) {
        // Записываем время начала заполнения формы
        const formStartTime = Date.now();
        const formStartTimeInput = document.getElementById('formStartTime');
        if (formStartTimeInput) {
            formStartTimeInput.value = formStartTime.toString();
        }
        
        // Отслеживаем первое взаимодействие с формой
        let formInteracted = false;
        orderForm.addEventListener('focusin', function() {
            if (!formInteracted) {
                formInteracted = true;
                const startTimeInput = document.getElementById('formStartTime');
                if (startTimeInput && !startTimeInput.value) {
                    startTimeInput.value = Date.now().toString();
                }
            }
        }, true);
        
        orderForm.addEventListener('submit', function(e) {
            // Проверка honeypot поля
            const honeypotField = this.querySelector('.honeypot-field');
            if (honeypotField && honeypotField.value !== '') {
                e.preventDefault();
                console.warn('Spam detected: honeypot field filled');
                alert('Ошибка отправки формы. Пожалуйста, попробуйте еще раз.');
                return false;
            }
            
            // Проверка времени заполнения формы (минимум 3 секунды)
            const startTimeInput = document.getElementById('formStartTime');
            if (startTimeInput && startTimeInput.value) {
                const startTime = parseInt(startTimeInput.value);
                const currentTime = Date.now();
                const timeSpent = (currentTime - startTime) / 1000; // в секундах
                
                if (timeSpent < 3) {
                    e.preventDefault();
                    console.warn('Spam detected: form filled too quickly');
                    alert('Пожалуйста, заполните форму внимательнее. Это займет несколько секунд.');
                    return false;
                }
            }
            
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    }
});'''
    
    async def _copy_user_media(self, project_dir: str, user_data: Dict[str, Any]):
        """
        Копирование всех медиа файлов пользователя в папку проекта
        
        Args:
            project_dir: Директория проекта
            user_data: Данные пользователя с медиа файлами
        """
        from backend.utils.path_validator import get_safe_path
        
        img_dir = os.path.join(project_dir, 'img')
        os.makedirs(img_dir, exist_ok=True)
        
        copied_files = []  # Список скопированных файлов для логирования
        
        # Проверяем, используется ли новая структура
        is_new_structure = user_data.get('landing_type') is not None
        
        logger.info(f"Starting media copy to {img_dir}, new_structure={is_new_structure}")
        
        if is_new_structure:
            # Новая структура - копируем все медиа файлы
            # Hero медиа (фото или видео)
            hero_media = user_data.get('hero_media')
            if hero_media:
                if isinstance(hero_media, str) and os.path.exists(hero_media):
                    hero_ext = os.path.splitext(hero_media)[1] or '.jpg'
                    dest_path = get_safe_path(f'hero{hero_ext}', img_dir)
                    try:
                        shutil.copy2(hero_media, dest_path)
                        copied_files.append(f'hero{hero_ext}')
                        logger.info(f"✓ Copied hero media: {hero_media} -> {dest_path}")
                    except Exception as e:
                        logger.error(f"✗ Error copying hero media: {e}")
                else:
                    logger.warning(f"Hero media path does not exist: {hero_media}")
            
            # Среднее видео
            middle_video = user_data.get('middle_video')
            if middle_video:
                if isinstance(middle_video, str) and os.path.exists(middle_video):
                    video_ext = os.path.splitext(middle_video)[1] or '.mp4'
                    dest_path = get_safe_path(f'middle{video_ext}', img_dir)
                    try:
                        shutil.copy2(middle_video, dest_path)
                        copied_files.append(f'middle{video_ext}')
                        logger.info(f"✓ Copied middle video: {middle_video} -> {dest_path}")
                    except Exception as e:
                        logger.error(f"✗ Error copying middle video: {e}")
                else:
                    logger.warning(f"Middle video path does not exist: {middle_video}")
            
            # Галерея среднего блока
            middle_gallery = user_data.get('middle_gallery', [])
            if middle_gallery:
                for i, photo_item in enumerate(middle_gallery):
                    # Обрабатываем словари и строки
                    if isinstance(photo_item, dict):
                        photo_path = photo_item.get('path', '')
                    else:
                        photo_path = photo_item
                    
                    if isinstance(photo_path, str) and os.path.exists(photo_path):
                        photo_ext = os.path.splitext(photo_path)[1] or '.jpg'
                        dest_path = get_safe_path(f'gallery_{i+1}{photo_ext}', img_dir)
                        try:
                            shutil.copy2(photo_path, dest_path)
                            copied_files.append(f'gallery_{i+1}{photo_ext}')
                            logger.info(f"✓ Copied gallery photo {i+1}: {photo_path} -> {dest_path}")
                        except Exception as e:
                            logger.error(f"✗ Error copying gallery photo {i+1}: {e}")
                    else:
                        logger.warning(f"Gallery photo {i+1} path does not exist: {photo_path}")
            
            # Фото для описания
            description_photos = user_data.get('description_photos', [])
            if description_photos:
                for i, photo_item in enumerate(description_photos):
                    # Обрабатываем словари и строки
                    if isinstance(photo_item, dict):
                        photo_path = photo_item.get('path', '')
                    else:
                        photo_path = photo_item
                    
                    if isinstance(photo_path, str) and os.path.exists(photo_path):
                        photo_ext = os.path.splitext(photo_path)[1] or '.jpg'
                        dest_path = get_safe_path(f'description_{i+1}{photo_ext}', img_dir)
                        try:
                            shutil.copy2(photo_path, dest_path)
                            copied_files.append(f'description_{i+1}{photo_ext}')
                            logger.info(f"✓ Copied description photo {i+1}: {photo_path} -> {dest_path}")
                        except Exception as e:
                            logger.error(f"✗ Error copying description photo {i+1}: {e}")
                    else:
                        logger.warning(f"Description photo {i+1} path does not exist: {photo_path}")
            
            # Фото отзывов
            reviews = user_data.get('reviews', [])
            if reviews:
                for i, review in enumerate(reviews):
                    if isinstance(review, dict):
                        photo_path = review.get('photo') or review.get('photo_path')
                    else:
                        photo_path = None
                    
                    if photo_path and isinstance(photo_path, str) and os.path.exists(photo_path):
                        photo_ext = os.path.splitext(photo_path)[1] or '.jpg'
                        dest_path = get_safe_path(f'review_{i+1}{photo_ext}', img_dir)
                        try:
                            shutil.copy2(photo_path, dest_path)
                            copied_files.append(f'review_{i+1}{photo_ext}')
                            logger.info(f"✓ Copied review photo {i+1}: {photo_path} -> {dest_path}")
                        except Exception as e:
                            logger.error(f"✗ Error copying review photo {i+1}: {e}")
                    elif photo_path:
                        logger.warning(f"Review photo {i+1} path does not exist: {photo_path}")
        else:
            # Старая структура - копируем только photos
            photos = user_data.get('photos', [])
            if photos:
                for i, photo_path in enumerate(photos):
                    if isinstance(photo_path, str) and os.path.exists(photo_path):
                        photo_ext = os.path.splitext(photo_path)[1] or '.jpg'
                        dest_path = get_safe_path(f'photo_{i+1}{photo_ext}', img_dir)
                        try:
                            shutil.copy2(photo_path, dest_path)
                            copied_files.append(f'photo_{i+1}{photo_ext}')
                            logger.info(f"✓ Copied photo {i+1}: {photo_path} -> {dest_path}")
                        except Exception as e:
                            logger.error(f"✗ Error copying photo {i+1}: {e}")
                    else:
                        logger.warning(f"Photo {i+1} path does not exist: {photo_path}")
        
        # Итоговое логирование
        if copied_files:
            logger.info(f"✓ Successfully copied {len(copied_files)} media files to {img_dir}")
            logger.info(f"  Files: {', '.join(copied_files)}")
        else:
            logger.warning(f"⚠ No media files were copied to {img_dir}. Check user_data paths.")
