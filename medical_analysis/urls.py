from medical_analysis import web_views
from django.urls import path

urlpatterns = [
    # Главная и аутентификация
    path("", web_views.home, name="home"),
    path("register/", web_views.register_view, name="register"),
    path("login/", web_views.login_view, name="login"),
    path("logout/", web_views.logout_view, name="logout"),
    # Основной функционал
    path("dashboard/", web_views.dashboard, name="dashboard"),
    path("upload/", web_views.upload_file, name="upload_file"),
    path("sessions/", web_views.analysis_sessions, name="analysis_sessions"),
    path("sessions/<int:session_id>/status/", web_views.session_status, name="session_status"),
    path("results/", web_views.analysis_results, name="analysis_results"),
    path("results/<int:analysis_id>/", web_views.analysis_detail, name="analysis_detail"),
    path("compare/", web_views.compare_analyses, name="compare_analyses"),
    # Управление данными
    path("analysis/<int:analysis_id>/delete/", web_views.delete_analysis, name="delete_analysis"),
    path("export/", web_views.export_data, name="export_data"),
    # Настройки
    path("profile/", web_views.profile_settings, name="profile_settings"),
    path("partials/recent-sessions/", web_views.recent_sessions_partial, name="recent_sessions_partial"),
    # Изменение анализов по времени
    path("trends/", web_views.analysis_trends, name="analysis_trends"),
    path("trends/data/", web_views.trends_data, name="trends_data_all"),
    path("trends/data/<str:analysis_type>/", web_views.trends_data, name="trends_data"),
]
