from rest_framework import viewsets, permissions

from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.action import (
    log_action_create,
    log_action_delete,
    log_action_update,
)
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission

from django.db.models import Q

from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.clientModel.client import Client, IpWhitelist
from squadServices.models.company import Company
from squadServices.models.finanace.invoiceSetup import InvoiceSetup
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.clientSerializer.clientSerializer import (
    ClientSerializer,
    IpWhitelistSerializer,
)
from squadServices.serializer.financeSerailizer.invoiceSetupSerializer import (
    InvoiceSetupSerializer,
)


class InvoiceSetupFilter(ExtendedFilterSet):

    company = django_filters.NumberFilter()

    class Meta:
        model = InvoiceSetup
        fields = {
            "company__name": ["exact", "icontains", "isnull"],
            "billingAddressOverride": ["exact", "icontains", "isnull"],
            "businessEntity__legalEntityName": ["exact", "icontains", "isnull"],
            "invoiceFrequency": ["exact", "icontains", "isnull"],
            "isTaxApplied": ["exact", "icontains", "isnull"],
            "tax": ["exact", "icontains", "isnull"],
            "dueDays": ["exact", "gt", "lt", "range", "isnull"],
            "createdAt": ["exact", "range", "gt", "lt"],
        }


class InvoiceSetupViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSetupSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = InvoiceSetupFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return InvoiceSetup.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)

        instance = serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "InvoiceSetup", instance.company.name)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)

        user = self.request.user
        instance = serializer.save(updatedBy=user)
        log_action_update(user, "InvoiceSetup", instance.company.name)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "InvoiceSetup", instance.company.name)
