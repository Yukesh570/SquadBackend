from rest_framework import viewsets, permissions

from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.action import (
    log_action_create,
    log_action_delete,
    log_action_update,
)
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.notificationModel.notification import Notification

from squadServices.models.transaction.transaction import (
    ClientTransaction,
    VendorTransaction,
)
from squadServices.models.users import UserLog
from rest_framework.viewsets import ReadOnlyModelViewSet
from squadServices.serializer.transactionSerializer.transactionSerializer import (
    ClientTransactionSerializer,
    VendorTransactionSerializer,
)


class ClientTransactionFilter(ExtendedFilterSet):
    class Meta:
        model = ClientTransaction
        fields = {
            "client__name": ["exact", "icontains"],
            "message__message_id": ["exact", "icontains"],
            "transactionType": ["exact", "icontains"],
            "description": ["exact", "icontains"],
            "segments": ["exact", "gt", "lt", "range", "isnull"],
            "ratePerSegment": ["exact", "gt", "lt", "range", "isnull"],
            "amount": ["exact", "gt", "lt", "range", "isnull"],
            "balanceSpent": ["exact", "gt", "lt", "range", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class ClientTransactionViewSet(ReadOnlyModelViewSet):
    serializer_class = ClientTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientTransactionFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return ClientTransaction.objects.filter(isDeleted=False)


class VendorTransactionFilter(ExtendedFilterSet):
    class Meta:
        model = VendorTransaction
        fields = {
            "vendor__profileName": ["exact", "icontains"],
            "message__message_id": ["exact", "icontains"],
            "transactionType": ["exact", "icontains"],
            "description": ["exact", "icontains"],
            "segments": ["exact", "gt", "lt", "range", "isnull"],
            "ratePerSegment": ["exact", "gt", "lt", "range", "isnull"],
            "amount": ["exact", "gt", "lt", "range", "isnull"],
            "balanceSpent": ["exact", "gt", "lt", "range", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class VendorTransactionViewSet(ReadOnlyModelViewSet):
    serializer_class = VendorTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientTransactionFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return VendorTransaction.objects.filter(isDeleted=False)
