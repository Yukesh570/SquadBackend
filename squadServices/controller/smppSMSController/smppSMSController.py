from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from squad.utils.authenticators import JWTAuthentication
from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.smpp.smppSMS import (
    DLREvent,
    MessageAttempt,
    SMSMessage,
    SMSMessagePart,
)
from squadServices.serializer.smppSmsSerializer.smppSMSSerializer import (
    DLREventSerializer,
    MessageAttemptSerializer,
    SMSMessagePartSerializer,
    smppSMSSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
import django_filters


class SmppSMSFilter(django_filters.FilterSet):
    destination = django_filters.CharFilter(lookup_expr="icontains")
    status = django_filters.CharFilter(lookup_expr="icontains")

    systemId = django_filters.CharFilter(lookup_expr="icontains")

    clientName = django_filters.CharFilter(
        field_name="client__name", lookup_expr="icontains"
    )
    vendorName = django_filters.CharFilter(
        field_name="vendor__name", lookup_expr="icontains"
    )
    smppName = django_filters.CharFilter(
        field_name="smpp__name", lookup_expr="icontains"
    )

    class Meta:
        model = SMSMessage
        fields = [
            "destination",
            "status",
            "systemId",
            "clientName",
            "vendorName",
            "smppName",
        ]


class SmppSMSViewSet(viewsets.ModelViewSet):
    queryset = SMSMessage.objects.all()
    serializer_class = smppSMSSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = SmppSMSFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return SMSMessage.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)

        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)

        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class SMSMessagePartFilter(ExtendedFilterSet):
    # Keep your global search
    #     search = django_filters.CharFilter(method="global_search")

    class Meta:
        model = SMSMessagePart
        # Define the fields and their allowed standard lookups
        fields = {
            # TEXT FIELDS: Support Equals, Contains, Is Empty
            "message__destination": ["exact", "icontains", "isnull"],
            "part_no": ["exact", "icontains", "isnull"],
            "part_total": ["exact", "icontains"],
            "udh_ref": ["exact", "icontains"],
            "udh_hex": ["exact", "icontains"],
            "submit_status": ["exact", "icontains"],
            "vendor_msg_id": ["exact", "icontains"],
            "vendor_submit_status": ["exact", "icontains"],
            "submit_attempts": ["exact", "icontains"],
            "submitted_at": ["exact", "gt", "lt", "range", "isnull"],
            "sent_at": ["exact", "gt", "lt", "range"],
            "failed_at": ["exact", "gt", "lt", "range"],
            "created_at": ["exact", "range", "gt", "lt"],
        }


class SMSMessagePartViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for SMS segments to prevent alteration of split history."""

    queryset = SMSMessagePart.objects.select_related("message").all()
    serializer_class = SMSMessagePartSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = SMSMessagePartFilter

    def get_queryset(self):
        module = self.kwargs.get(
            "module", "sms_reports"
        )  # Fallback to a default module name if not provided
        check_permission(self, "read", module)
        return super().get_queryset()


class MessageAttemptFilter(ExtendedFilterSet):
    # Keep your global search
    #     search = django_filters.CharFilter(method="global_search")

    class Meta:
        model = MessageAttempt
        # Define the fields and their allowed standard lookups
        fields = {
            # TEXT FIELDS: Support Equals, Contains, Is Empty
            "message__destination": ["exact", "icontains", "isnull"],
            "attempt_number": ["exact", "icontains", "isnull"],
            "provider": ["exact", "icontains"],
            "provider_message_id": ["exact", "icontains"],
            "status": ["exact", "icontains"],
            "started_at": ["exact", "gt", "lt", "range"],
            "completed_at": ["exact", "gt", "lt", "range"],
        }


class MessageAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for vendor submission attempts."""

    queryset = MessageAttempt.objects.select_related("message", "segment").all()
    serializer_class = MessageAttemptSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = MessageAttemptFilter

    def get_queryset(self):
        module = self.kwargs.get("module", "sms_reports")
        check_permission(self, "read", module)
        return super().get_queryset()


class DLREventFilter(ExtendedFilterSet):
    # Keep your global search
    #     search = django_filters.CharFilter(method="global_search")

    class Meta:
        model = DLREvent
        # Define the fields and their allowed standard lookups
        fields = {
            # TEXT FIELDS: Support Equals, Contains, Is Empty
            "message__destination": ["exact", "icontains", "isnull"],
            "provider_message_id": ["exact", "icontains", "isnull"],
            "event_type": ["exact", "icontains"],
            "segment_number": ["exact", "icontains"],
            "status_code": ["exact", "icontains"],
            "segment_number": ["exact", "icontains"],
            "received_at": ["exact", "gt", "lt", "range"],
        }


class DLREventViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for Delivery Receipts to preserve compliance and billing logs."""

    queryset = DLREvent.objects.select_related("message", "segment").all()
    serializer_class = DLREventSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = DLREventFilter

    def get_queryset(self):
        module = self.kwargs.get("module", "sms_reports")
        check_permission(self, "read", module)
        return super().get_queryset()
