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

from squadServices.models.clientModel.client import (
    Client,
    ClientPolicy,
    ClientSession,
    IpWhitelist,
    PuskarClient,
)
from squadServices.models.company import Company
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.clientSerializer.clientSerializer import (
    ClientSerializer,
    IpWhitelistSerializer,
    PuskarClientSerializer,
)
from rest_framework.permissions import AllowAny

from squadServices.serializer.vendorClientPolicySerializer import ClientPolicySerializer
from squadServices.serializer.vendorClientSessionSerializer import (
    ClientSessionSerializer,
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
            "bindStatus": ["exact", "icontains", "isnull"],
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

    def perform_create(self, serializer):
        name = serializer.validated_data.get("name")
        smppUsername = serializer.validated_data.get("name")
        clean_name = name.replace(" ", "")
        safe_smpp_username = clean_name[:10]
        # 2. Enforce the 8-character limit for Password
        # We take the first 4 letters of the name, and append 4 random numbers
        prefix = clean_name[:4]  # Gets up to 4 chars
        random_suffix = random.randint(1000, 9999)  # 4 digits
        random_suffix2 = random.randint(1000, 9999)  # 4 digits
        random_suffix3 = random.randint(1000, 9999)  # 4 digits

        finalDsmppUsername = f"{safe_smpp_username}{random_suffix}"
        finalFsmppUsername = f"{safe_smpp_username}{random_suffix2}"
        finalFsmppUsername = f"{safe_smpp_username}{random_suffix3}"

        # This guarantees the password is exactly 8 characters (or less if the name is super short)
        safe_smpp_password = f"{prefix}{random_suffix}"
        print("nam1111111111111111111111111111111111111e", name)
        exist = PuskarClient.objects.filter(
            Q(name__iexact=name),
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
            DsmppUsername=finalDsmppUsername,
            FsmppUsername=finalFsmppUsername,
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


class ClientPolicyFilter(ExtendedFilterSet):

    class Meta:
        model = ClientPolicy
        fields = {
            "client__name": ["exact", "icontains", "isnull"],
            "maxTps": ["exact", "icontains", "isnull"],
            "maxWindowPerSession": ["exact", "icontains", "isnull"],
            "maxWindowGlobal": ["exact", "icontains", "isnull"],
            "maxSessions": ["exact", "icontains", "isnull"],
            "idleTimeoutSec": ["exact", "icontains", "isnull"],
            "submitTimeoutSec": ["exact", "icontains", "isnull"],
            "maxQueueDepth": ["exact", "icontains", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class ClientPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = ClientPolicySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientPolicyFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return ClientPolicy.objects.filter(isDeleted=False)

    def create(self, request, *args, **kwargs):
        """
        Intercept the creation process to handle soft-deleted OneToOne records.
        """
        module = self.kwargs.get("module")
        check_permission(self, "write", module)

        client_id = request.data.get("client")

        if client_id:
            # Look for an existing policy (even if it is soft-deleted)
            existing_policy = ClientPolicy.objects.filter(client_id=client_id).first()

            if existing_policy and existing_policy.isDeleted:
                # 1. RESTORE: It exists but is deleted. Treat this POST as an UPDATE.

                # Make a mutable copy of the request data and force it to be active
                data = request.data.copy()
                data["isDeleted"] = False

                # Pass the existing instance to the serializer so DRF knows it's an update,
                # bypassing the strict OneToOne UniqueValidator error!
                serializer = self.get_serializer(
                    existing_policy, data=data, partial=True
                )
                serializer.is_valid(raise_exception=True)

                user = request.user
                # Keep original creator, update the modifier
                instance = serializer.save(
                    updatedBy=user, createdBy=existing_policy.createdBy or user
                )

                log_action_create(
                    user,
                    "ClientPolicy",
                    f"{instance.client.name} Policy (Restored)",
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)

        # 2. NORMAL CREATE: If no deleted policy exists, proceed normally
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)

        instance = serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "ClientPolicy", f"{instance.client.name} Policy")

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)

        user = self.request.user
        instance = serializer.save(updatedBy=user)
        log_action_update(user, "ClientPolicy", f"{instance.client.name} Policy")

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "ClientPolicy", f"{instance.client.name} Policy")


class ClientSessionFilter(ExtendedFilterSet):

    class Meta:
        model = ClientSession
        fields = {
            "client__name": ["exact", "icontains", "isnull"],
            "sessionId": ["exact", "icontains", "isnull"],
            "systemId": ["exact", "icontains", "isnull"],
            "bindType": ["exact", "icontains", "isnull"],
            "remoteIp": ["exact", "icontains", "isnull"],
            "remotePort": ["exact", "icontains", "isnull"],
            "status": ["exact", "icontains", "isnull"],
            "connectedAt": ["exact", "gt", "lt", "range", "isnull"],
            "boundAt": ["exact", "gt", "lt", "range", "isnull"],
            "last_activityAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class ClientSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view for ClientSession"""

    queryset = ClientSession.objects.all()
    serializer_class = ClientSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientSessionFilter

    def get_queryset(self):
        module = self.kwargs.get("module", "sms_reports")
        check_permission(self, "read", module)
        return super().get_queryset()
