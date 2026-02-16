from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.connectivitySerializer.vendorSerializer import (
    VendorSerializer,
)


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
        Notification.objects.create(
            title="Vendor",
            description=f"A new Vendor named '{serializer.validated_data.get('profileName')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Vendor",
            action=f"Vendor '{serializer.validated_data.get('profileName')}' created.",
            createdBy=user,
            updatedBy=user,
        )

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
        Notification.objects.create(
            title="Vendor",
            description=f"A Vendor named '{serializer.validated_data.get('profileName')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Vendor",
            action=f"Vendor '{serializer.validated_data.get('profileName')}' updated.",
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
            title="Vendor",
            description=f"A Vendor named '{instance.profileName}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Vendor",
            action=f"Vendor '{instance.profileName}' deleted.",
            createdBy=user,
            updatedBy=user,
        )
