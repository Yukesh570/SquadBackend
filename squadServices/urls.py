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

from squadServices.controller.campaignController import CampaignViewSet, TemplateViewSet
from squadServices.controller.emailController import (
    EmailHostViewSet,
    EmailTemplateViewSet,
)
from squadServices.controller.user import (
    ChangePasswordView,
    EditUserView,
    LoginView,
    RegisterView,
)
from squadServices.controller.views import (
    GetNavUserRelationViewSet,
    NavItemViewSet,
    NavUserRelationViewSet,
    sendMail,
)


urlpatterns = [
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
        "navItem/<str:module>/",
        NavItemViewSet.as_view(
            {
                "post": "create",
            }
        ),
    ),
    path(
        "navItem/<str:module>/<int:pk>/",
        NavItemViewSet.as_view(
            {
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
        "navUserRelation/bulk-update/",
        NavUserRelationViewSet.as_view({"patch": "bulk_partial_update"}),
    ),
    path(
        "navUserRelationGet/",
        GetNavUserRelationViewSet.as_view({"get": "list"}),
    ),
    path(
        "navUserRelationGet/getByUserType/<str:userType>",
        GetNavUserRelationViewSet.as_view({"get": "getByUserType"}),
    ),
    path(
        "campaign/<str:module>/",
        CampaignViewSet.as_view({"post": "create", "get": "list"}),
        name="campaignContact-bulk-create",
    ),
    path(
        "template/<str:module>/",
        TemplateViewSet.as_view({"get": "list", "post": "create"}),
        name="templateCreate",
    ),
    path(
        "template/<str:module>/<int:pk>/",
        TemplateViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="templateCreate",
    ),
    path(
        "emailTemplate/<str:module>/",
        EmailTemplateViewSet.as_view({"get": "list", "post": "create"}),
        name="emailTemplateCreate",
    ),
    path(
        "emailTemplate/<str:module>/<int:pk>/",
        EmailTemplateViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="emailTemplateCreate",
    ),
    path(
        "template/",
        TemplateViewSet.as_view({"get": "list"}),
        name="templateCreate",
    ),
    path(
        "email/",
        sendMail,
        name="sendmail",
    ),
    path(
        "emailHost/<str:module>/",
        EmailHostViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="emailHost",
    ),
    path(
        "emailHost/<str:module>/<int:pk>/",
        EmailHostViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="emailHost",
    ),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
