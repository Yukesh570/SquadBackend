from rest_framework import viewsets, permissions

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

from squadServices.models.notificationModel.notification import Notification
from squadServices.models.operators.operators import Operators

from squadServices.models.users import UserLog
from squadServices.serializer.operatorSerailizer.operatorSerializer import (
    OperatorSerializer,
)


class OperatorFilter(django_filters.FilterSet):
    countryName = django_filters.CharFilter(
        field_name="country__name", lookup_expr="icontains"
    )
    name = django_filters.CharFilter(lookup_expr="icontains")

    MNC = django_filters.CharFilter(lookup_expr="icontains")
    createdAt = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Operators
        fields = [
            "countryName",
            "name",
            "MNC",
            "createdAt",
        ]


class OperatorViewSet(viewsets.ModelViewSet):
    serializer_class = OperatorSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = OperatorFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return Operators.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = Operators.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "Operators with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "Operator", serializer.validated_data.get("name"))

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Operators.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Operators with the same name already exists."}
                )
        user = self.request.user
        serializer.save(updatedBy=user)
        log_action_update(user, "Operator", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Operator", instance.name)
