from rest_framework import viewsets, permissions

from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission

from django.db.models import Q

from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.clientModel.client import Client, IpWhitelist
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.clientSerializer.clientSerializer import (
    ClientSerializer,
    IpWhitelistSerializer,
)


class ClientFilter(ExtendedFilterSet):

    # smtpUser = django_filters.CharFilter(lookup_expr="icontains")
    # name = django_filters.CharFilter(lookup_expr="icontains")
    # status = django_filters.CharFilter(lookup_expr="icontains")
    # route = django_filters.CharFilter(lookup_expr="icontains")
    # paymentTerms = django_filters.CharFilter(lookup_expr="icontains")
    # creditLimit = django_filters.CharFilter(lookup_expr="icontains")
    # balanceAlertAmount = django_filters.CharFilter(lookup_expr="icontains")
    # allowNetting = django_filters.CharFilter(lookup_expr="icontains")
    # createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Client
        fields = {
            "name": ["exact", "icontains", "isnull"],
            "status": ["exact", "icontains", "isnull"],
            "route": ["exact", "icontains", "isnull"],
            "smppUsername": ["exact", "icontains", "isnull"],
            "paymentTerms": ["exact", "icontains", "isnull"],
            "creditLimit": ["exact", "gt", "lt", "range", "isnull"],
            "balanceAlertAmount": ["exact", "gt", "lt", "range", "isnull"],
            "allowNetting": ["exact"],
            "createdAt": ["exact", "range", "gt", "lt"],
        }


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return Client.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        smppUsername = serializer.validated_data.get("smppUsername")

        exist = Client.objects.filter(
            Q(name__iexact=name) | Q(smppUsername__iexact=smppUsername), isDeleted=False
        )
        if exist.exists():
            raise ValidationError(
                {"error": "Client with this name or smppUsername already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="Client",
            description=f"A new Client named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title="Client",
            action=f"Client '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Client.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Client with the same name already exists."}
                )
        user = self.request.user
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="Client",
            description=f"A Client named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title="Client",
            action=f"Client '{serializer.validated_data.get('name')}' updated.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        Notification.objects.create(
            title="Client",
            description=f"A Client named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title="Client",
            action=f"Client '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )


class IpWhitelistFilter(django_filters.FilterSet):
    ip = django_filters.CharFilter(lookup_expr="icontains")
    clientName = django_filters.CharFilter(
        field_name="client__name", lookup_expr="icontains"
    )

    createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = IpWhitelist
        fields = [
            "ip",
            "clientName",
            "createdAt",
        ]


class IpWhiteListViewSet(viewsets.ModelViewSet):
    serializer_class = IpWhitelistSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = IpWhitelistFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return IpWhitelist.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)

        user = self.request.user
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
