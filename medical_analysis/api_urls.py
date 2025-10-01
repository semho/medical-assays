from django.urls import path, include
from rest_framework.routers import DefaultRouter

from medical_analysis import api_views

router = DefaultRouter()
router.register(r"profile", api_views.UserProfileViewSet, basename="profile")
router.register(r"sessions", api_views.AnalysisSessionViewSet, basename="sessions")
router.register(r"medical-data", api_views.MedicalDataViewSet, basename="medical-data")
router.register(r"security-logs", api_views.SecurityLogViewSet, basename="security-logs")

urlpatterns = [
    # API основные endpoints
    path("", include(router.urls)),
    # Загрузка файлов
    path("upload/", api_views.FileUploadViewSet.as_view({"post": "create"}), name="api_upload"),
    path("upload/status/", api_views.FileUploadViewSet.as_view({"get": "status"}), name="api_upload_status"),
    # Аутентификация API
    # TODO: добавить
    # path("auth/register/", api_views.RegisterAPIView.as_view(), name="api_register"),
    # path("auth/login/", api_views.LoginAPIView.as_view(), name="api_login"),
    # path("auth/logout/", api_views.LogoutAPIView.as_view(), name="api_logout"),
    # path("auth/change-password/", api_views.ChangePasswordAPIView.as_view(), name="api_change_password"),
    # # Дополнительные endpoints
    # path("stats/", api_views.UserStatsAPIView.as_view(), name="api_stats"),
    # path("trends/", api_views.TrendsAPIView.as_view(), name="api_trends"),
]
