from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from squadServices.controller.campaignController import (
    CampaignContactViewSet,
    CampaignViewSet,
    TemplateViewSet,
)
from squadServices.controller.clientController.clientController import ClientViewSet
from squadServices.controller.companyController import (
    CompanyCategoryViewSet,
    CompanyStatusViewSet,
    CompanyViewSet,
)
from squadServices.controller.connnectivity.SMPPController import (
    SMPPViewSet,
)
from squadServices.controller.connnectivity.vendorController import VendorViewSet
from squadServices.controller.countryController import (
    CountryViewSet,
    CurrencyViewSet,
    EntityViewSet,
    StateViewSet,
    TimeZoneViewSet,
)
from squadServices.controller.emailController import (
    EmailHostViewSet,
    EmailTemplateViewSet,
)
from squadServices.controller.mappingSetupController.mappingSetupController import (
    MappingSetupViewSet,
)
from squadServices.controller.networkController import NetworkViewSet
from squadServices.controller.operatorController.operatorController import (
    OperatorViewSet,
)
from squadServices.controller.rateManagementController.customerRateController import (
    CustomerRateViewSet,
)
from squadServices.controller.user import (
    ChangePasswordView,
    EditUserView,
    LoginView,
    RegisterView,
    UserProfileView,
)
from squadServices.controller.views import (
    GetNavUserRelationViewSet,
    NavItemViewSet,
    NavUserRelationViewSet,
    sendMail,
)
from squadServices.helper.csvDownloadHelper import csv_status, download_file
from squadServices.controller.rateManagementController.vendorRateController import (
    VendorRateViewSet,
)
from squadServices.helper.csvUploadHelper import (
    upload_vendor_rate_csv,
    vendor_rate_import_status,
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
    path("userLog/", UserProfileView.as_view(), name="user-profile"),
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
        CampaignContactViewSet.as_view({"get": "list"}),
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
        "smpp/<str:module>/",
        SMPPViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="smpp",
    ),
    path(
        "smpp/<str:module>/<int:pk>/",
        SMPPViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="smpp",
    ),
    path(
        "vendor/<str:module>/",
        VendorViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="vendor",
    ),
    path(
        "vendor/<str:module>/<int:pk>/",
        VendorViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="vendor",
    ),
    path(
        "client/<str:module>/",
        ClientViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="client",
    ),
    path(
        "client/<str:module>/<int:pk>/",
        ClientViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="client",
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
        CompanyViewSet.as_view({"get": "csv"}),
    ),
    path(
        "country/downloadCsv/<str:module>/",
        CountryViewSet.as_view({"get": "csv"}),
    ),
    path(
        "csv-status/<str:module>/",
        csv_status,
    ),
    path(
        "download-file/<str:module>/<str:filename>/",
        download_file,
        name="download-file",
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
    path(
        "vendorRate/<str:module>/",
        VendorRateViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="vendorRate",
    ),
    path(
        "vendorRate/<str:module>/<int:pk>/",
        VendorRateViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="vendorRate",
    ),
    path(
        "customerRate/<str:module>/",
        CustomerRateViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="customerRate",
    ),
    path(
        "customerRate/<str:module>/<int:pk>/",
        CustomerRateViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="customerRate",
    ),
    path(
        "network/<str:module>/",
        NetworkViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "network/<str:module>/<int:pk>/",
        NetworkViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "mappingSetup/<str:module>/",
        MappingSetupViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "mappingSetup/<str:module>/<int:pk>/",
        MappingSetupViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path(
        "operator/<str:module>/",
        OperatorViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "operator/<str:module>/<int:pk>/",
        OperatorViewSet.as_view(
            {
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
    ),
    path("vendor-rate/import/", upload_vendor_rate_csv),
    path("vendor-rate/import/status/<str:task_id>/", vendor_rate_import_status),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
