from celery.result import AsyncResult
import os
from django.conf import settings
from django.http import FileResponse, HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.csvDownloadHelper import start_csv_export
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.company import Company, CompanyCategory, CompanyStatus
from squadServices.serializer.companySerializer import (
    CompanyCategorySerializer,
    CompanySerializer,
    CompanyStatusSerializer,
)
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.decorators import action
from django.http import StreamingHttpResponse

import csv


class CompanyCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = CompanyCategory
        fields = ["name"]


class CompanyCategoryViewSet(viewsets.ModelViewSet):
    queryset = CompanyCategory.objects.all()
    serializer_class = CompanyCategorySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyCategoryFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return CompanyCategory.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = CompanyCategory.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "CompanyCategory with this name already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = CompanyCategory.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "CompanyCategory with the same name already exists."}
                )
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class CompanyStatusFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = CompanyStatus
        fields = ["name"]


class CompanyStatusViewSet(viewsets.ModelViewSet):
    queryset = CompanyStatus.objects.all()
    serializer_class = CompanyStatusSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyStatusFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return CompanyStatus.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = CompanyStatus.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "CompanyStatus with this name already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = CompanyStatus.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "CompanyStatus with the same name already exists."}
                )
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class CompanyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    shortName = django_filters.CharFilter(lookup_expr="icontains")
    phone = django_filters.CharFilter(lookup_expr="icontains")
    companyEmail = django_filters.CharFilter(lookup_expr="icontains")
    supportEmail = django_filters.CharFilter(lookup_expr="icontains")
    billingEmail = django_filters.CharFilter(lookup_expr="icontains")
    ratesEmail = django_filters.CharFilter(lookup_expr="icontains")
    lowBalanceAlertEmail = django_filters.CharFilter(lookup_expr="icontains")

    category_name = django_filters.CharFilter(
        field_name="category__name", lookup_expr="icontains"
    )
    status_name = django_filters.CharFilter(
        field_name="status__name", lookup_expr="icontains"
    )
    currency_name = django_filters.CharFilter(
        field_name="currency__name", lookup_expr="icontains"
    )
    timeZone_name = django_filters.CharFilter(
        field_name="timeZone__name", lookup_expr="icontains"
    )
    businessEntity = django_filters.CharFilter(
        field_name="businessEntity__name", lookup_expr="icontains"
    )
    customerCreditLimit = django_filters.NumberFilter()

    vendorCreditLimit = django_filters.NumberFilter()
    balanceAlertAmount = django_filters.NumberFilter()
    referencNumber = django_filters.CharFilter(lookup_expr="icontains")
    vatNumber = django_filters.CharFilter(lookup_expr="icontains")
    address = django_filters.CharFilter(lookup_expr="icontains")
    validityPeriod = django_filters.CharFilter(lookup_expr="icontains")
    defaultEmail = django_filters.CharFilter(lookup_expr="icontains")
    onlinePayment = django_filters.BooleanFilter()
    companyBlocked = django_filters.BooleanFilter()
    allowWhiteListedCards = django_filters.BooleanFilter()
    sendDailyReports = django_filters.BooleanFilter()
    allowNetting = django_filters.BooleanFilter()
    sendMonthlyReports = django_filters.BooleanFilter()
    showHlrApi = django_filters.BooleanFilter()
    enableVendorPanel = django_filters.BooleanFilter()

    class Meta:
        model = Company
        fields = [
            "name",
            "shortName",
            "phone",
            "companyEmail",
            "supportEmail",
            "billingEmail",
            "ratesEmail",
            "lowBalanceAlertEmail",
            "category_name",
            "status_name",
            "currency_name",
            "timeZone_name",
            "businessEntity",
            "customerCreditLimit",
            "vendorCreditLimit",
            "balanceAlertAmount",
            "referencNumber",
            "vatNumber",
            "address",
            "validityPeriod",
            "defaultEmail",
            "onlinePayment",
            "companyBlocked",
            "allowWhiteListedCards",
            "sendDailyReports",
            "allowNetting",
            "sendMonthlyReports",
            "showHlrApi",
            "enableVendorPanel",
        ]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CompanyFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return Company.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = Company.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError({"error": "Company with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Company.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Company with the same name already exists."}
                )
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

    @action(detail=False, methods=["get"], url_path="downloadCsv")
    def csv(self, request, module=None):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        filtered_qs = self.filter_queryset(self.get_queryset())
        filter_dict = getattr(getattr(filtered_qs.query, "where", None), "children", [])
        return start_csv_export(
            self,
            request,
            module,
            model_name="squadServices.Company",
            fields=[
                "id",
                "name",
                "shortName",
                "phone",
                "companyEmail",
                "supportEmail",
                "billingEmail",
                "ratesEmail",
                "lowBalanceAlertEmail",
            ],
            filter_dict=filter_dict,
        )

    # @action(detail=False, methods=['get'], url_path="downloadCsv")
    # def start_csv_export(self, request, module=None):
    #     module = self.kwargs.get('module')
    #     check_permission(self, 'read', module)

    #     # Apply filters the same way DRF FilterSet does
    #     filtered_qs = self.filter_queryset(self.get_queryset())

    #     # Convert queryset filters into simple filter dict
    #     # (primary columns only – complex filters need customizing)
    #     filter_dict = filtered_qs.query.__dict__.get('where').children
    #     filters = {}
    #     for f in filter_dict:
    #         try:
    #             filters[f.lhs.target.name] = f.rhs
    #         except:
    #             pass

    #     # Start Celery Task
    #     task = export_model_csv.delay( model_name="squadServices.Company",filters=filters,fields=["id","name","shortName","phone","companyEmail","supportEmail","billingEmail","ratesEmail","lowBalanceAlertEmail",], module=module)

    #     return Response({
    #         "task_id": task.id,
    #         "status": "processing"
    #     })

    # @action(detail=False, methods=['get'], url_path="csv-status/(?P<module>[^/.]+)")
    # def csv_status(self, request, module=None):
    #     task_id = request.query_params.get("task_id")
    #     if not task_id:
    #         return Response({"error": "task_id required"}, status=400)

    #     result = AsyncResult(task_id)

    #     if result.successful():
    #         filename = result.result
    #         download_url = request.build_absolute_uri(
    #             f"/company/download-file/{module}/{filename}/"
    #         )
    #         return Response({
    #             "ready": True,
    #             "download_url": download_url
    #         })

    #     return Response({"ready": False})

    # @action(detail=False, methods=['get'], url_path="download-file/(?P<module>[^/]+)/(?P<filename>[^/]+)",authentication_classes=[],
    #     permission_classes=[AllowAny],)
    # def download_file(self, request, module, filename):
    #     file_path = os.path.join(settings.BASE_DIR, "exports", filename)

    #     if not os.path.exists(file_path):
    #         return Response({"error": "File not found"}, status=404)
    #     file_handle = open(file_path, "rb")

    #     response = FileResponse(open(file_path, "rb"), as_attachment=True)
    #     response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'
    #     response["Content-Type"] = "text/csv"
    #     def remove_file_callback(response):
    #         try:
    #             file_handle.close()
    #             os.remove(file_path)
    #         except Exception as e:
    #             print("Error deleting file:", e)

    #     response.close = lambda *args, **kwargs: (
    #         FileResponse.close(response),
    #         remove_file_callback(response),
    #     )
    #     return response

    # def get_permissions(self):
    #     # Allow anyone for download_file
    #     if self.action == "download_file":
    #         return [AllowAny()]
    #     return super().get_permissions()
