"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from bounties import views as bounty_views

urlpatterns = [
    path("", bounty_views.home, name="home"),
    path("login/", bounty_views.LoginView.as_view(), name="login"),
    path("wanted/", bounty_views.WantedPersonListView.as_view(), name="wanted-list"),
    path(
        "wanted/nouveau/",
        bounty_views.WantedCreateView.as_view(),
        name="wanted-create",
    ),
    path(
        "wanted/<int:pk>/",
        bounty_views.WantedPersonDetailView.as_view(),
        name="wanted-detail",
    ),
    path("missions/", bounty_views.MissionListView.as_view(), name="mission-list"),
    path(
        "missions/nouvelle/",
        bounty_views.MissionCreateView.as_view(),
        name="mission-create",
    ),
    path("admin/", admin.site.urls),
    path("api/", include("bounties.urls")),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
