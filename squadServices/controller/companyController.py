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
from django.db.models import Q

import csv


class CompanyCategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = CompanyCategory
        fields = ["name"]


class CompanyCategoryViewSet(viewsets.ModelViewSet):
    queryset = CompanyCategory.objects.all()
    serializer_class = CompanyCategorySerializer
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
            exist = CompanyCategory.objects.filter(name=name, isDeleted=False)
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
            exist = CompanyStatus.objects.filter(name=name, isDeleted=False)
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


class ExtendedFilterSet(django_filters.FilterSet):
    """
    Base FilterSet that adds 'Not Equals' (for all) and 'Does Not Contain' (for text)
    capabilities to fields defined in the Meta class.
    """

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)

        # Dynamically add negative filters, but ONLY for the 'exact' lookups
        # This prevents creating duplicate/redundant filters for range/gt/lt/icontains fields
        for field_name, field in self.base_filters.items():

            # Only extend the "base" fields (where lookup_expr is exact or default)
            if getattr(field, "lookup_expr", "exact") == "exact":

                # 1. Add "Not Equals" (__ne) to almost all types
                if not isinstance(
                    field, (django_filters.BooleanFilter, django_filters.BaseCSVFilter)
                ):
                    self.filters[f"{field_name}__ne"] = self._copy_filter(
                        field, method="filter_not_equals", label_suffix="Not Equals"
                    )

                # 2. Add "Does Not Contain" (__not_contains) ONLY to Text fields
                if isinstance(field, django_filters.CharFilter):
                    self.filters[f"{field_name}__not_contains"] = self._copy_filter(
                        field,
                        method="filter_does_not_contain",
                        label_suffix="Does Not Contain",
                    )

    def _copy_filter(self, original_field, method, label_suffix):
        """Helper to copy a filter configuration but change the method."""
        new_filter = type(original_field)(
            field_name=original_field.field_name,
            method=method,
            label=f"{original_field.label or original_field.field_name} {label_suffix}",
        )
        # CRITICAL FIX: Manually bind the filter to the current FilterSet instance.
        # Without this, string methods (like "filter_not_equals") fail because the
        # filter doesn't know who its parent is.
        new_filter.parent = self
        return new_filter

    def filter_not_equals(self, queryset, name, value):
        """Excludes exact matches"""
        # The 'name' argument passed here is the MODEL FIELD NAME (e.g. 'shortName'),
        # not the filter name, because _copy_filter explicitly sets field_name.
        # So we do NOT need to slice it (name[:-4] was causing 'shortName' -> 'short').

        # FIX: Strip whitespace from value to handle "GECKO " vs "GECKO" mismatches
        if isinstance(value, str):
            value = value.strip()

        return queryset.exclude(**{name: value})

    def filter_does_not_contain(self, queryset, name, value):
        """Excludes partial matches"""
        # The 'name' argument passed here is the MODEL FIELD NAME.
        # Ensure we target the icontains lookup for the exclusion
        lookup = f"{name}__icontains"
        return queryset.exclude(**{lookup: value})


class CompanyFilter(ExtendedFilterSet):
    search = django_filters.CharFilter(method="dynamic_search")

    # 👇 whitelist allowed searchable fields
    ALLOWED_SEARCH_FIELDS = {
        "name": "name__icontains",
        "shortName": "shortName__icontains",
        "phone": "phone__icontains",
        "companyEmail": "companyEmail__icontains",
        "supportEmail": "supportEmail__icontains",
        "billingEmail": "billingEmail__icontains",
        "ratesEmail": "ratesEmail__icontains",
        "lowBalanceAlertEmail": "lowBalanceAlertEmail__icontains",
        "address": "address__icontains",
        "referencNumber": "referencNumber__icontains",
        "vatNumber": "vatNumber__icontains",
        "category": "category__name__icontains",
        "status": "status__name__icontains",
        "currency": "currency__name__icontains",
        "timeZone": "timeZone__name__icontains",
        "businessEntity": "businessEntity__name__icontains",
    }

    def dynamic_search(self, queryset, name, value):
        request = self.request
        fields_param = request.query_params.get("search_fields")

        # Default → global search
        if not fields_param:
            fields = self.ALLOWED_SEARCH_FIELDS.values()
        else:
            fields = [
                self.ALLOWED_SEARCH_FIELDS[f.strip()]
                for f in fields_param.split(",")
                if f.strip() in self.ALLOWED_SEARCH_FIELDS
            ]

        q = Q()
        for lookup in fields:
            q |= Q(**{lookup: value})

        return queryset.filter(q)

    class Meta:
        model = Company
        fields = []  # filtering done manually


# class CompanyFilter(ExtendedFilterSet):
#     # Keep your global search
#     search = django_filters.CharFilter(method="global_search")

#     class Meta:
#         model = Company
#         # Define the fields and their allowed standard lookups
#         fields = {
#             # TEXT FIELDS: Support Equals, Contains, Is Empty
#             "name": ["exact", "icontains", "isnull"],
#             "shortName": ["exact", "icontains", "isnull"],
#             "phone": ["exact", "icontains"],
#             "companyEmail": ["exact", "icontains"],
#             "supportEmail": ["exact", "icontains"],
#             "billingEmail": ["exact", "icontains"],
#             "ratesEmail": ["exact", "icontains"],
#             "lowBalanceAlertEmail": ["exact", "icontains"],
#             "address": ["exact", "icontains"],
#             "referencNumber": ["exact", "icontains"],
#             "vatNumber": ["exact", "icontains"],
#             # RELATIONSHIP FIELDS:
#             "category__name": ["exact", "icontains"],
#             "status__name": ["exact", "icontains"],
#             "currency__name": ["exact", "icontains"],
#             "timeZone__name": ["exact", "icontains"],
#             "businessEntity__name": ["exact", "icontains"],
#             # NUMERIC FIELDS: Support Equals, GT, LT, Range (Between)
#             "customerCreditLimit": ["exact", "gt", "lt", "range", "isnull"],
#             "vendorCreditLimit": ["exact", "gt", "lt", "range"],
#             "balanceAlertAmount": ["exact", "gt", "lt", "range"],
#             # DATE FIELDS: Support Exact, Range (Between), GT, LT
#             "createdAt": ["exact", "range", "gt", "lt"],
#             # BOOLEAN FIELDS
#             "onlinePayment": ["exact"],
#             "companyBlocked": ["exact"],
#             "allowWhiteListedCards": ["exact"],
#             "sendDailyReports": ["exact"],
#             "allowNetting": ["exact"],
#             "showHlrApi": ["exact"],
#             "enableVendorPanel": ["exact"],
#         }

#     def global_search(self, queryset, name, value):
#         return queryset.filter(
#             Q(name__icontains=value)
#             | Q(shortName__icontains=value)
#             | Q(phone__icontains=value)
#             | Q(companyEmail__icontains=value)
#             | Q(supportEmail__icontains=value)
#             | Q(billingEmail__icontains=value)
#             | Q(ratesEmail__icontains=value)
#             | Q(lowBalanceAlertEmail__icontains=value)
#             | Q(referencNumber__icontains=value)
#             | Q(vatNumber__icontains=value)
#             | Q(address__icontains=value)
#             | Q(category__name__icontains=value)
#             | Q(status__name__icontains=value)
#             | Q(currency__name__icontains=value)
#             | Q(timeZone__name__icontains=value)
#             | Q(businessEntity__name__icontains=value)
#         )


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
            exist = Company.objects.filter(name=name, isDeleted=False)
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
