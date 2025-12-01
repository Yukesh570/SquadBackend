from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.connectivityModel.connectivity import Connectivity
from squadServices.serializer.connectivitySerializer.connectivitySerializer import (
    ConnectivitySerializer,
)
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters


class ConnectivityFilter(django_filters.FilterSet):
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
        model = Connectivity
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


class ConnectivityViewSet(viewsets.ModelViewSet):
    serializer_class = ConnectivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ConnectivityFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return Connectivity.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        systemID = serializer.validated_data.get("systemID")
        exist = Connectivity.objects.filter(systemID__iexact=systemID, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "Connectivity with this systemID already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        systemID = serializer.validated_data.get("systemID")
        if systemID != serializer.instance.systemID:
            exist = Connectivity.objects.filter(
                systemID__iexact=systemID, isDeleted=False
            )
            if exist.exists():
                raise ValidationError(
                    {"error": "Connectivity with the same systemID already exists."}
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
