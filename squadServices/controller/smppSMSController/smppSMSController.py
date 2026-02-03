import json
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.csvDownloadHelper import start_csv_export
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from squadServices.models.smpp.smppSMS import SMSMessage
from squadServices.serializer.smppSMSSerializer import smppSMSSerializer

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
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
