"""
Логика выбора шаблона лендинга для чат-бота
Версия: 1.0
Python 3.7+
"""

import json
from typing import Dict, List, Optional, Any, Tuple


class TemplateSelector:
    """Класс для выбора подходящего шаблона лендинга"""
    
    def __init__(self, templates_path_or_data, logic_path_or_data):
        """
        Инициализация селектора
        
        Args:
            templates_path_or_data: Путь к файлу landing-templates.json или dict
            logic_path_or_data: Путь к файлу template-selection-logic.json или dict
        """
        if isinstance(templates_path_or_data, dict):
            self.templates = templates_path_or_data
        else:
            with open(templates_path_or_data, 'r', encoding='utf-8') as f:
                self.templates = json.load(f)
        
        if isinstance(logic_path_or_data, dict):
            self.logic = logic_path_or_data
        else:
            with open(logic_path_or_data, 'r', encoding='utf-8') as f:
                self.logic = json.load(f)
        
        self.user_data = {}
        self.current_step = 'step_1_product_type'
    
    def set_answer(self, question_id: str, answer: Any) -> Dict:
        """
        Задать ответ пользователя на вопрос
        
        Args:
            question_id: ID вопроса
            answer: Ответ пользователя
            
        Returns:
            Следующий вопрос или результат выбора шаблона
        """
        self.user_data[question_id] = answer
        return self.get_next_question()
    
    def get_next_question(self) -> Dict:
        """
        Получить следующий вопрос из decision tree
        
        Returns:
            Словарь с вопросом и вариантами ответов
        """
        step_key = self.current_step
        step = self.logic['decision_tree'].get(step_key)
        
        if not step:
            # Дошли до конца, выбираем шаблон
            return self.select_template()
        
        # Проверяем наличие условий
        if 'condition' in step:
            return self._handle_condition(step['condition'])
        
        # Обычный вопрос
        return {
            'type': 'question',
            'question': step['question'],
            'options': step['options'],
            'step_id': self.current_step
        }
    
    def _handle_condition(self, condition: Dict) -> Dict:
        """
        Обработка условных переходов в decision tree
        
        Args:
            condition: Условие из decision tree
            
        Returns:
            Вопрос для следующего шага
        """
        # Обработка if
        if 'if' in condition and self._evaluate_condition(condition['if']):
            then_block = condition['then']
            if 'next_step' in then_block:
                self.current_step = then_block['next_step']
            
            if 'template_suggestion' in then_block:
                self.user_data['suggested_template'] = then_block['template_suggestion']
            
            return {
                'type': 'question',
                'question': then_block['question'],
                'options': then_block['options'],
                'step_id': self.current_step
            }
        
        # Обработка elif
        if 'elif' in condition:
            for condition_str, then_block in condition['elif'].items():
                if self._evaluate_condition(condition_str):
                    if 'next_step' in then_block:
                        self.current_step = then_block['next_step']
                    
                    if 'template_suggestion' in then_block:
                        self.user_data['suggested_template'] = then_block['template_suggestion']
                    
                    return {
                        'type': 'question',
                        'question': then_block['question'],
                        'options': then_block['options'],
                        'step_id': self.current_step
                    }
        
        # Если ни одно условие не подошло
        return self.get_next_question()
    
    def _evaluate_condition(self, condition_string: str) -> bool:
        """
        Вычисление условия вида "step_1_product_type == 'physical_product'"
        
        Args:
            condition_string: Строка условия
            
        Returns:
            True если условие выполнено
        """
        import re
        match = re.match(r"(\w+)\s*==\s*['\"]([^'\"]+)['\"]", condition_string)
        if match:
            key = match.group(1)
            expected_value = match.group(2)
            actual_value = self.user_data.get(key)
            return actual_value == expected_value
        return False
    
    def select_template(self) -> Dict:
        """
        Выбор финального шаблона на основе всех ответов
        
        Returns:
            Словарь с выбранным шаблоном и обоснованием
        """
        special_scenarios = self.user_data.get('step_4_special_scenarios', [])
        
        # Проверка B2B (высший приоритет)
        if 'b2b' in special_scenarios:
            return {
                'type': 'template',
                'template': 'b2b',
                'reason': 'B2B продажи требуют специального шаблона',
                'priority': 'highest'
            }
        
        # Проверка предзаказа (высокий приоритет)
        if 'pre_order' in special_scenarios:
            return {
                'type': 'template',
                'template': 'pre_order',
                'reason': 'Предзаказ требует специального шаблона',
                'priority': 'high'
            }
        
        # Проверка ограниченного предложения
        if 'limited_offer' in special_scenarios:
            base_template = self._get_base_template()
            if base_template:
                return {
                    'type': 'template',
                    'template': 'limited_offer',
                    'base_template': base_template,
                    'reason': 'Ограниченное предложение с элементами срочности',
                    'priority': 'high'
                }
        
        # Использование предложенного шаблона из шага 2
        if 'suggested_template' in self.user_data:
            return {
                'type': 'template',
                'template': self.user_data['suggested_template'],
                'reason': 'Шаблон определен по типу товара',
                'priority': 'medium'
            }
        
        # Применение правил выбора
        return self._apply_selection_rules()
    
    def _apply_selection_rules(self) -> Dict:
        """
        Применение правил выбора шаблона
        
        Returns:
            Выбранный шаблон с обоснованием
        """
        rules = self.logic['decision_tree']['template_selection']['rules']
        
        # Сортируем по приоритету (1 - выше)
        sorted_rules = sorted(rules, key=lambda x: x.get('priority', 999))
        
        for rule in sorted_rules:
            if self._match_rule(rule['conditions']):
                return {
                    'type': 'template',
                    'template': rule['template'],
                    'reason': rule['reason'],
                    'override': rule.get('override', False),
                    'priority': rule.get('priority', 'medium')
                }
        
        # Базовый шаблон по умолчанию
        base_template = self._get_base_template()
        return {
            'type': 'template',
            'template': base_template or 'physical_single',
            'reason': 'Использован базовый шаблон по умолчанию',
            'priority': 'low'
        }
    
    def _match_rule(self, conditions: Dict) -> bool:
        """
        Проверка соответствия условиям правила
        
        Args:
            conditions: Условия правила
            
        Returns:
            True если условия выполнены
        """
        for key, condition_value in conditions.items():
            # Определяем ключ в user_data
            user_key = None
            if key == 'product_type':
                user_key = 'step_1_product_type'
            elif key == 'business_model':
                user_key = 'step_2_business_model'
            elif key == 'price_range':
                user_key = 'step_3_price_range'
            elif key == 'special_scenarios':
                user_key = 'step_4_special_scenarios'
            else:
                user_key = key
            
            user_value = self.user_data.get(user_key)
            
            if isinstance(condition_value, list):
                # Если условие - список, проверяем вхождение
                if key == 'special_scenarios':
                    special_scenarios = self.user_data.get('step_4_special_scenarios', [])
                    if len(condition_value) == 0 and len(special_scenarios) == 0:
                        continue  # Пустые массивы = совпадение
                    if len(condition_value) > 0:
                        if not any(sc in special_scenarios for sc in condition_value):
                            return False
                else:
                    if user_value not in condition_value:
                        return False
            else:
                if condition_value != user_value:
                    return False
        
        return True
    
    def _get_base_template(self) -> Optional[str]:
        """
        Получение базового шаблона без особых сценариев
        
        Returns:
            ID базового шаблона или None
        """
        product_type = self.user_data.get('step_1_product_type')
        business_model = self.user_data.get('step_2_business_model')
        price_range = self.user_data.get('step_3_price_range')
        
        if product_type == 'physical_product':
            if business_model == 'variants':
                return 'physical_multi'
            elif business_model == 'dropshipping':
                return 'physical_dropshipping'
            elif price_range == 'low':
                return 'low_price_impulse'
            elif price_range == 'medium':
                return 'medium_price_justified'
            elif price_range == 'high':
                return 'high_price_detailed'
            else:
                return 'physical_single'
        
        if product_type == 'service':
            return 'service_consultation'
        
        if product_type == 'digital_product':
            return 'digital_course'
        
        return 'physical_single'
    
    def quick_select(self, text: str) -> Optional[Dict]:
        """
        Быстрый выбор шаблона по ключевым словам в тексте
        
        Args:
            text: Текст пользователя
            
        Returns:
            Результат выбора или None
        """
        keywords = self.logic['quick_selection']['keywords']
        lower_text = text.lower()
        
        for template, template_keywords in keywords.items():
            if any(keyword in lower_text for keyword in template_keywords):
                return {
                    'type': 'template',
                    'template': template,
                    'reason': f'Найдено соответствие по ключевым словам',
                    'confidence': 'medium'
                }
        
        return None
    
    def get_template_info(self, template_id: str) -> Optional[Dict]:
        """
        Получить информацию о шаблоне
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Информация о шаблоне или None
        """
        return self.templates['templates'].get(template_id)
    
    def check_compatibility(self, base_template: str, special_scenarios: List[str]) -> Dict:
        """
        Проверить совместимость шаблона с особыми сценариями
        
        Args:
            base_template: Базовый шаблон
            special_scenarios: Список особых сценариев
            
        Returns:
            Результат проверки совместимости
        """
        matrix = self.logic['compatibility_matrix']['matrix']
        base_info = matrix.get(base_template)
        
        if not base_info:
            return {'compatible': True, 'warnings': []}
        
        warnings = []
        incompatible = base_info.get('not_compatible_with', [])
        
        for scenario in special_scenarios:
            if scenario in incompatible:
                warnings.append(f'Шаблон {base_template} несовместим с {scenario}')
        
        return {
            'compatible': len(warnings) == 0,
            'warnings': warnings
        }
    
    def get_recommended_modifications(self, template_id: str, special_scenarios: List[str]) -> List[Dict]:
        """
        Получить рекомендуемые модификации для шаблона
        
        Args:
            template_id: ID шаблона
            special_scenarios: Список особых сценариев
            
        Returns:
            Список рекомендуемых модификаций
        """
        modifications = []
        
        if 'seasonal' in special_scenarios:
            modifications.append({
                'type': 'design',
                'description': 'Использовать сезонную цветовую схему',
                'items': ['color_scheme', 'seasonal_imagery', 'lifestyle_photos']
            })
        
        if 'limited_offer' in special_scenarios:
            modifications.append({
                'type': 'urgency',
                'description': 'Добавить элементы срочности',
                'items': ['countdown_timer', 'stock_counter', 'purchase_counter']
            })
        
        return modifications
    
    def reset(self):
        """Сброс состояния для нового выбора"""
        self.user_data = {}
        self.current_step = 'step_1_product_type'


# Пример использования
if __name__ == '__main__':
    # Инициализация
    selector = TemplateSelector(
        'landing-templates.json',
        'template-selection-logic.json'
    )
    
    # Пример 1: Пошаговый выбор
    print('=== Пошаговый выбор ===')
    result = selector.get_next_question()
    print(f'Вопрос 1: {result["question"]}')
    
    selector.set_answer('step_1_product_type', 'physical_product')
    result = selector.get_next_question()
    print(f'Вопрос 2: {result["question"]}')
    
    selector.set_answer('step_2_business_model', 'single_item')
    result = selector.get_next_question()
    print(f'Вопрос 3: {result["question"]}')
    
    selector.set_answer('step_3_price_range', 'low')
    result = selector.get_next_question()
    print(f'Вопрос 4: {result["question"]}')
    
    selector.set_answer('step_4_special_scenarios', [])
    result = selector.select_template()
    print(f'\nВыбранный шаблон: {result["template"]}')
    print(f'Обоснование: {result["reason"]}')
    
    # Пример 2: Быстрый выбор
    print('\n=== Быстрый выбор ===')
    selector.reset()
    quick_result = selector.quick_select('Хочу создать лендинг для подушки со скидкой 50%')
    if quick_result:
        print(f'Результат: {quick_result["template"]}')
        print(f'Уверенность: {quick_result["confidence"]}')
