from django.contrib.auth import views as auth_views
from django.urls import path

from portal import views


urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="portal/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.index, name="index"),
    path("tools/volumes/", views.volumes, name="volumes"),
    path("tools/quotas/", views.quota_manager, name="quotas"),
    path("tools/accounts/", views.account_lookup, name="accounts"),
    path("tools/wwn/", views.wwn_lookup, name="wwn_lookup"),
    path(
        "api/accounts/<str:project_id>/",
        views.account_details_api,
        name="account_details_api",
    ),
]
