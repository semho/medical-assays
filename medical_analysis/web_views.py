from collections import defaultdict

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

from .constants.parameter_names import PARAMETER_NAMES_RU
from .enums import Status, AnalysisType
from .models import AnalysisSession, MedicalData, UserProfile, SecurityLog
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from .file_processor import FileUploadHandler
from .utils import get_client_ip

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
        serializer = UserRegistrationSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            messages.success(request, "Аккаунт успешно создан!")
            return redirect("dashboard")
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, "medical_analysis/register.html")


def login_view(request):
    """Вход пользователя"""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        serializer = UserLoginSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            login(request, user)

            # Логируем вход
            SecurityLog.objects.create(
                user=user,
                action="USER_LOGIN",
                details=f"Пользователь {user.username} вошел в систему",
                ip_address=get_client_ip(request),
            )

            messages.success(request, "Добро пожаловать!")
            return redirect("dashboard")
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)

    return render(request, "medical_analysis/login.html")


def logout_view(request):
    """Выход пользователя"""
    if request.user.is_authenticated:
        SecurityLog.objects.create(
            user=request.user,
            action="USER_LOGOUT",
            details=f"Пользователь {request.user.username} вышел из системы",
            ip_address=get_client_ip(request),
        )

    logout(request)
    messages.info(request, "Вы вышли из системы")
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

    context = {
        "total_analyses": total_analyses,
        "recent_analyses": recent_analyses,
        "latest_analyses": latest_analyses,
        "active_sessions": active_sessions,
    }

    return render(request, "medical_analysis/dashboard.html", context)


@login_required
def upload_file(request):
    """Страница загрузки файлов"""
    if request.method == "POST" and request.FILES.get("file"):
        try:
            upload_handler = FileUploadHandler()
            session = upload_handler.handle_upload(request.FILES["file"], request.user)

            messages.success(request, "Файл загружен и отправлен на обработку!")

            # Если это HTMX запрос, возвращаем статус
            if request.headers.get("HX-Request"):
                return JsonResponse(
                    {"success": True, "session_id": session.pk, "message": "Файл успешно загружен"},
                    json_dumps_params={"ensure_ascii": False},
                )

            return redirect("analysis_sessions")

        except Exception as e:
            error_msg = str(e)
            messages.error(request, f"Ошибка загрузки файла: {error_msg}")

            if request.headers.get("HX-Request"):
                return JsonResponse({"success": False, "error": error_msg}, json_dumps_params={"ensure_ascii": False})

    return render(request, "medical_analysis/upload.html")


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

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Status.choices,
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

    context = {
        "page_obj": page_obj,
        "type_filter": type_filter,
        "date_from": date_from,
        "date_to": date_to,
        "analysis_types": AnalysisType.choices,
    }

    return render(request, "medical_analysis/results.html", context)


@login_required
def analysis_detail(request, analysis_id):
    """Детальный просмотр анализа"""
    medical_data = get_object_or_404(MedicalData, id=analysis_id, user=request.user)

    # Расшифровываем данные
    decrypted_data = medical_data.decrypt_data()

    if not decrypted_data:
        messages.error(request, "Ошибка расшифровки данных")
        return redirect("analysis_results")

    # Локализуем названия
    parsed_data_localized = {}
    for key, value in decrypted_data.get("parsed_data", {}).items():
        ru_name = PARAMETER_NAMES_RU.get(key, key.replace("_", " ").title())
        parsed_data_localized[ru_name] = value

    # Логируем доступ к данным
    SecurityLog.objects.create(
        user=request.user,
        action="DATA_VIEW",
        details=f"Просмотр анализа {analysis_id}",
        ip_address=get_client_ip(request),
    )

    context = {
        "medical_data": medical_data,
        "parsed_data": parsed_data_localized,
        "raw_text": decrypted_data.get("raw_text", ""),
        "processing_info": decrypted_data.get("processing_info", {}),
    }

    return render(request, "medical_analysis/analysis_detail.html", context)


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
                messages.error(request, "Один из анализов не найден")

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
                messages.success(request, "Настройки обновлены")

        # Обновление профиля пользователя
        if "first_name" in request.POST:
            request.user.first_name = request.POST.get("first_name", "")
            request.user.last_name = request.POST.get("last_name", "")
            request.user.email = request.POST.get("email", "")
            request.user.save()
            messages.success(request, "Профиль обновлен")

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
    messages.success(request, "Анализ удален")

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
        param_name = PARAMETER_NAMES_RU.get(key, key.replace("_", " ").title())

        if val1 is not None and val2 is not None:
            try:
                val1_float = float(val1)
                val2_float = float(val2)

                diff = val2_float - val1_float
                percent_change = (diff / val1_float) * 100 if val1_float != 0 else 0

                differences[key] = {
                    "parameter_name": param_name,
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
                    "parameter_name": param_name,
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
                "parameter_name": param_name,
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
    return JsonResponse({"error": "Неподдерживаемый формат"}, status=400)


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

    context = {
        "available_types": available_types,
        "analysis_types": AnalysisType.choices,
    }

    return render(request, "medical_analysis/trends.html", context)


@login_required
def trends_data(request, analysis_type):
    """API endpoint для получения данных графиков"""

    # Получаем все анализы данного типа
    analyses = MedicalData.objects.filter(user=request.user, analysis_type=analysis_type).order_by("analysis_date")

    if analyses.count() < 2:
        return JsonResponse({"error": "Недостаточно данных для построения графика (минимум 2 анализа)"}, status=400)

    # Структура для хранения данных по параметрам
    parameters_data = defaultdict(
        lambda: {"dates": [], "values": [], "units": None, "reference_min": [], "reference_max": [], "name": None}
    )

    for analysis in analyses:
        decrypted = analysis.decrypt_data()
        if not decrypted:
            continue

        parsed_data = decrypted.get("parsed_data", {})
        date_str = analysis.analysis_date.isoformat()

        for param_key, param_data in parsed_data.items():
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
                value_float = float(value)
            except (ValueError, TypeError):
                continue

            # Добавляем данные
            parameters_data[param_key]["dates"].append(date_str)
            parameters_data[param_key]["values"].append(value_float)

            # Единицы измерения
            if not parameters_data[param_key]["units"]:
                parameters_data[param_key]["units"] = unit

            # Русское название
            if not parameters_data[param_key]["name"]:
                parameters_data[param_key]["name"] = PARAMETER_NAMES_RU.get(
                    param_key, param_key.replace("_", " ").title()
                )

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
        if len(data["values"]) >= 2:
            result[param_key] = data

    return JsonResponse(result)


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
