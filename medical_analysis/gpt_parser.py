import json
import logging
import re

import tiktoken
from openai import OpenAI
from django.conf import settings
from medical_analysis.constants.prompts import BLOOD_GENERAL_PROMPT, BLOOD_BIOCHEM_PROMPT, HORMONES_PROMPT
from medical_analysis.enums import AnalysisType

logger = logging.getLogger(__name__)

class GPTMedicalParser:
    """Парсер медицинских анализов через GPT с поддержкой разных лабораторий"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_input_tokens = settings.GPT_MAX_INPUT_TOKENS
        self.max_output_tokens = settings.GPT_MAX_OUTPUT_TOKENS
        self.temperature = settings.GPT_TEMPERATURE

        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Подсчет токенов в тексте"""
        return len(self.encoding.encode(text))

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Обрезка текста до максимального количества токенов"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        truncated_text = self.encoding.decode(truncated_tokens)

        logger.warning(f"Текст обрезан с {len(tokens)} до {len(truncated_tokens)} токенов")
        return truncated_text

    def parse_analysis(
            self,
            text: str,
            analysis_type: str = "blood_general",
            laboratory: str = "unknown"
    ) -> dict:
        """
        Парсинг анализа через GPT с контролем токенов

        Args:
            text: Текст анализа
            analysis_type: Тип анализа
            laboratory: Название лаборатории (для адаптации промпта)
        """

        # Предобработка текста
        text = preprocess_analysis_text(text)
        logger.info("Текст предобработан для GPT")

        # Подсчитываем токены входного текста
        input_tokens = self.count_tokens(text)
        logger.info(f"Входной текст: {input_tokens} токенов")

        # Если текст слишком большой - обрезаем
        if input_tokens > self.max_input_tokens:
            logger.warning(f"Текст превышает лимит ({input_tokens} > {self.max_input_tokens})")
            text = self.truncate_text(text, self.max_input_tokens)
            input_tokens = self.count_tokens(text)
            logger.info(f"После обрезки: {input_tokens} токенов")

        system_prompt = self._get_system_prompt(analysis_type, laboratory)

        # Подсчитываем общее количество токенов запроса
        system_tokens = self.count_tokens(system_prompt)
        total_request_tokens = system_tokens + input_tokens
        logger.info(
            f"Общий запрос: {total_request_tokens} токенов "
            f"(система: {system_tokens}, текст: {input_tokens})"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Текст анализа:\n\n{text}"},
                ],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Логируем использование токенов
            usage = response.usage
            if usage:
                logger.info(
                    f"GPT токены: запрос={usage.prompt_tokens}, "
                    f"ответ={usage.completion_tokens}, всего={usage.total_tokens}"
                )

                # Оценка стоимости
                cost = self._estimate_cost(usage.prompt_tokens, usage.completion_tokens)
                logger.info(f"Примерная стоимость: ${cost:.4f}")

            logger.info(f"GPT распознал {len(result.get('parameters', {}))} параметров")
            return result

        except Exception as e:
            logger.error(f"Ошибка GPT парсинга: {e}")
            return {}

    def _get_system_prompt(self, analysis_type: str, laboratory: str = "unknown") -> str:
        """
        Системный промпт для GPT с адаптацией под лабораторию

        Args:
            analysis_type: Тип анализа
            laboratory: Название лаборатории
        """

        # Базовый промпт для типа анализа
        if analysis_type == AnalysisType.BLOOD_GENERAL:
            base_prompt = BLOOD_GENERAL_PROMPT
        elif analysis_type == AnalysisType.BLOOD_BIOCHEM:
            base_prompt = BLOOD_BIOCHEM_PROMPT
        elif analysis_type == AnalysisType.HORMONES:
            base_prompt = HORMONES_PROMPT
        else:
            base_prompt = "Извлеки ВСЕ медицинские показатели в JSON: parameters с value, unit, reference, status."

        # Добавляем специфичные инструкции для известных лабораторий
        lab_hints = {
            'invitro': """

            ОСОБЕННОСТИ INVITRO:
            - Единицы измерения часто идут ПЕРЕД названием параметра
            - Формат: "ммоль/л \n Глюкоза \n 5.2"
            - Референсные значения обычно в конце строки
            - Код исследования вида "A09.05.XXX" - игнорируй
            """,
            'helix': """

            ОСОБЕННОСТИ HELIX:
            - Строгий табличный формат с фиксированными колонками
            - Формат: "Параметр | Значение | Единицы | Референс"
            - Отклонения помечены символом *
            """,
            'kdl': """

            ОСОБЕННОСТИ КДЛ:
            - Смешанный формат, может быть и табличный и построчный
            - Референсные значения иногда на отдельной строке
            """,
            'gemotest': """

            ОСОБЕННОСТИ GEMOTEST:
            - Похож на Invitro
            - Единицы могут быть как до, так и после значения
            """,
        }

        # Добавляем подсказку для лаборатории, если она известна
        lab_hint = lab_hints.get(laboratory, "")

        return base_prompt + lab_hint

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Оценка стоимости запроса"""
        prices = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},  # $0.15/$0.60 per 1M tokens
        }

        model_prices = prices.get(self.model, prices["gpt-4o-mini"])
        cost = (
                (input_tokens / 1_000_000 * model_prices["input"]) +
                (output_tokens / 1_000_000 * model_prices["output"])
        )
        return cost

def preprocess_analysis_text(text: str) -> str:
    """Предобработка текста для улучшения распознавания"""
    lines = text.split("\n")
    cleaned_lines = []

    # Ищем секцию с анализами
    in_analysis_section = False

    for i, line in enumerate(lines):
        # Определяем начало секции анализов
        if "ОБЩИЙ АНАЛИЗ КРОВИ" in line.upper() or "CBC" in line.upper():
            in_analysis_section = True
            cleaned_lines.append(line)
            continue

        # Конец секции
        if in_analysis_section and ("БИОХИМИЧЕСКИЕ" in line.upper() or "ГОРМОНАЛЬНЫЕ" in line.upper()):
            in_analysis_section = False

        # Если в секции анализов - пытаемся исправить порядок
        if in_analysis_section and i + 2 < len(lines):
            # Паттерн: единицы → название → значение → референс
            # Нужно: название → значение → единицы → референс

            # Проверяем, похоже ли на единицы измерения
            if re.match(r"^\d+\^?\d*/л|^г/л|^%|^фл|^пг|^мм/ч", line.strip()):
                # Следующая строка - название параметра
                next_line = lines[i + 1].strip()
                if any(
                    keyword in next_line.lower()
                    for keyword in [
                        "лейкоциты",
                        "эритроциты",
                        "гемоглобин",
                        "тромбоциты",
                        "wbc",
                        "rbc",
                        "hgb",
                        "plt",
                        "нейтрофилы",
                        "лимфоциты",
                    ]
                ):
                    # Следующая за ней - значение
                    if i + 2 < len(lines):
                        value_line = lines[i + 2].strip()
                        # Собираем в правильном порядке
                        cleaned_lines.append(f"{next_line} {value_line} {line}")
                        continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
