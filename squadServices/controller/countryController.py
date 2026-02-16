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


class CountryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    countryCode = django_filters.CharFilter(lookup_expr="icontains")
    MCC = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Country
        fields = ["name", "countryCode", "MCC"]


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = CountryFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return Country.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = Country.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError({"error": "Country with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="Country",
            description=f"A new Country named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Country ",
            action=f"Country '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")

        if name != serializer.instance.name:
            exist = Country.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Country with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="Country",
            description=f"A Country named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Country ",
            action=f"Country '{serializer.validated_data.get('name')}' updated.",
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
            title="Country",
            description=f"A Country named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Country ",
            action=f"Country '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )

    @action(detail=False, methods=["get"], url_path="downloadCsv")
    def csv(self, request, module=None):
        module = self.kwargs.get("module")
        user = self.request.user

        check_permission(self, "read", module)
        filtered_qs = self.filter_queryset(self.get_queryset())
        filter_dict = getattr(getattr(filtered_qs.query, "where", None), "children", [])
        print("filter_dict", filter_dict)
        Notification.objects.create(
            title="Country",
            description=f"A Country CSV export has been initiated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title="Country",
            action=f"Country CSV export initiated.",
            createdBy=user,
            updatedBy=user,
        )
        return start_csv_export(
            self,
            request,
            module,
            model_name="squadServices.Country",
            fields=["id", "name", "countryCode", "MCC", "createdAt"],
            filter_dict=filter_dict,
        )


class StateFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    countryName = django_filters.CharFilter(
        field_name="country__name", lookup_expr="icontains"
    )

    class Meta:
        model = State
        fields = ["name", "countryName"]


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = StateFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return State.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = State.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError(
                {"error": "State for the selected country already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="State",
            description=f"A new State named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" State ",
            action=f"State '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = State.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "State with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="State",
            description=f"A State named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" State ",
            action=f"State '{serializer.validated_data.get('name')}' updated.",
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
            title="State",
            description=f"A State named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" State ",
            action=f"State '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )


class CurrencyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    country_name = django_filters.CharFilter(
        field_name="country__name", lookup_expr="icontains"
    )

    class Meta:
        model = Currency
        fields = ["name", "country_name"]


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CurrencyFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return Currency.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        country = serializer.validated_data.get("country")
        exist = Currency.objects.filter(country=country, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "Currency for the selected country already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="Currency",
            description=f"A new Currency named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Currency ",
            action=f"Currency '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Currency.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Currency with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="Currency",
            description=f"A Currency named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Currency ",
            action=f"Currency '{serializer.validated_data.get('name')}' updated.",
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
            title="Currency",
            description=f"A Currency named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Currency ",
            action=f"Currency '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )


class EntityFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Entity
        fields = ["name"]


class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = EntityFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return Entity.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = Entity.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "Entity for the selected country already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="Entity",
            description=f"A new Entity named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Entity ",
            action=f"Entity '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Entity.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "Entity with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="Entity",
            description=f"A Entity named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Entity ",
            action=f"Entity '{serializer.validated_data.get('name')}' updated.",
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
            title="Entity",
            description=f"A Entity named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" Entity ",
            action=f"Entity '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )


class TimeZoneFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = TimeZone
        fields = ["name"]


class TimeZoneViewSet(viewsets.ModelViewSet):
    queryset = TimeZone.objects.all()
    serializer_class = TimeZoneSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = TimeZoneFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)
            return TimeZone.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        name = serializer.validated_data.get("name")
        exist = TimeZone.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError(
                {"error": "TimeZone for the selected country already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        Notification.objects.create(
            title="TimeZone",
            description=f"A new TimeZone named '{serializer.validated_data.get('name')}' has been created.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" TimeZone ",
            action=f"TimeZone '{serializer.validated_data.get('name')}' created.",
            createdBy=user,
            updatedBy=user,
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = TimeZone.objects.filter(name=name, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "TimeZone with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        Notification.objects.create(
            title="TimeZone",
            description=f"A TimeZone named '{serializer.validated_data.get('name')}' has been updated.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" TimeZone ",
            action=f"TimeZone '{serializer.validated_data.get('name')}' updated.",
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
            title="TimeZone",
            description=f"A TimeZone named '{instance.name}' has been deleted.",
            createdBy=user,
            updatedBy=user,
        )
        UserLog.objects.create(
            user=user,
            title=" TimeZone ",
            action=f"TimeZone '{instance.name}' deleted.",
            createdBy=user,
            updatedBy=user,
        )
