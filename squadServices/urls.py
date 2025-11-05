"""SmartGateway URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from squadServices.controller.campaignController import CampaignContactBulkCreateAPIView
from squadServices.controller.user import (
    ChangePasswordView,
    EditUserView,
    LoginView,
    RegisterView,
)
from squadServices.controller.views import NavItemViewSet, NavUserRelationViewSet, hello


urlpatterns = [
    path("hello/", hello, name="hello"),

    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("user/edit/<int:pk>/", EditUserView.as_view(), name="edit-user"),
    path("changePassword/", ChangePasswordView.as_view(), name="changePassword"),



    path(
        "navItem/",
        NavItemViewSet.as_view(
            {
                "get": "list",
                "post": "create",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "navUserRelation/",
        NavUserRelationViewSet.as_view(
            {
                "get": "list",
                "post": "create",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "navUserRelation/createLabel/",
        NavUserRelationViewSet.as_view({"post": "createSidebar"}),
    ),
    path(
        "navUserRelation/getByUserType/<str:userType>",
        NavUserRelationViewSet.as_view({"get": "getByUserType"}),
    ),
    path(
        "navUserRelation/bulk-update/",
        NavUserRelationViewSet.as_view({"patch": "bulk_partial_update"}),
    ),
    


    path(
        'campaignContact/bulk-create/',
        CampaignContactBulkCreateAPIView.as_view(),
        name='campaignContact-bulk-create',
    )



]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
