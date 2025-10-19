from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import logging
from medical_analysis.models import AnalysisSession, MedicalData, UserProfile, SecurityLog
from medical_analysis.file_processor import FileUploadHandler
from medical_analysis.serializers import (
    UserProfileSerializer,
    FileUploadSerializer,
    AnalysisSessionSerializer,
    MedicalDataSerializer,
)
from medical_analysis.utils.core import get_client_ip
from django.utils.translation import gettext as _
logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")


class UserProfileViewSet(viewsets.ModelViewSet):
    """API для управления профилем пользователя"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Получить профиль текущего пользователя"""
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"])
    def update_language(self, request):
        """Обновить языковые настройки"""
        profile = self.get_object()
        language = request.data.get("language_preference")

        if language in ["ru", "en"]:
            profile.language_preference = language
            profile.save()

            SecurityLog.objects.create(
                user=request.user,
                action="LANGUAGE_CHANGED",
                details=f"Язык изменен на: {language}",
                ip_address=get_client_ip(request),
            )

            return Response({"status": "success", "language": language})
        else:
            return Response({"error": _("Неподдерживаемый язык")}, status=status.HTTP_400_BAD_REQUEST)


class FileUploadViewSet(viewsets.ViewSet):
    """API для загрузки медицинских файлов"""

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        """Загрузка нового файла для анализа"""
        try:
            serializer = FileUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            uploaded_file = serializer.validated_data["file"]

            # Проверяем, есть ли профиль пользователя
            profile, created = UserProfile.objects.get_or_create(user=request.user)

            # Обрабатываем загрузку
            upload_handler = FileUploadHandler()
            session = upload_handler.handle_upload(uploaded_file, request.user)

            # Логируем действие
            SecurityLog.objects.create(
                user=request.user,
                action="FILE_UPLOAD_INITIATED",
                details=_(f"Начата загрузка файла: {uploaded_file.name}"),
                ip_address=get_client_ip(request),
            )

            return Response(
                {
                    "session_id": session.pk,
                    "status": session.processing_status,
                    "message": _("Файл загружен и отправлен на обработку"),
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")
            return Response({"error": _("Внутренняя ошибка сервера")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def status(self, request):
        """Проверить статус обработки файла"""
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response({"error": _("Не указан session_id")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = AnalysisSession.objects.get(id=session_id, user=request.user)

            response_data = {
                "session_id": session.pk,
                "status": session.processing_status,
                "upload_time": session.upload_timestamp,
                "processing_started": session.processing_started,
                "processing_completed": session.processing_completed,
                "file_deleted": session.file_deleted_timestamp is not None,
                "analysis_type": session.analysis_type,
            }

            if session.processing_status == "error":
                response_data["error_message"] = session.error_message

            return Response(response_data)

        except AnalysisSession.DoesNotExist:
            return Response({"error": _("Сессия не найдена")}, status=status.HTTP_404_NOT_FOUND)


class AnalysisSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра сессий анализов"""

    serializer_class = AnalysisSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AnalysisSession.objects.filter(user=self.request.user)

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        """Получить результаты анализа"""
        try:
            session = self.get_object()

            if session.processing_status != "completed":
                return Response(
                    {"error": _("Анализ еще не завершен"), "status": session.processing_status},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                medical_data = session.medical_data
                decrypted_data = medical_data.decrypt_data()

                if decrypted_data is None:
                    return Response(
                        {"error": _("Ошибка расшифровки данных")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                response_data = {
                    "session_id": session.id,
                    "analysis_type": medical_data.analysis_type,
                    "analysis_date": medical_data.analysis_date,
                    "parsed_data": decrypted_data.get("parsed_data", {}),
                    "processing_info": decrypted_data.get("processing_info", {}),
                }

                # Не возвращаем сырой текст в API (только для отладки)
                if request.user.is_staff:
                    response_data["raw_text"] = decrypted_data.get("raw_text", "")

                # Логируем доступ к данным
                SecurityLog.objects.create(
                    user=request.user,
                    action="DATA_ACCESS",
                    details=_(f"Доступ к результатам анализа, сессия: {session.id}"),
                    ip_address=get_client_ip(request),
                )

                return Response(response_data)

            except MedicalData.DoesNotExist:
                return Response({"error": _("Данные анализа не найдены")}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Ошибка получения результатов анализа: {e}")
            return Response({"error": _("Ошибка получения данных")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicalDataViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра медицинских данных"""

    serializer_class = MedicalDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MedicalData.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def timeline(self, request):
        """Получить временную линию всех анализов"""
        medical_data = self.get_queryset().order_by("-analysis_date")

        timeline = []
        for data in medical_data:
            decrypted = data.decrypt_data()
            if decrypted:
                timeline.append(
                    {
                        "id": data.pk,
                        "date": data.analysis_date,
                        "type": data.analysis_type,
                        "parsed_data": decrypted.get("parsed_data", {}),
                        "session_id": data.session.id,
                    }
                )

        return Response({"count": len(timeline), "results": timeline})

    @action(detail=False, methods=["get"])
    def by_type(self, request):
        """Получить анализы по типу"""
        analysis_type = request.query_params.get("type")

        if not analysis_type:
            return Response({"error": _("Не указан тип анализа")}, status=status.HTTP_400_BAD_REQUEST)

        medical_data = self.get_queryset().filter(analysis_type=analysis_type).order_by("-analysis_date")

        results = []
        for data in medical_data:
            decrypted = data.decrypt_data()
            if decrypted:
                results.append(
                    {
                        "id": data.pk,
                        "date": data.analysis_date,
                        "parsed_data": decrypted.get("parsed_data", {}),
                        "session_id": data.session.id,
                    }
                )

        return Response({"type": analysis_type, "count": len(results), "results": results})

    @action(detail=False, methods=["get"])
    def compare(self, request):
        """Сравнить два анализа"""
        id1 = request.query_params.get("id1")
        id2 = request.query_params.get("id2")

        if not id1 or not id2:
            return Response({"error": _("Не указаны ID анализов для сравнения")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data1 = self.get_queryset().get(id=id1)
            data2 = self.get_queryset().get(id=id2)

            decrypted1 = data1.decrypt_data()
            decrypted2 = data2.decrypt_data()

            if not decrypted1 or not decrypted2:
                return Response({"error": _("Ошибка расшифровки данных")}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            comparison = {
                "analysis1": {
                    "id": data1.pk,
                    "date": data1.analysis_date,
                    "type": data1.analysis_type,
                    "data": decrypted1.get("parsed_data", {}),
                },
                "analysis2": {
                    "id": data2.pk,
                    "date": data2.analysis_date,
                    "type": data2.analysis_type,
                    "data": decrypted2.get("parsed_data", {}),
                },
                "differences": self._calculate_differences(
                    decrypted1.get("parsed_data", {}), decrypted2.get("parsed_data", {})
                ),
            }

            return Response(comparison)

        except MedicalData.DoesNotExist:
            return Response({"error": _("Один из анализов не найден")}, status=status.HTTP_404_NOT_FOUND)

    def _calculate_differences(self, data1, data2):
        """Вычислить разности между показателями"""
        differences = {}

        for key in set(data1.keys()) | set(data2.keys()):
            val1 = data1.get(key)
            val2 = data2.get(key)

            if val1 is not None and val2 is not None:
                try:
                    diff = float(val2) - float(val1)
                    percent_change = (diff / float(val1)) * 100 if val1 != 0 else 0
                    differences[key] = {
                        "absolute_change": diff,
                        "percent_change": round(percent_change, 2),
                        "trend": "up" if diff > 0 else "down" if diff < 0 else "stable",
                    }
                except (ValueError, TypeError):
                    differences[key] = {"note": _("Невозможно сравнить значения")}

        return differences


class SecurityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра логов безопасности (только для администраторов)"""

    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return SecurityLog.objects.all()

    @action(detail=False, methods=["get"])
    def user_activity(self, request):
        """Получить активность конкретного пользователя"""
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response({"error": _("Не указан user_id")}, status=status.HTTP_400_BAD_REQUEST)

        logs = SecurityLog.objects.filter(user_id=user_id).order_by("-timestamp")

        activities = []
        for log in logs:
            activities.append(
                {"timestamp": log.timestamp, "action": log.action, "details": log.details, "ip_address": log.ip_address}
            )

        return Response({"user_id": user_id, "activity_count": len(activities), "activities": activities})
