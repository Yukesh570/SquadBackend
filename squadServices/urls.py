from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from squadServices.controller.campaignController import CampaignContactViewSet, CampaignViewSet, TemplateViewSet
from squadServices.controller.companyController import CompanyCategoryViewSet, CompanyStatusViewSet, CompanyViewSet
from squadServices.controller.countryController import CountryViewSet, CurrencyViewSet, EntityViewSet, StateViewSet, TimeZoneViewSet
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
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("user/edit/<int:pk>/", EditUserView.as_view(), name="edit-user"),
    path("changePassword/", ChangePasswordView.as_view(), name="changePassword"),
    path(
        "navItem/<str:module>/",
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
    # path(
    #     "navItem/<str:module>/",
    #     NavItemViewSet.as_view(
    #         {
    #             "post": "create",
    #         }
    #     ),
    # ),
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
        "campaign/<str:module>/<int:pk>/",
        CampaignViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="campaign",
    ),
 
    path(
        "campaignContact/<str:module>/<int:pk>/",
        CampaignContactViewSet.as_view({ "get": "list"}),
        name="campaignContact",
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
    path(
        "country/<str:module>/",
        CountryViewSet.as_view(
            {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "country/<str:module>/<int:pk>/",
        CountryViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "state/<str:module>/",
        StateViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "state/<str:module>/<int:pk>/",
        StateViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),

    
    path(
        "currency/<str:module>/",
        CurrencyViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "currency/<str:module>/<int:pk>/",
        CurrencyViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "entity/<str:module>/",
        EntityViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "entity/<str:module>/<int:pk>/",
        EntityViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "timeZone/<str:module>/",
        TimeZoneViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "timeZone/<str:module>/<int:pk>/",
        TimeZoneViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "companyCategory/<str:module>/",
        CompanyCategoryViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "companyCategory/<str:module>/<int:pk>/",
        CompanyCategoryViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "companyStatus/<str:module>/",
        CompanyStatusViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
        "companyStatus/<str:module>/<int:pk>/",
        CompanyStatusViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "company/<str:module>/",
        CompanyViewSet.as_view(
              {
                "get": "list",
                "post": "create",

            }
        ),
    ),
    path(
    "company/downloadCsv/<str:module>/",
    CompanyViewSet.as_view({"get": "start_csv_export"}),
),
    path(
    "company/csv-status/<str:module>/",
    CompanyViewSet.as_view({"get": "csv_status"}),
),
    path(
    "company/download-file/<str:module>/<str:filename>/",
    CompanyViewSet.as_view({"get": "download_file"}),
    name="company-download-file"
),
    path(
        "company/<str:module>/<int:pk>/",
        CompanyViewSet.as_view(
              {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
