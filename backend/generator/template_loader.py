"""
Загрузчик шаблонов
"""
import json
import os
from typing import Dict, Any, Optional

class TemplateLoader:
    """Класс для загрузки и работы с шаблонами"""
    
    def __init__(self, templates_path: str = 'landing-templates.json'):
        """
        Инициализация загрузчика
        
        Args:
            templates_path: Путь к файлу с шаблонами
        """
        self.templates_path = templates_path
        self.templates = None
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка шаблонов из файла"""
        try:
            if os.path.exists(self.templates_path):
                with open(self.templates_path, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)
            else:
                raise FileNotFoundError(f"Файл {self.templates_path} не найден")
        except Exception as e:
            raise Exception(f"Ошибка загрузки шаблонов: {str(e)}")
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить шаблон по ID
        
        Args:
            template_id: ID шаблона
            
        Returns:
            Информация о шаблоне или None
        """
        if not self.templates:
            return None
        
        return self.templates.get('templates', {}).get(template_id)
    
    def get_all_templates(self) -> Dict[str, Any]:
        """
        Получить все шаблоны
        
        Returns:
            Словарь со всеми шаблонами
        """
        return self.templates.get('templates', {}) if self.templates else {}
    
    def get_template_list(self) -> list:
        """
        Получить список всех шаблонов с базовой информацией
        
        Returns:
            Список шаблонов
        """
        templates = self.get_all_templates()
        return [
            {
                'id': template_id,
                'name': template.get('name', ''),
                'description': template.get('description', ''),
                'use_case': template.get('use_case', '')
            }
            for template_id, template in templates.items()
        ]
