/**
 * Логика выбора шаблона лендинга для чат-бота
 * Версия: 1.0
 */

class TemplateSelector {
  constructor(templates, selectionLogic) {
    this.templates = templates;
    this.logic = selectionLogic;
    this.userData = {};
    this.currentStep = 'step_1_product_type';
  }

  /**
   * Задать ответ пользователя на текущий вопрос
   */
  setAnswer(questionId, answer) {
    this.userData[questionId] = answer;
    return this.getNextQuestion();
  }

  /**
   * Получить следующий вопрос
   */
  getNextQuestion() {
    const step = this.logic.decision_tree[this.currentStep];
    
    if (!step) {
      return this.selectTemplate();
    }

    // Если есть условие, проверяем его
    if (step.condition) {
      return this.handleCondition(step.condition);
    }

    return {
      type: 'question',
      question: step.question,
      options: step.options,
      stepId: this.currentStep
    };
  }

  /**
   * Обработка условий в decision tree
   */
  handleCondition(condition) {
    // Проверяем условие if
    if (this.evaluateCondition(condition.if)) {
      this.currentStep = condition.then.next_step || this.currentStep;
      // Если есть предложение шаблона, сохраняем его
      if (condition.then.template_suggestion) {
        this.userData.suggested_template = condition.then.template_suggestion;
      }
      return {
        type: 'question',
        question: condition.then.question,
        options: condition.then.options,
        stepId: this.currentStep
      };
    }

    // Проверяем elif условия
    if (condition.elif) {
      const elifKeys = Object.keys(condition.elif);
      for (const key of elifKeys) {
        if (this.evaluateCondition(key)) {
          const elifThen = condition.elif[key];
          this.currentStep = elifThen.next_step || this.currentStep;
          if (elifThen.template_suggestion) {
            this.userData.suggested_template = elifThen.template_suggestion;
          }
          return {
            type: 'question',
            question: elifThen.question,
            options: elifThen.options,
            stepId: this.currentStep
          };
        }
      }
    }

    // Если ни одно условие не выполнено, переходим к следующему шагу
    this.currentStep = step.next_step;
    return this.getNextQuestion();
  }

  /**
   * Вычисление условия
   */
  evaluateCondition(conditionString) {
    // Парсинг условий вида "step_1_product_type == 'physical_product'"
    const match = conditionString.match(/(\w+)\s*==\s*['"]([^'"]+)['"]/);
    if (match) {
      const key = match[1];
      const value = match[2];
      return this.userData[key] === value;
    }
    return false;
  }

  /**
   * Выбор финального шаблона на основе ответов
   */
  selectTemplate() {
    // Если есть специальные сценарии с высоким приоритетом
    const specialScenarios = this.userData.step_4_special_scenarios || [];
    
    // Проверяем B2B (высший приоритет)
    if (specialScenarios.includes('b2b')) {
      return {
        type: 'template',
        template: 'b2b',
        reason: 'B2B продажи требуют специального шаблона'
      };
    }

    // Проверяем предзаказ (высокий приоритет)
    if (specialScenarios.includes('pre_order')) {
      return {
        type: 'template',
        template: 'pre_order',
        reason: 'Предзаказ требует специального шаблона'
      };
    }

    // Проверяем ограниченное предложение
    if (specialScenarios.includes('limited_offer')) {
      // Определяем базовый шаблон для комбинации
      const baseTemplate = this.getBaseTemplate();
      if (baseTemplate) {
        return {
          type: 'template',
          template: 'limited_offer',
          base_template: baseTemplate,
          reason: 'Ограниченное предложение с элементами срочности'
        };
      }
    }

    // Проверяем предложенный шаблон из шага 2
    if (this.userData.suggested_template) {
      return {
        type: 'template',
        template: this.userData.suggested_template,
        reason: 'Шаблон определен по типу товара'
      };
    }

    // Применяем правила выбора
    return this.applySelectionRules();
  }

  /**
   * Применение правил выбора шаблона
   */
  applySelectionRules() {
    const rules = this.logic.decision_tree.template_selection.rules;
    const userData = this.userData;

    // Сортируем правила по приоритету (1 - выше)
    const sortedRules = rules.sort((a, b) => a.priority - b.priority);

    for (const rule of sortedRules) {
      if (this.matchRule(rule.conditions)) {
        return {
          type: 'template',
          template: rule.template,
          reason: rule.reason,
          override: rule.override || false
        };
      }
    }

    // Если не найдено подходящее правило, возвращаем базовый шаблон
    const baseTemplate = this.getBaseTemplate();
    return {
      type: 'template',
      template: baseTemplate || 'physical_single',
      reason: 'Использован базовый шаблон по умолчанию'
    };
  }

  /**
   * Проверка соответствия правилу
   */
  matchRule(conditions) {
    for (const key in conditions) {
      const conditionValue = conditions[key];
      const userValue = this.userData[`step_${key === 'product_type' ? '1' : 
                                         key === 'business_model' ? '2' : 
                                         key === 'price_range' ? '3' : '4'}_${key}`] || 
                        this.userData[key];

      if (Array.isArray(conditionValue)) {
        // Если условие - массив, проверяем вхождение
        if (key === 'special_scenarios') {
          const specialScenarios = this.userData.step_4_special_scenarios || [];
          if (conditionValue.length === 0 && specialScenarios.length === 0) {
            continue; // Пустые массивы = нет особых условий
          }
          if (conditionValue.length > 0 && !conditionValue.some(sc => specialScenarios.includes(sc))) {
            return false;
          }
        } else {
          if (!conditionValue.includes(userValue)) {
            return false;
          }
        }
      } else {
        if (conditionValue !== userValue) {
          return false;
        }
      }
    }
    return true;
  }

  /**
   * Получение базового шаблона без особых сценариев
   */
  getBaseTemplate() {
    const productType = this.userData.step_1_product_type;
    const businessModel = this.userData.step_2_business_model;
    const priceRange = this.userData.step_3_price_range;

    if (productType === 'physical_product') {
      if (businessModel === 'variants') return 'physical_multi';
      if (businessModel === 'dropshipping') return 'physical_dropshipping';
      if (priceRange === 'low') return 'low_price_impulse';
      if (priceRange === 'medium') return 'medium_price_justified';
      if (priceRange === 'high') return 'high_price_detailed';
      return 'physical_single';
    }

    if (productType === 'service') return 'service_consultation';
    if (productType === 'digital_product') return 'digital_course';

    return 'physical_single'; // По умолчанию
  }

  /**
   * Быстрый выбор по ключевым словам
   */
  quickSelect(text) {
    const keywords = this.logic.quick_selection.keywords;
    const lowerText = text.toLowerCase();

    for (const [template, templateKeywords] of Object.entries(keywords)) {
      if (templateKeywords.some(keyword => lowerText.includes(keyword))) {
        return {
          type: 'template',
          template: template,
          reason: `Найдено соответствие по ключевым словам`,
          confidence: 'medium'
        };
      }
    }

    return null;
  }

  /**
   * Получить информацию о выбранном шаблоне
   */
  getTemplateInfo(templateId) {
    return this.templates.templates[templateId] || null;
  }

  /**
   * Проверить совместимость шаблонов
   */
  checkCompatibility(baseTemplate, specialScenarios) {
    const matrix = this.logic.compatibility_matrix.matrix;
    const baseInfo = matrix[baseTemplate];

    if (!baseInfo) return { compatible: true, warnings: [] };

    const warnings = [];
    const incompatible = baseInfo.not_compatible_with || [];

    for (const scenario of specialScenarios) {
      if (incompatible.includes(scenario)) {
        warnings.push(`Шаблон ${baseTemplate} несовместим с ${scenario}`);
      }
    }

    return {
      compatible: warnings.length === 0,
      warnings: warnings
    };
  }

  /**
   * Получить рекомендуемые модификации для шаблона
   */
  getRecommendedModifications(templateId, specialScenarios) {
    const modifications = [];
    const matrix = this.logic.compatibility_matrix.matrix;

    // Сезонные модификации
    if (specialScenarios.includes('seasonal')) {
      modifications.push({
        type: 'design',
        description: 'Использовать сезонную цветовую схему',
        items: ['color_scheme', 'seasonal_imagery', 'lifestyle_photos']
      });
    }

    // Модификации для акций
    if (specialScenarios.includes('limited_offer')) {
      modifications.push({
        type: 'urgency',
        description: 'Добавить элементы срочности',
        items: ['countdown_timer', 'stock_counter', 'purchase_counter']
      });
    }

    return modifications;
  }
}

/**
 * Пример использования
 */
function exampleUsage() {
  // Загружаем данные (в реальности из файлов)
  const templates = require('./landing-templates.json');
  const selectionLogic = require('./template-selection-logic.json');

  // Создаем селектор
  const selector = new TemplateSelector(templates, selectionLogic);

  // Вариант 1: Пошаговый выбор
  console.log('=== Пошаговый выбор ===');
  let result = selector.getNextQuestion();
  console.log('Вопрос 1:', result);

  selector.setAnswer('step_1_product_type', 'physical_product');
  result = selector.getNextQuestion();
  console.log('Вопрос 2:', result);

  selector.setAnswer('step_2_business_model', 'single_item');
  result = selector.getNextQuestion();
  console.log('Вопрос 3:', result);

  selector.setAnswer('step_3_price_range', 'low');
  result = selector.getNextQuestion();
  console.log('Вопрос 4:', result);

  selector.setAnswer('step_4_special_scenarios', []);
  result = selector.selectTemplate();
  console.log('Выбранный шаблон:', result);

  // Вариант 2: Быстрый выбор по тексту
  console.log('\n=== Быстрый выбор ===');
  const quickResult = selector.quickSelect('Хочу создать лендинг для подушки со скидкой 50%');
  console.log('Результат быстрого выбора:', quickResult);
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TemplateSelector;
}

// Для использования в браузере
if (typeof window !== 'undefined') {
  window.TemplateSelector = TemplateSelector;
}
