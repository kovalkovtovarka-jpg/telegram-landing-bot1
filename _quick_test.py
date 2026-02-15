# -*- coding: utf-8 -*-
from template_selector import TemplateSelector

MIN_TEMPLATES = {"templates": {"physical_single": {"name": "One"}, "b2b": {"name": "B2B"}, "service_consultation": {"name": "Service"}}}
MIN_LOGIC = {
    "decision_tree": {},
    "quick_selection": {"keywords": {"physical_single": ["подушка", "товар"]}},
    "compatibility_matrix": {"matrix": {}},
}
sel = TemplateSelector(MIN_TEMPLATES, MIN_LOGIC)
t = "Хочу лендинг для подушки"
print("lower:", repr(t.lower()))
print("подушка in lower?", "подушка" in t.lower())
result = sel.quick_select(t)
print("result:", result)
