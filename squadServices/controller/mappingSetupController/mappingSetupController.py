from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.mappingSetup.mappingSetup import MappingSetup

from squadServices.serializer.mappingSetupSerailzer.mappingSetupSerailzer import (
    MappingSetupSerializer,
)


class MappingSetupFilter(django_filters.FilterSet):
    ratePlan = django_filters.CharFilter(lookup_expr="icontains")
    country = django_filters.CharFilter(lookup_expr="icontains")
    countryCode = django_filters.CharFilter(lookup_expr="icontains")
    timeZone = django_filters.CharFilter(lookup_expr="icontains")

    network = django_filters.CharFilter(lookup_expr="icontains")

    MCC = django_filters.CharFilter(lookup_expr="icontains")
    MNC = django_filters.CharFilter(lookup_expr="icontains")
    rate = django_filters.NumberFilter()

    dateTime = django_filters.CharFilter(lookup_expr="icontains")

    createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = MappingSetup
        fields = [
            "ratePlan",
            "country",
            "countryCode",
            "timeZone",
            "network",
            "MCC",
            "MNC",
            "rate",
            "dateTime",
            "createdAt",
        ]


class MappingSetupViewSet(viewsets.ModelViewSet):
    serializer_class = MappingSetupSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = MappingSetupFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return MappingSetup.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        ratePlan = serializer.validated_data.get("ratePlan")
        exist = MappingSetup.objects.filter(ratePlan__iexact=ratePlan, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "MappingSetup with this ratePlan already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        ratePlan = serializer.validated_data.get("ratePlan")
        if ratePlan != serializer.instance.ratePlan:
            exist = MappingSetup.objects.filter(ratePlan=ratePlan, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "MappingSetup with the same ratePlan already exists."}
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
