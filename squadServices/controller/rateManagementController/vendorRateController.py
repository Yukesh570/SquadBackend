from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.rateManagementModel.vendorRate import VendorRate

from squadServices.models.users import UserLog
from squadServices.serializer.roleManagementSerializer.vendorRateSerializer import (
    VendorRateSerializer,
)


class VendorRateFilter(django_filters.FilterSet):
    # countryName = django_filters.CharFilter(
    #     field_name="country__name", lookup_expr="icontains"
    # )
    # ratePlan = django_filters.CharFilter(lookup_expr="icontains")
    # network = django_filters.CharFilter(lookup_expr="icontains")

    # currencyCode = django_filters.CharFilter(lookup_expr="icontains")
    # timeZone = django_filters.CharFilter(lookup_expr="icontains")
    # MCC = django_filters.CharFilter(lookup_expr="icontains")
    # MNC = django_filters.CharFilter(lookup_expr="icontains")
    # countryCode = django_filters.CharFilter(lookup_expr="icontains")
    # rate = django_filters.NumberFilter()
    # createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = VendorRate
        fields = {
            "ratePlan": ["exact", "icontains", "isnull"],
            "country": ["exact", "icontains", "isnull"],
            "currencyCode": ["exact", "icontains", "isnull"],
            "timeZone": ["exact", "icontains", "isnull"],
            "MCC": ["exact", "icontains", "isnull"],
            "rate": ["exact", "gt", "lt", "range", "isnull"],
            "MNC": ["exact", "icontains", "isnull"],
            "countryCode": ["exact", "icontains", "isnull"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class VendorRateViewSet(viewsets.ModelViewSet):
    serializer_class = VendorRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = VendorRateFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return VendorRate.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        ratePlan = serializer.validated_data.get("ratePlan")
        exist = VendorRate.objects.filter(ratePlan__iexact=ratePlan, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "VendorRate with this ratePlan already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="VendorRate",
            description=f"A new VendorRate named '{serializer.validated_data.get('ratePlan')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" VendorRate ",
            action=f"VendorRate '{serializer.validated_data.get('ratePlan')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        ratePlan = serializer.validated_data.get("ratePlan")
        if ratePlan != serializer.instance.ratePlan:
            exist = VendorRate.objects.filter(ratePlan=ratePlan, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "VendorRate with the same ratePlan already exists."}
                )
        user = self.request.user
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="VendorRate",
            description=f"A VendorRate named '{serializer.validated_data.get('ratePlan')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" VendorRate ",
            action=f"VendorRate '{serializer.validated_data.get('ratePlan')}' updated.",
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
            title="VendorRate",
            description=f"A VendorRate named '{instance.ratePlan}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" VendorRate ",
            action=f"VendorRate '{instance.ratePlan}' deleted.",
            createdBy=user,
            updatedBy=user,
        )
