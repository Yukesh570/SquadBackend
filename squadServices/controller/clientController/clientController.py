import random
from rest_framework import viewsets, permissions

from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.controller.user import User
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
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.clientSerializer.clientSerializer import (
    ClientSerializer,
    IpWhitelistSerializer,
    PuskarClientSerializer,
)
from rest_framework.permissions import AllowAny


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
    company = django_filters.NumberFilter()

    class Meta:
        model = Client
        fields = {
            "name": ["exact", "icontains", "isnull"],
            "status": ["exact", "icontains", "isnull"],
            "route": ["exact", "icontains", "isnull"],
            "company__name": ["exact", "icontains", "isnull"],
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
        log_action_create(user, "Client", serializer.validated_data.get("name"))

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
        log_action_update(user, "Client", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Client", instance.name)


class PuskarClientViewSet(viewsets.ModelViewSet):
    serializer_class = PuskarClientSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    permission_classes = [AllowAny]

    filterset_class = ClientFilter

    def perform_create(self, serializer):
        name = serializer.validated_data.get("name")
        smppUsername = serializer.validated_data.get("name")
        clean_name = name.replace(" ", "")
        safe_smpp_username = clean_name[:15]
        # 2. Enforce the 8-character limit for Password
        # We take the first 4 letters of the name, and append 4 random numbers
        prefix = clean_name[:4]  # Gets up to 4 chars
        random_suffix = random.randint(1000, 9999)  # 4 digits

        # This guarantees the password is exactly 8 characters (or less if the name is super short)
        safe_smpp_password = f"{prefix}{random_suffix}"
        print("nam1111111111111111111111111111111111111e", name)
        exist = Client.objects.filter(
            Q(name__iexact=name) | Q(smppUsername__iexact=safe_smpp_username),
            isDeleted=False,
        )
        if exist.exists():
            raise ValidationError(
                {"error": "Client with this name or smppUsername already exists."}
            )

        clean_name = name.replace(" ", "")

        try:
            sweta_user = User.objects.get(
                username="sweta"
            )  # Adjust 'username' if your login field is different (e.g., 'email')
        except User.DoesNotExist:
            raise ValidationError(
                {
                    "error": "The default user 'sweta' could not be found in the database."
                }
            )
        serializer.save(
            ratePlanName="Puskar Default Rate Plan",
            company=Company.objects.first(),
            balanceAlertAmount=0,
            allowNetting=False,
            enableDlr=True,
            status="Active",
            smppUsername=safe_smpp_username,
            smppPassword=safe_smpp_password,
            createdBy=sweta_user,  # Updated
            updatedBy=sweta_user,
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
