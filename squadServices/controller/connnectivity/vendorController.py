from rest_framework import viewsets, permissions

from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.action import (
    log_action_create,
    log_action_delete,
    log_action_update,
)
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from django_filters import rest_framework as filters
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


class VendorFilter(ExtendedFilterSet):

    class Meta:
        model = Vendor
        fields = {
            "company__name": ["exact", "icontains", "isnull"],
            "profileName": ["exact", "icontains", "isnull"],
            "connectionType": ["exact", "icontains", "isnull"],
            "bindStatus": ["exact", "icontains", "isnull"],
            "invoicePolicy": ["exact", "icontains", "isnull"],
            "smpp__smppHost": ["exact", "icontains", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


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
    vendor = filters.NumberFilter(field_name="vendor_id", lookup_expr="exact")

    class Meta:
        model = VendorPolicy
        fields = {
            "vendor": ["exact", "isnull"],
            "vendor__profileName": ["exact", "icontains", "isnull"],
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
        # module = self.kwargs.get("module")
        # check_permission(self, "read", module)
        return VendorPolicy.objects.filter(isDeleted=False)

    def create(self, request, *args, **kwargs):
        """
        Intercept the creation process to handle soft-deleted OneToOne records.
        """
        # module = self.kwargs.get("module")
        # check_permission(self, "write", module)

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
        # module = self.kwargs.get("module")
        user = self.request.user
        # check_permission(self, "write", module)

        instance = serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "VendorPolicy", f"{instance.vendor.profileName} Policy")

    def perform_update(self, serializer):
        # module = self.kwargs.get("module")
        # check_permission(self, "put", module)

        user = self.request.user
        instance = serializer.save(updatedBy=user)
        log_action_update(user, "VendorPolicy", f"{instance.vendor.profileName} Policy")

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to treat the URL parameter as the vendor_id
        instead of the ClientPolicy primary key.
        """
        vendor_id = kwargs.get("pk")

        # Look up the policy associated with this client_id
        instance = get_object_or_404(VendorPolicy, vendor_id=vendor_id, isDeleted=False)

        # Call perform_destroy to execute your custom soft-delete logic
        self.perform_destroy(instance)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        # module = self.kwargs.get("module")
        # check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "VendorPolicy", f"{instance.vendor.profileName} Policy")
