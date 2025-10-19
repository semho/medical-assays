import json
from collections import defaultdict
from django.utils.translation import gettext as _
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
import logging

from medical_mvp.settings import RECAPTCHA_SECRET_KEY, RECAPTCHA_PUBLIC_KEY
from .constants import PARAMETER_TYPE_MAP
from .enums import Status, AnalysisType, SubcriptionType
from .models import AnalysisSession, MedicalData, UserProfile, SecurityLog
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from .file_processor import FileUploadHandler
from medical_analysis.utils.core import get_client_ip, get_all_units_list, parse_value_with_operator, verify_recaptcha
from .utils.i18n_helpers import get_parameter_display_name, get_analysis_type_display

logger = logging.getLogger(__name__)


def home(request):
    """Главная страница"""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "medical_analysis/home.html")


def register_view(request):
    """Регистрация пользователя"""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        # Verify reCAPTCHA
        recaptcha_response = request.POST.get("g-recaptcha-response")
        if not verify_recaptcha(recaptcha_response, RECAPTCHA_SECRET_KEY):
            messages.error(request, _("Пожалуйста, пройдите проверку CAPTCHA"))
            return render(request, "medical_analysis/register.html")

        serializer = UserRegistrationSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            messages.success(request, _("Аккаунт успешно создан!"))
            return redirect("dashboard")
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    # Pass reCAPTCHA public key to template
    context = {"RECAPTCHA_PUBLIC_KEY": RECAPTCHA_PUBLIC_KEY}
    return render(request, "medical_analysis/register.html", context)


def login_view(request):
    """Вход пользователя"""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        # Verify reCAPTCHA
        recaptcha_response = request.POST.get("g-recaptcha-response")
        if not verify_recaptcha(recaptcha_response, RECAPTCHA_SECRET_KEY):
            messages.error(request, _("Пожалуйста, пройдите проверку CAPTCHA"))
            return render(request, "medical_analysis/login.html")

        serializer = UserLoginSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            login(request, user)

            # Логируем вход
            SecurityLog.objects.create(
                user=user,
                action="USER_LOGIN",
                details=_(f"Пользователь {user.username} вошел в систему"),
                ip_address=get_client_ip(request),
            )

            messages.success(request, _("Добро пожаловать!"))
            return redirect("dashboard")
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
    context = {"RECAPTCHA_PUBLIC_KEY": RECAPTCHA_PUBLIC_KEY}
    return render(request, "medical_analysis/login.html", context)


def logout_view(request):
    """Выход пользователя"""
    if request.user.is_authenticated:
        SecurityLog.objects.create(
            user=request.user,
            action="USER_LOGOUT",
            details=_(f"Пользователь {request.user.username} вышел из системы"),
            ip_address=get_client_ip(request),
        )

    logout(request)
    messages.info(request, _("Вы вышли из системы"))
    return redirect("home")


@login_required
def dashboard(request):
    # Получаем статистику по РЕЗУЛЬТАТАМ, а не сессиям
    total_analyses = MedicalData.objects.filter(user=request.user).count()
    recent_analyses = MedicalData.objects.filter(
        user=request.user, created_at__gte=timezone.now() - timedelta(days=30)
    ).count()

    # Последние анализы (результаты, не сессии)
    latest_analyses = MedicalData.objects.filter(user=request.user).order_by("-analysis_date")[:5]

    # Активные сессии - только те что реально в процессе
    active_sessions = AnalysisSession.objects.filter(
        user=request.user, processing_status__in=["uploading", "processing"]
    ).order_by("-upload_timestamp")

    # Информация о подписке
    sub = request.user.subscription
    if sub.subscription_type == SubcriptionType.PAID:
        remaining_uploads = _("Неограниченно")
    else:
        remaining_uploads = max(0, sub.remaining_uploads())

    context = {
        "total_analyses": total_analyses,
        "recent_analyses": recent_analyses,
        "latest_analyses": latest_analyses,
        "active_sessions": active_sessions,
        "remaining_uploads": remaining_uploads,
        "subscription_type": sub.subscription_type,
    }

    return render(request, "medical_analysis/dashboard.html", context)


@login_required
def upload_file(request):
    """Страница загрузки файлов"""
    sub = request.user.subscription
    if not sub.can_upload():
        messages.warning(request, _("Вы исчерпали лимит бесплатных загрузок. Оформите подписку для продолжения."))
        return redirect("subscription_upgrade")

    if request.method == "POST" and request.FILES.get("file"):
        try:
            upload_handler = FileUploadHandler()
            session = upload_handler.handle_upload(request.FILES["file"], request.user)

            sub.used_uploads += 1
            sub.save()

            messages.success(request, _("Файл загружен и отправлен на обработку!"))

            # Если это HTMX запрос, возвращаем статус
            if request.headers.get("HX-Request"):
                return JsonResponse(
                    {"success": True, "session_id": session.pk, "message": _("Файл успешно загружен")},
                    json_dumps_params={"ensure_ascii": False},
                )

            return redirect('session_wait', session_id=session.pk)

        except Exception as e:
            error_msg = str(e)
            messages.error(request, _(f"Ошибка загрузки файла: {error_msg}"))

            if request.headers.get("HX-Request"):
                return JsonResponse({"success": False, "error": error_msg}, json_dumps_params={"ensure_ascii": False})

    return render(request, "medical_analysis/upload.html")


@login_required
def subscription_upgrade(request):
    """Страница апгрейда подписки"""
    sub = request.user.subscription
    remaining = sub.remaining_uploads()

    context = {
        'remaining_uploads': max(0, remaining) if remaining != float('inf') else _('Неограниченно'),
        'subscription_type': sub.subscription_type,
    }
    return render(request, "medical_analysis/subscription_upgrade.html", context)

@login_required
def analysis_sessions(request):
    """Список сессий анализов"""
    sessions = AnalysisSession.objects.filter(user=request.user).order_by("-upload_timestamp")

    # Фильтрация по статусу
    status_filter = request.GET.get("status")
    if status_filter:
        sessions = sessions.filter(processing_status=status_filter)

    # Пагинация
    paginator = Paginator(sessions, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Обработка choices с переводом
    status_choices = [(choice[0], get_analysis_type_display(choice[0])) for choice in Status.choices]

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": status_choices,
    }

    return render(request, "medical_analysis/sessions.html", context)


@login_required
def session_status(request, session_id):
    """HTMX endpoint для проверки статуса сессии"""
    session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)

    context = {"session": session}
    return render(request, "medical_analysis/partials/session_status.html", context)


@login_required
def analysis_results(request):
    """Список результатов анализов"""
    medical_data = MedicalData.objects.filter(user=request.user)

    # Фильтрация по типу анализа
    type_filter = request.GET.get("type")
    if type_filter:
        medical_data = medical_data.filter(analysis_type=type_filter)

    # Поиск по дате
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        medical_data = medical_data.filter(analysis_date__gte=date_from)
    if date_to:
        medical_data = medical_data.filter(analysis_date__lte=date_to)

    # Пагинация
    paginator = Paginator(medical_data, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Обработка choices с переводом
    analysis_types = [(choice[0], get_analysis_type_display(choice[0])) for choice in AnalysisType.choices]

    context = {
        "page_obj": page_obj,
        "type_filter": type_filter,
        "date_from": date_from,
        "date_to": date_to,
        "analysis_types": analysis_types,
        "date_placeholder": _("date placeholder"),
    }

    return render(request, "medical_analysis/results.html", context)


@login_required
def analysis_detail(request, analysis_id):
    """Детальный просмотр и редактирование анализа"""
    medical_data = get_object_or_404(MedicalData, id=analysis_id, user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "confirm":
            # Собираем обновленные данные от пользователя
            decrypted = medical_data.decrypt_data()
            if not decrypted:
                messages.error(request, _("Ошибка расшифровки данных"))
                return redirect("analysis_results")

            updated_parsed_data = {}

            # Проходим по всем параметрам из формы
            for key in request.POST:
                if key.startswith("value_"):
                    param_key = key.replace("value_", "")

                    try:
                        value_str = request.POST.get(f"value_{param_key}", "").strip()
                        logger.info(f"Обработка {param_key}: '{value_str}'")
                        # Парсим значение с оператором
                        value, operator = parse_value_with_operator(value_str)

                        if value is None:
                            logger.warning(_(f"Не удалось распарсить значение: {value_str}"))
                            messages.warning(request, _(f"Ошибка в параметре {param_key}"))
                            continue

                        unit = request.POST.get(f"unit_{param_key}", "")
                        reference = request.POST.get(f"reference_{param_key}", "")
                        status = request.POST.get(f"status_{param_key}", "норма")

                        param_data = {
                            "value": value,
                            "unit": unit,
                            "reference": reference,
                            "status": status,
                        }

                        # Добавляем оператор если есть
                        if operator:
                            param_data["operator"] = operator

                        updated_parsed_data[param_key] = param_data
                    except (ValueError, TypeError) as e:
                        logger.error(_(f"Ошибка парсинга {param_key}: {e}"))
                        messages.warning(request, _(f"Ошибка в параметре {param_key}: {e}"))
                        continue


            # Обновляем зашифрованные данные
            decrypted["parsed_data"] = updated_parsed_data
            decrypted["confirmed"] = True
            decrypted["edited_by_user"] = True

            if "grouped_data" in decrypted:
                new_grouped = {
                    "blood_general": {},
                    "blood_biochem": {},
                    "hormones": {},
                    "other": {},
                }

                for param_key, param_value in updated_parsed_data.items():
                    param_type = PARAMETER_TYPE_MAP.get(param_key.lower())

                    if param_type == "blood_general":
                        new_grouped["blood_general"][param_key] = param_value
                    elif param_type == "blood_biochem":
                        new_grouped["blood_biochem"][param_key] = param_value
                    elif param_type == "hormones":
                        new_grouped["hormones"][param_key] = param_value
                    else:
                        new_grouped["other"][param_key] = param_value

                decrypted["grouped_data"] = new_grouped

            medical_data.encrypt_and_save(decrypted)
            medical_data.is_confirmed = True
            medical_data.save()
            SecurityLog.objects.create(
                user=request.user,
                action="ANALYSIS_CONFIRMED",
                details=_(f"Пользователь подтвердил анализ {analysis_id}"),
                ip_address=get_client_ip(request),
            )

            messages.success(request, _("Анализ успешно сохранён"))
            return redirect("analysis_results")

        elif action == "delete":
            # Удаляем анализ
            SecurityLog.objects.create(
                user=request.user,
                action="ANALYSIS_DELETED",
                details=_(f"Удалён анализ {analysis_id}"),
                ip_address=get_client_ip(request),
            )
            medical_data.delete()
            messages.info(request, _("Анализ удалён"))
            return redirect("dashboard")

    # GET запрос - показываем форму
    decrypted_data = medical_data.decrypt_data()

    if not decrypted_data:
        messages.error(request, _("Ошибка расшифровки данных"))
        return redirect("analysis_results")

    grouped_data = decrypted_data.get('grouped_data')

    if grouped_data:
        # Новый формат - объединяем все типы
        parsed_data = {}
        for type_key in ['blood_general', 'blood_biochem', 'hormones', 'other']:
            parsed_data.update(grouped_data.get(type_key, {}))
    else:
        # Старый формат
        parsed_data = decrypted_data.get('parsed_data', {})

    # Подготавливаем данные для отображения
    parameters_list = []
    for param_key, param_value in parsed_data.items():
        if isinstance(param_value, dict):
            value = param_value.get("value")
            operator = param_value.get("operator", "")
            unit = param_value.get("unit", "")
            reference = param_value.get("reference", "")
            status = param_value.get("status", "норма")
        else:
            value = param_value
            operator = ""
            unit = ""
            reference = ""
            status = "норма"

        if value is None or value == "" or (isinstance(value, str) and value.strip() == ""):
            continue

        if operator:
            display_value = f"{operator} {value}"
        else:
            # Оставляем как есть для обычных чисел
            if isinstance(value, str):
                display_value = value.replace(",", ".")
            else:
                display_value = value

        display_name = get_parameter_display_name(param_key, unit)
        parameters_list.append({
            "key": param_key,
            "name": display_name,
            "value": display_value,
            "unit": unit,
            "reference": reference,
            "status": status
        })

    # Сортируем по русскому названию
    parameters_list.sort(key=lambda x: x["name"])

    # Определяем правильный тип на основе реально заполненных параметров
    actual_type_counts = {"blood_general": 0, "blood_biochem": 0, "hormones": 0}
    for param in parameters_list:
        param_type = PARAMETER_TYPE_MAP.get(param["key"].lower())
        if param_type in actual_type_counts:
            actual_type_counts[param_type] += 1

    # Находим тип с максимальным количеством параметров
    max_count = max(actual_type_counts.values()) if actual_type_counts.values() else 0
    if max_count > 0:
        for type_name, count in actual_type_counts.items():
            if count == max_count:
                # Обновляем тип только если он отличается
                if medical_data.analysis_type != type_name:
                    logger.info(_(f"Корректировка типа: {medical_data.analysis_type} → {type_name}"))
                    medical_data.analysis_type = type_name
                    medical_data.save(update_fields=['analysis_type'])
                break

    # Логируем просмотр
    SecurityLog.objects.create(
        user=request.user,
        action="DATA_VIEW",
        details=_(f"Просмотр анализа {analysis_id}"),
        ip_address=get_client_ip(request),
    )

    context = {
        "medical_data": medical_data,
        "parameters": parameters_list,
        "all_units": get_all_units_list(),
        "edit_mode": not medical_data.is_confirmed,
        "raw_text": decrypted_data.get("raw_text", ""),
        "processing_info": decrypted_data.get("processing_info", {}),
    }

    return render(request, "medical_analysis/analysis_confirm.html", context)


@login_required
def compare_analyses(request):
    """Сравнение анализов"""
    if request.method == "POST":
        analysis1_id = request.POST.get("analysis1_id")
        analysis2_id = request.POST.get("analysis2_id")

        if analysis1_id and analysis2_id:
            try:
                analysis1 = MedicalData.objects.get(id=analysis1_id, user=request.user)
                analysis2 = MedicalData.objects.get(id=analysis2_id, user=request.user)

                data1 = analysis1.decrypt_data()
                data2 = analysis2.decrypt_data()

                if data1 and data2:
                    comparison = calculate_differences(data1.get("parsed_data", {}), data2.get("parsed_data", {}))

                    context = {
                        "analysis1": analysis1,
                        "analysis2": analysis2,
                        "data1": data1.get("parsed_data", {}),
                        "data2": data2.get("parsed_data", {}),
                        "comparison": comparison,
                    }

                    return render(request, "medical_analysis/comparison_result.html", context)

            except MedicalData.DoesNotExist:
                messages.error(request, _("Один из анализов не найден"))

    # Получаем доступные анализы для сравнения
    available_analyses = MedicalData.objects.filter(user=request.user).order_by("-analysis_date")

    context = {
        "available_analyses": available_analyses,
    }

    return render(request, "medical_analysis/compare.html", context)


@login_required
def profile_settings(request):
    """Настройки профиля"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Обновление языка
        if "language_preference" in request.POST:
            language = request.POST.get("language_preference")
            if language in ["ru", "en"]:
                profile.language_preference = language
                profile.save()
                messages.success(request, _("Настройки обновлены"))

        # Обновление профиля пользователя
        if "first_name" in request.POST:
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.email = request.POST.get("email", "")
            request.user.save()
            messages.success(request, _("Профиль обновлен"))

        return redirect("profile_settings")

    context = {
        "profile": profile,
    }

    return render(request, "medical_analysis/profile.html", context)


@login_required
@require_POST
def delete_analysis(request, analysis_id):
    """Удаление анализа"""
    medical_data = get_object_or_404(MedicalData, id=analysis_id, user=request.user)

    # Логируем удаление
    SecurityLog.objects.create(
        user=request.user,
        action="DATA_DELETED",
        details=f"Удален анализ {analysis_id} от {medical_data.analysis_date}",
        ip_address=get_client_ip(request),
    )

    medical_data.delete()
    messages.success(request, _("Анализ удален"))

    if request.headers.get("HX-Request"):
        return HttpResponse(status=204)  # No content для HTMX

    return redirect("analysis_results")


def calculate_differences(data1, data2):
    """Вычисление разностей между анализами"""
    differences = {}

    for key in set(data1.keys()) | set(data2.keys()):
        val1_data = data1.get(key)
        val2_data = data2.get(key)

        # Получаем значения из словаря или напрямую
        if isinstance(val1_data, dict):
            val1 = val1_data.get("value")
            unit1 = val1_data.get("unit", "")
        else:
            val1 = val1_data
            unit1 = ""

        if isinstance(val2_data, dict):
            val2 = val2_data.get("value")
            unit2 = val2_data.get("unit", "")
        else:
            val2 = val2_data
            unit2 = ""

        # Получаем русское название параметра
        # param_name = PARAMETER_NAMES_RU.get(key, key.replace("_", " ").title())
        display_name = get_parameter_display_name(key, unit1 or unit2)
        if val1 is not None and val2 is not None:
            try:
                val1_float = float(val1)
                val2_float = float(val2)

                diff = val2_float - val1_float
                percent_change = (diff / val1_float) * 100 if val1_float != 0 else 0

                differences[key] = {
                    "parameter_name": display_name,
                    "value1": val1,
                    "value2": val2,
                    "unit1": unit1,
                    "unit2": unit2,
                    "absolute_change": round(diff, 2),
                    "percent_change": round(percent_change, 1),
                    "trend": "up" if diff > 0 else "down" if diff < 0 else "stable",
                }
            except (ValueError, TypeError):
                differences[key] = {
                    "parameter_name": display_name,
                    "value1": val1,
                    "value2": val2,
                    "unit1": unit1,
                    "unit2": unit2,
                    "absolute_change": "—",
                    "percent_change": "—",
                    "trend": "unknown",
                }
        else:
            differences[key] = {
                "parameter_name": display_name,
                "value1": val1 if val1 is not None else "—",
                "value2": val2 if val2 is not None else "—",
                "unit1": unit1,
                "unit2": unit2,
                "absolute_change": "—",
                "percent_change": "—",
                "trend": "unknown",
            }

    return differences


@login_required
def export_data(request):
    """Экспорт данных пользователя"""
    format_type = request.GET.get("format", "json")

    medical_data = MedicalData.objects.filter(user=request.user)

    if format_type == "json":
        data = []
        for item in medical_data:
            decrypted = item.decrypt_data()
            if decrypted:
                data.append(
                    {
                        "id": item.pk,
                        "date": item.analysis_date.isoformat(),
                        "type": item.analysis_type,
                        "data": decrypted.get("parsed_data", {}),
                    }
                )

        response = JsonResponse({"analyses": data}, json_dumps_params={"ensure_ascii": False})
        response["Content-Disposition"] = 'attachment; filename="medical_data.json"'
        return response

    # Пока поддерживаем только JSON
    return JsonResponse({"error": _("Неподдерживаемый формат")}, status=400)


@login_required
def recent_sessions_partial(request):
    """Частичный шаблон последних сессий для HTMX"""
    sessions = AnalysisSession.objects.filter(user=request.user).order_by("-upload_timestamp")[:5]

    return render(request, "medical_analysis/partials/recent_sessions.html", {"sessions": sessions})


@login_required
def analysis_trends(request):
    """Страница графиков динамики показателей"""
    # Получаем доступные типы анализов у пользователя
    available_types = MedicalData.objects.filter(user=request.user).values_list("analysis_type", flat=True).distinct()

    # Обработка choices с переводом
    analysis_types = [(choice[0], get_analysis_type_display(choice[0])) for choice in AnalysisType.choices]

    # Создаём словарь типов для JS
    analysis_type_names = {choice[0]: choice[1] for choice in analysis_types}


    context = {
        "available_types": available_types,
        "analysis_types": analysis_types,
        "analysis_type_names_json": json.dumps(analysis_type_names, ensure_ascii=False),
    }

    return render(request, "medical_analysis/trends.html", context)


@login_required
def trends_data(request, analysis_type=None):
    """Получить данные графиков через API endpoint.

    Теперь с поддержкой групповых данных.
    """
    # Получаем все анализы пользователя
    analyses = MedicalData.objects.filter(user=request.user).order_by("analysis_date", "created_at")

    if analyses.count() < 1:
        return JsonResponse({"error": _("Нет данных для построения графиков")}, status=400)

    # Структура для хранения данных по параметрам
    parameters_data = defaultdict(
        lambda: {
            "dates": [],
            "values": [],
            "units": None,
            "reference_min": [],
            "reference_max": [],
            "name": None,
            "analysis_type": None,
        }
    )

    for analysis in analyses:
        decrypted = analysis.decrypt_data()
        if not decrypted:
            continue

        date_str = analysis.analysis_date.isoformat()

        # НОВОЕ: Проверяем наличие групповых данных
        grouped_data = decrypted.get("grouped_data", {})

        if grouped_data:
            # Новый формат с групповыми данными
            # Если тип указан - берём только его
            if analysis_type and analysis_type != "all":
                parsed_data = grouped_data.get(analysis_type, {})
            else:
                # Объединяем все типы
                parsed_data = {}
                for type_key in ["blood_general", "blood_biochem", "hormones", "other"]:
                    parsed_data.update(grouped_data.get(type_key, {}))
        else:
            # Старый формат (для совместимости)
            parsed_data = decrypted.get("parsed_data", {})

            # Если указан фильтр по типу - фильтруем
            if analysis_type and analysis_type != "all":
                filtered_data = {}
                for param_key, param_data in parsed_data.items():
                    param_real_type = PARAMETER_TYPE_MAP.get(param_key.lower())
                    if param_real_type == analysis_type:
                        filtered_data[param_key] = param_data
                parsed_data = filtered_data

        # Обрабатываем параметры
        for param_key, param_data in parsed_data.items():
            # Определяем реальный тип параметра
            param_real_type = PARAMETER_TYPE_MAP.get(param_key.lower())

            # Получаем значение
            if isinstance(param_data, dict):
                value = param_data.get("value")
                unit = param_data.get("unit", "")
                reference = param_data.get("reference", "")
            else:
                value = param_data
                unit = ""
                reference = ""

            try:
                # Если есть оператор - используем только числовое значение для графика
                if isinstance(param_data, dict) and param_data.get("operator"):
                    value_float = float(value)
                else:
                    value_float = float(value)
            except (ValueError, TypeError):
                continue

            # Добавляем данные
            parameters_data[param_key]["dates"].append(date_str)
            parameters_data[param_key]["values"].append(value_float)

            # Тип анализа для параметра
            if not parameters_data[param_key]["analysis_type"]:
                parameters_data[param_key]["analysis_type"] = param_real_type or "other"

            # Единицы измерения
            if not parameters_data[param_key]["units"]:
                parameters_data[param_key]["units"] = unit

            # Русское название
            if not parameters_data[param_key]["name"]:
                parameters_data[param_key]["name"] = get_parameter_display_name(param_key, unit)
                # parameters_data[param_key]["name"] = PARAMETER_NAMES_RU.get(
                #     param_key, param_key.replace("_", " ").title()
                # )

            # Парсим референсные значения
            if reference:
                ref_min, ref_max = parse_reference_range(reference)
                parameters_data[param_key]["reference_min"].append(ref_min)
                parameters_data[param_key]["reference_max"].append(ref_max)
            else:
                parameters_data[param_key]["reference_min"].append(None)
                parameters_data[param_key]["reference_max"].append(None)

    # Фильтруем параметры с достаточным количеством точек
    result = {}
    for param_key, data in parameters_data.items():
        if len(data["values"]) >= 1:  # Даже одна точка имеет смысл
            result[param_key] = data

    return JsonResponse(result)


@login_required
def session_wait(request, session_id):
    """Страница ожидания обработки с автоматическим редиректом"""
    session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)

    # # Если обработка завершена - перенаправляем на подтверждение
    # if session.processing_status == Status.COMPLETED and hasattr(session, "medical_data") and session.medical_data:
    #     return redirect("analysis_detail", analysis_id=session.medical_data.id)
    #
    # # Если ошибка - показываем сообщение
    # if session.processing_status == Status.ERROR:
    #     messages.error(request, f"Ошибка обработки: {session.error_message}")
    #     return redirect("upload_file")

    context = {
        "session": session,
    }

    return render(request, "medical_analysis/session_wait.html", context)


@login_required
def check_session_status(request, session_id):
    """AJAX endpoint для проверки статуса сессии"""
    session = get_object_or_404(AnalysisSession, id=session_id, user=request.user)

    # примерные этапы обработки для расчета прогресса
    stages = {
        "uploading": {"progress": 10, "message": _("загрузка файла...")},
        "processing": {"progress": 30, "message": _("обработка файла...")},
        "ocr": {"progress": 50, "message": _("распознавание текста...")},
        "parsing": {"progress": 70, "message": _("анализ данных...")},
        "completed": {"progress": 100, "message": _("готово")},
        "error": {"progress": 0, "message": _("ошибка обработки")},
    }

    current_stage = stages.get(session.processing_status, {"progress": 30, "message": "обработка..."})

    response_data = {
        "status": session.processing_status,
        "progress": current_stage["progress"],
        "message": current_stage["message"],
        "error_message": session.error_message if session.processing_status == "error" else None,
    }

    # response_data = {
    #     "status": session.processing_status,
    #     "analysis_type": session.analysis_type,
    # }
    #
    # # Если обработка завершена, возвращаем URL для редиректа
    # if session.processing_status == Status.COMPLETED:
    #     if hasattr(session, "medical_data") and session.medical_data:
    #         response_data["redirect_url"] = f"/results/{session.medical_data.id}/"
    #
    # elif session.processing_status == Status.ERROR:
    #     response_data["error_message"] = session.error_message

    if session.processing_status == Status.COMPLETED:
        if hasattr(session, 'medical_data'):
            response_data["analysis_id"] = session.medical_data.id

    return JsonResponse(response_data)


def parse_reference_range(reference_str):
    """Парсинг референсного диапазона из строки"""
    try:
        # Формат: "138.50-166.70" или "138.50 - 166.70"
        parts = reference_str.replace(" ", "").split("-")
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
    except (ValueError, AttributeError):
        pass

    return None, None

@login_required
def subscription_contact(request):
    """Страница контакта для оплаты"""
    return render(request, "medical_analysis/subscription_contact.html")