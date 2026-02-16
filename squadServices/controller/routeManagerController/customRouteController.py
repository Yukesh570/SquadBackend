from rest_framework.permissions import IsAuthenticated
from squad.utils.authenticators import JWTAuthentication
from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.action import log_action_create, log_action_delete, log_action_delete, log_action_update
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.country import Country
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.routeManager.customRoute import CustomRoute
from rest_framework import viewsets

from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from squadServices.models.users import UserLog
from squadServices.serializer.routeManagerSerializer.customRouteSerializer import (
    CustomRouteSerializer,
)


class CustomRouteFilter(ExtendedFilterSet):
    # name = django_filters.CharFilter(lookup_expr="icontains")
    # orginatingCompany = django_filters.CharFilter(
    #     field_name="orginatingCompany__name", lookup_expr="icontains"
    # )

    # orginatingClient = django_filters.CharFilter(
    #     field_name="orginatingClient__name", lookup_expr="icontains"
    # )

    # country = django_filters.CharFilter(
    #     field_name="country__name", lookup_expr="icontains"
    # )

    # operator = django_filters.CharFilter(
    #     field_name="operator__name", lookup_expr="icontains"
    # )

    # terminatingCompany = django_filters.CharFilter(
    #     field_name="terminatingCompany__name", lookup_expr="icontains"
    # )
    # terminatingVendor = django_filters.CharFilter(
    #     field_name="terminatingVendor__name", lookup_expr="icontains"
    # )
    # status = django_filters.CharFilter(lookup_expr="iexact")
    # priority = django_filters.CharFilter(lookup_expr="icontains")
    # createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = CustomRoute
        fields = {
            "name": ["exact", "icontains"],
            "orginatingCompany__name": ["exact", "icontains"],
            "orginatingClient__name": ["exact", "icontains"],
            "country__name": ["exact", "icontains"],
            "operator__name": ["exact", "icontains"],
            "terminatingCompany__name": ["exact", "icontains"],
            "terminatingVendor__profileName": ["exact", "icontains"],
            "status": ["exact"],
            "priority": ["exact", "icontains"],
            "createdAt": ["exact", "gt", "lt", "range", "isnull"],
        }


class CustomRouteViewSet(viewsets.ModelViewSet):
    queryset = CustomRoute.objects.all()
    serializer_class = CustomRouteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomRouteFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return CustomRoute.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = CustomRoute.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError(
                {"error": "CustomRoute with this name already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "CustomRoute", serializer.validated_data.get("name"))

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")

        if name != serializer.instance.name:
            exist = CustomRoute.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "CustomRoute with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        log_action_update(user, "CustomRoute", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "CustomRoute", instance.name)
      