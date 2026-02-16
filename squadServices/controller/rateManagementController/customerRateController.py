from rest_framework import viewsets, permissions
from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from squadServices.models.rateManagementModel.customerRate import CustomerRate
from squadServices.serializer.roleManagementSerializer.customerRateSerializer import (
    CustomerRateSerializer,
)


class CustomerRateFilter(ExtendedFilterSet):

    class Meta:
        model = CustomerRate
        fields = {
            "country__name": ["exact", "icontains"],
            "ratePlan": ["exact", "icontains"],
            "currencyCode": ["exact", "icontains"],
            "countryCode": ["exact", "icontains"],
            "timeZone__name": ["exact", "icontains"],
            "MCC": ["exact", "icontains"],
            "MNC": ["exact", "icontains"],
            "rate": ["exact", "gt", "lt", "range", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class CustomerRateViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomerRateFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return CustomerRate.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        ratePlan = serializer.validated_data.get("ratePlan")
        exist = CustomerRate.objects.filter(ratePlan__iexact=ratePlan, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "CustomerRate with this ratePlan already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        ratePlan = serializer.validated_data.get("ratePlan")
        if ratePlan != serializer.instance.ratePlan:
            exist = CustomerRate.objects.filter(ratePlan=ratePlan, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "CustomerRate with the same ratePlan already exists."}
                )
        user = self.request.user
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
