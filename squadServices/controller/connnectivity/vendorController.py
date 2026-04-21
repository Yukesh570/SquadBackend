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

from squadServices.models.connectivityModel.verdor import Vendor, VendorPolicy
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.connectivitySerializer.vendorSerializer import (
    VendorSerializer,
)
from squadServices.serializer.vendorClientPolicySerializer import VendorPolicySerializer


class VendorFilter(django_filters.FilterSet):
    companyName = django_filters.CharFilter(
        field_name="company__name", lookup_expr="icontains"
    )
    profileName = django_filters.CharFilter(lookup_expr="icontains")
    connectionType = django_filters.CharFilter(lookup_expr="icontains")
    createdAt = django_filters.DateFromToRangeFilter()
    smppName = django_filters.CharFilter(
        field_name="smpp_smppHost", lookup_expr="icontains"
    )

    class Meta:
        model = Vendor
        fields = [
            "companyName",
            "profileName",
            "connectionType",
            "smppName",
            "createdAt",
        ]


# re
class VendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = VendorFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return Vendor.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        profileName = serializer.validated_data.get("profileName")
        exist = Vendor.objects.filter(profileName__iexact=profileName, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "Vendor with this profileName already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "Vendor", serializer.validated_data.get("profileName"))

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        profileName = serializer.validated_data.get("profileName")
        if profileName != serializer.instance.profileName:
            exist = Vendor.objects.filter(profileName=profileName, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Vendor with the same profileName already exists."}
                )
        user = self.request.user
        serializer.save(updatedBy=user)
        log_action_update(user, "Vendor", serializer.validated_data.get("profileName"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Vendor", instance.profileName)


class VendorPolicyFilter(ExtendedFilterSet):

    class Meta:
        model = VendorPolicy
        fields = {
            "vendor__profileName": ["exact", "icontains", "isnull"],
            "sourceAddrTon": ["exact", "icontains", "isnull"],
            "sourceAddrNpi": ["exact", "icontains", "isnull"],
            "destAddrTon": ["exact", "icontains", "isnull"],
            "destAddrNpi": ["exact", "icontains", "isnull"],
            "addrTon": ["exact", "icontains", "isnull"],
            "addrNpi": ["exact", "icontains", "isnull"],
            "rateTps": ["exact", "icontains", "isnull"],
            "sendQueueLimit": ["exact", "icontains", "isnull"],
            "delayTime": ["exact", "icontains", "isnull"],
            "responseTimeout": ["exact", "icontains", "isnull"],
            "enquireLinkInterval": ["exact", "icontains", "isnull"],
            "connectionTimeout": ["exact", "icontains", "isnull"],
            "connectionRetryDelay": ["exact", "icontains", "isnull"],
            "connectionRetryCount": ["exact", "icontains", "isnull"],
            "bindRetryDelay": ["exact", "icontains", "isnull"],
            "bindRetryCount": ["exact", "icontains", "isnull"],
            "connectionRecoveryDelay": ["exact", "icontains", "isnull"],
            "logLevel": ["exact", "icontains", "isnull"],
            "tlvTag": ["exact", "icontains", "isnull"],
            "tlvValue": ["exact", "icontains", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class VendorPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = VendorPolicySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = VendorPolicyFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return VendorPolicy.objects.filter(isDeleted=False)

    def create(self, request, *args, **kwargs):
        """
        Intercept the creation process to handle soft-deleted OneToOne records.
        """
        module = self.kwargs.get("module")
        check_permission(self, "write", module)

        vendor_id = request.data.get("vendor")

        if vendor_id:
            # Look for an existing policy (even if it is soft-deleted)
            existing_policy = VendorPolicy.objects.filter(vendor_id=vendor_id).first()

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
                    "VendorPolicy",
                    f"{instance.vendor.profileName} Policy (Restored)",
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)

        # 2. NORMAL CREATE: If no deleted policy exists, proceed normally
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)

        instance = serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "VendorPolicy", f"{instance.vendor.profileName} Policy")

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)

        user = self.request.user
        instance = serializer.save(updatedBy=user)
        log_action_update(user, "VendorPolicy", f"{instance.vendor.profileName} Policy")

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "VendorPolicy", f"{instance.vendor.profileName} Policy")
