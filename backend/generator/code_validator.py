"""
Валидатор сгенерированного кода
"""
import re
from typing import Dict, List, Any

class CodeValidator:
    """Валидация HTML/CSS/JS кода"""
    
    def validate(self, code: Dict[str, str]) -> Dict[str, Any]:
        """
        Валидация всего кода
        
        Args:
            code: Словарь с html, css, js
            
        Returns:
            Результат валидации с ошибками
        """
        errors = []
        warnings = []
        
        html = code.get('html', '')
        css = code.get('css', '')
        js = code.get('js', '')
        
        # Валидация HTML
        html_errors, html_warnings = self._validate_html(html)
        errors.extend(html_errors)
        warnings.extend(html_warnings)
        
        # Валидация CSS
        css_errors, css_warnings = self._validate_css(css)
        errors.extend(css_errors)
        warnings.extend(css_warnings)
        
        # Валидация JS
        js_errors, js_warnings = self._validate_js(js)
        errors.extend(js_errors)
        warnings.extend(js_warnings)
        
        # Проверка наличия обязательных элементов
        required_errors, required_warnings = self._check_required_elements(html, css, js)
        errors.extend(required_errors)
        warnings.extend(required_warnings)
        
        # Проверка SEO
        seo_errors, seo_warnings = self._validate_seo(html)
        errors.extend(seo_errors)
        warnings.extend(seo_warnings)
        
        # Проверка Accessibility
        a11y_errors, a11y_warnings = self._validate_accessibility(html)
        errors.extend(a11y_errors)
        warnings.extend(a11y_warnings)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _validate_html(self, html: str) -> tuple[List[str], List[str]]:
        """
        Валидация HTML
        
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        if not html:
            errors.append("HTML код отсутствует")
            return errors, warnings
        
        # Проверка базовой структуры
        if '<!DOCTYPE html>' not in html and '<!doctype html>' not in html:
            warnings.append("Отсутствует DOCTYPE")
        
        if '<html' not in html:
            errors.append("Отсутствует тег <html>")
        
        if '<head' not in html:
            errors.append("Отсутствует тег <head>")
        
        if '<body' not in html:
            errors.append("Отсутствует тег <body>")
        
        # Проверка закрывающих тегов
        open_tags = len(re.findall(r'<(\w+)[^>]*>', html))
        close_tags = len(re.findall(r'</(\w+)>', html))
        if abs(open_tags - close_tags) > 5:  # Допускаем небольшую погрешность
            warnings.append(f"Возможно несоответствие открывающих и закрывающих тегов: {open_tags} открывающих, {close_tags} закрывающих")
        
        return errors, warnings
    
    def _validate_css(self, css: str) -> tuple[List[str], List[str]]:
        """
        Валидация CSS
        
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        if not css:
            warnings.append("CSS код отсутствует (может использоваться внешний файл)")
            return errors, warnings
        
        # Проверка базового синтаксиса
        open_braces = css.count('{')
        close_braces = css.count('}')
        if open_braces != close_braces:
            errors.append(f"Несоответствие фигурных скобок в CSS: {open_braces} открывающих, {close_braces} закрывающих")
        
        # Проверка наличия точек с запятой (базовая проверка)
        if len(css) > 100 and css.count(';') < css.count('{'):
            warnings.append("Возможно недостаточное количество точек с запятой в CSS")
        
        return errors, warnings
    
    def _validate_js(self, js: str) -> tuple[List[str], List[str]]:
        """
        Валидация JavaScript
        
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        if not js:
            warnings.append("JavaScript код отсутствует (может использоваться внешний файл)")
            return errors, warnings
        
        # Проверка базового синтаксиса
        open_braces = js.count('{')
        close_braces = js.count('}')
        if open_braces != close_braces:
            errors.append(f"Несоответствие фигурных скобок в JS: {open_braces} открывающих, {close_braces} закрывающих")
        
        open_parens = js.count('(')
        close_parens = js.count(')')
        if open_parens != close_parens:
            errors.append(f"Несоответствие скобок в JS: {open_parens} открывающих, {close_parens} закрывающих")
        
        return errors, warnings
    
    def _check_required_elements(self, html: str, css: str, js: str) -> tuple[List[str], List[str]]:
        """
        Проверка наличия обязательных элементов
        
        Returns:
            (errors, warnings) - кортеж со списками ошибок и предупреждений
        """
        errors = []
        warnings = []
        
        # Проверка минимальных размеров
        if len(html) < 200:
            errors.append(f"HTML код слишком короткий ({len(html)} символов, минимум 200)")
        
        if len(css) < 100:
            errors.append(f"CSS код слишком короткий ({len(css)} символов, минимум 100)")
        
        if len(js) < 50:
            errors.append(f"JavaScript код слишком короткий ({len(js)} символов, минимум 50)")
        
        # Проверка базовой HTML-структуры
        if '<!DOCTYPE html>' not in html and '<!doctype html>' not in html:
            errors.append("Отсутствует <!DOCTYPE html>")
        
        if '</html>' not in html:
            errors.append("Отсутствует закрывающий тег </html>")
        
        if '</body>' not in html:
            errors.append("Отсутствует закрывающий тег </body>")
        
        # Проверка подключения CSS и JS
        if 'link' not in html.lower() and 'stylesheet' not in html.lower():
            warnings.append("Возможно отсутствует подключение CSS файла")
        
        if 'script.js' not in html and 'pillow.js' not in html:
            warnings.append("Возможно отсутствует подключение JavaScript файла")
        
        # Проверка форм
        if 'action="send.php"' not in html and "action='send.php'" not in html:
            errors.append("Отсутствует форма с action='send.php'")
        
        # Проверка полей формы
        if '<input' not in html or 'name="name"' not in html:
            errors.append("Отсутствует поле имени в форме")
        
        if 'name="phone"' not in html:
            errors.append("Отсутствует поле телефона в форме")
        
        # Проверка таймера (должен быть в JS)
        if 'countdown' not in js.lower() and 'timer' not in js.lower():
            errors.append("Отсутствует таймер обратного отсчета в JavaScript")
        
        # Проверка TikTok Pixel
        if 'TikTok Pixel' not in html and 'ttq' not in html:
            warnings.append("TikTok Pixel не найден (будет добавлен автоматически)")
        
        return errors, warnings
    
    def _check_user_data(self, html: str, user_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """
        Проверка наличия данных пользователя в коде
        
        Args:
            html: HTML код
            user_data: Данные пользователя
            
        Returns:
            (errors, warnings) - кортеж со списками ошибок и предупреждений
        """
        errors = []
        warnings = []
        
        # Преобразуем значения в строки для безопасной обработки
        product_name = str(user_data.get('product_name', '')).strip()
        new_price_raw = user_data.get('new_price', '')
        new_price = str(new_price_raw).strip() if new_price_raw is not None else ''
        
        if product_name:
            # Удаляем валюту и лишние символы для проверки
            name_clean = product_name.lower().replace(' ', '')
            html_clean = html.lower().replace(' ', '').replace('\n', '')
            
            if len(name_clean) > 3 and name_clean not in html_clean[:len(html_clean)//2]:
                # Проверяем хотя бы часть названия
                name_parts = name_clean[:min(10, len(name_clean))]
                if name_parts not in html_clean[:len(html_clean)//2]:
                    errors.append(f"Название товара '{product_name}' не найдено в HTML коде")
        
        if new_price:
            # Извлекаем число из цены
            import re
            price_match = re.search(r'\d+', new_price)
            if price_match:
                price_num = price_match.group()
                if price_num not in html:
                    warnings.append(f"Цена '{new_price}' не найдена в HTML коде")
        
        return errors, warnings
    
    def _validate_seo(self, html: str) -> tuple[List[str], List[str]]:
        """
        Валидация SEO элементов
        
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        html_lower = html.lower()
        
        # Проверка title
        if '<title>' not in html_lower:
            errors.append("Отсутствует тег <title> (важно для SEO)")
        else:
            # Проверка длины title (рекомендуется 50-60 символов)
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if title_match:
                title_text = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
                if len(title_text) < 10:
                    warnings.append(f"Title слишком короткий ({len(title_text)} символов, рекомендуется 50-60)")
                elif len(title_text) > 70:
                    warnings.append(f"Title слишком длинный ({len(title_text)} символов, рекомендуется 50-60)")
        
        # Проверка meta description
        if 'meta name="description"' not in html_lower and "meta name='description'" not in html_lower:
            warnings.append("Отсутствует meta description (важно для SEO)")
        else:
            desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if desc_match:
                desc_text = desc_match.group(1)
                if len(desc_text) < 50:
                    warnings.append(f"Meta description слишком короткая ({len(desc_text)} символов, рекомендуется 150-160)")
                elif len(desc_text) > 170:
                    warnings.append(f"Meta description слишком длинная ({len(desc_text)} символов, рекомендуется 150-160)")
        
        # Проверка alt текстов для изображений
        img_tags = re.findall(r'<img[^>]+>', html, re.IGNORECASE)
        images_without_alt = []
        for img_tag in img_tags:
            if 'alt=' not in img_tag.lower():
                images_without_alt.append(img_tag[:50])
        
        if images_without_alt:
            warnings.append(f"Найдено {len(images_without_alt)} изображений без alt текста (важно для SEO и accessibility)")
        
        # Проверка заголовков (h1, h2, h3)
        h1_count = len(re.findall(r'<h1[^>]*>', html, re.IGNORECASE))
        if h1_count == 0:
            warnings.append("Отсутствует заголовок H1 (важно для SEO)")
        elif h1_count > 1:
            warnings.append(f"Найдено {h1_count} заголовков H1 (рекомендуется один)")
        
        h2_count = len(re.findall(r'<h2[^>]*>', html, re.IGNORECASE))
        if h2_count == 0:
            warnings.append("Отсутствуют заголовки H2 (важно для структуры и SEO)")
        
        # Проверка lang атрибута
        if 'lang=' not in html.lower() and "lang=" not in html.lower():
            warnings.append("Отсутствует атрибут lang в теге <html> (важно для SEO)")
        
        return errors, warnings
    
    def _validate_accessibility(self, html: str) -> tuple[List[str], List[str]]:
        """
        Валидация accessibility (доступности)
        
        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []
        
        html_lower = html.lower()
        
        # Проверка alt текстов для изображений (критично для accessibility)
        img_tags = re.findall(r'<img[^>]+>', html, re.IGNORECASE)
        images_without_alt = []
        
        for img_tag in img_tags:
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
            if not alt_match:
                images_without_alt.append(img_tag[:50])
        
        if images_without_alt:
            errors.append(f"Найдено {len(images_without_alt)} изображений без alt атрибута (критично для accessibility)")
        
        # Проверка aria-labels для интерактивных элементов
        buttons = re.findall(r'<button[^>]*>', html, re.IGNORECASE)
        buttons_without_label = []
        for button in buttons:
            has_aria_label = 'aria-label=' in button.lower()
            has_text = re.search(r'<button[^>]*>([^<]+)</button>', button, re.IGNORECASE)
            if not has_aria_label and not has_text:
                buttons_without_label.append(button[:50])
        
        if buttons_without_label:
            warnings.append(f"Найдено {len(buttons_without_label)} кнопок без текста или aria-label")
        
        # Проверка форм на labels
        inputs = re.findall(r'<input[^>]+>', html, re.IGNORECASE)
        inputs_without_label = []
        for input_tag in inputs:
            input_id = re.search(r'id=["\']([^"\']+)["\']', input_tag, re.IGNORECASE)
            if input_id:
                input_id_value = input_id.group(1)
                # Проверяем наличие label с for атрибутом
                label_pattern = rf'<label[^>]*for=["\']{re.escape(input_id_value)}["\']'
                if not re.search(label_pattern, html, re.IGNORECASE):
                    inputs_without_label.append(input_tag[:50])
        
        if inputs_without_label:
            warnings.append(f"Найдено {len(inputs_without_label)} полей ввода без связанного label")
        
        # Проверка семантических тегов
        semantic_tags = ['header', 'nav', 'main', 'article', 'section', 'aside', 'footer']
        found_semantic = []
        for tag in semantic_tags:
            if f'<{tag}' in html_lower:
                found_semantic.append(tag)
        
        if len(found_semantic) < 2:
            warnings.append("Мало семантических HTML5 тегов (header, nav, main, section, footer) - улучшает accessibility")
        
        return errors, warnings
