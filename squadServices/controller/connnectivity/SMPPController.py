from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.connectivityModel.smpp import SMPP

from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.serializer.connectivitySerializer.SMPPSerializer import (
    SMPPSerializer,
)


class SMPPFilter(django_filters.FilterSet):
    smppHost = django_filters.CharFilter(lookup_expr="icontains")
    smppPort = django_filters.NumberFilter()
    systemID = django_filters.CharFilter(lookup_expr="icontains")
    smtpUser = django_filters.CharFilter(lookup_expr="icontains")
    bindMode = django_filters.CharFilter(lookup_expr="icontains")
    sourceTON = django_filters.NumberFilter()
    destTON = django_filters.NumberFilter()
    sourceNPI = django_filters.NumberFilter()
    destNPI = django_filters.NumberFilter()
    createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = SMPP
        fields = [
            "smppHost",
            "smppPort",
            "systemID",
            "smtpUser",
            "bindMode",
            "sourceTON",
            "destTON",
            "sourceNPI",
            "destNPI",
            "createdAt",
        ]


class SMPPViewSet(viewsets.ModelViewSet):
    serializer_class = SMPPSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = SMPPFilter

    def retrieve(self, request, *args, **kwargs):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return SMPP.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        systemID = serializer.validated_data.get("systemID")
        exist = SMPP.objects.filter(systemID__iexact=systemID, isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "SMPP with this systemID already exists."})
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        systemID = serializer.validated_data.get("systemID")
        if systemID != serializer.instance.systemID:
            exist = SMPP.objects.filter(systemID__iexact=systemID, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "SMPP with the same systemID already exists."}
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
