import json
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.csvDownloadHelper import start_csv_export
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from squadServices.models.network import Network
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.users import UserLog
from squadServices.serializer.countrySerializer import (
    CountrySerializer,
    CurrencySerializer,
    EntitySerializer,
    StateSerializer,
    TimeZoneSerializer,
)

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.serializer.networkSerializer import NetworkSerializer


class NetworkFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    MNC = django_filters.CharFilter(lookup_expr="icontains")

    countryName = django_filters.CharFilter(
        field_name="country__name", lookup_expr="icontains"
    )

    class Meta:
        model = Network
        fields = ["name", "countryName", "MNC"]


class NetworkViewSet(viewsets.ModelViewSet):
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = NetworkFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return Network.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = Network.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError(
                {"error": "Network for the selected country already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="Network",
            description=f"A new Network named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Network ",
            action=f"Network '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Network.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Network with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="Network",
            description=f"A Network named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Network ",
            action=f"Network '{serializer.validated_data.get('name')}' updated.",
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
            title="Network",
            description=f"A Network named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Network ",
            action=f"Network '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )
