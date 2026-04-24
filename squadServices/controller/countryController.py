import json
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.utils.authenticators import JWTAuthentication
from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.helper.action import (
    log_action_create,
    log_action_delete,
    log_action_export,
    log_action_update,
)
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

from squadServices.utils import compress_image


class CountryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    countryCode = django_filters.CharFilter(lookup_expr="icontains")
    region = django_filters.CharFilter(lookup_expr="icontains")
    subRegion = django_filters.CharFilter(lookup_expr="icontains")
    iso2 = django_filters.CharFilter(lookup_expr="icontains")
    isActive = django_filters.BooleanFilter()

    class Meta:
        model = Country
        fields = [
            "name",
            "countryCode",
            "region",
            "subRegion",
            "iso2",
            "isActive",
        ]


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
        log_action_create(user, "Country", serializer.validated_data.get("name"))

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
        log_action_update(user, "Country", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Country", instance.name)

    @action(detail=False, methods=["get"], url_path="downloadCsv")
    def csv(self, request, module=None):
        module = self.kwargs.get("module")
        user = self.request.user

        check_permission(self, "read", module)
        filtered_qs = self.filter_queryset(self.get_queryset())
        filter_dict = getattr(getattr(filtered_qs.query, "where", None), "children", [])
        print("filter_dict", filter_dict)
        log_action_export(user, "Country")

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
        log_action_create(user, "State", serializer.validated_data.get("name"))

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
        log_action_update(user, "State", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "State", instance.name)


class CurrencyFilter(ExtendedFilterSet):
    class Meta:
        model = Currency
        # Define the fields and their allowed standard lookups
        fields = {
            # TEXT FIELDS: Support Equals, Contains, Is Empty
            "name": ["exact", "icontains", "isnull"],
            "currencyCode": ["exact", "icontains", "isnull"],
            "numericCode": ["exact", "icontains", "isnull"],
            "symbol": ["exact", "icontains", "isnull"],
            "decimalPlaces": ["exact", "icontains"],
            "isActive": ["exact"],
            "createdAt": ["exact", "range", "gt", "lt"],
        }


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

        serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "Currency", serializer.validated_data.get("name"))

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
        log_action_update(user, "Currency", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Currency", instance.name)


class EntityFilter(ExtendedFilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Entity
        # Define the fields and their allowed standard lookups
        fields = {
            # TEXT FIELDS: Support Equals, Contains, Is Empty
            "legalEntityName": ["exact", "icontains", "isnull"],
            "companyName": ["exact", "icontains", "isnull"],
            "invoiceNumber": ["exact", "icontains"],
            "weekCommencing": ["exact", "icontains"],
            "vatRegistrationNumber": ["exact", "icontains"],
            "phone": ["exact", "icontains"],
            "emailAddress": ["exact", "icontains"],
            "businessAddress": ["exact", "icontains"],
            "bankAccountDetail": ["exact", "icontains"],
            "createdAt": ["exact", "range", "gt", "lt"],
        }


class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = EntityFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return Entity.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        legalEntityName = serializer.validated_data.get("legalEntityName")
        exist = Entity.objects.filter(
            legalEntityName__iexact=legalEntityName, isDeleted=False
        )
        if exist.exists():
            raise ValidationError(
                {"error": "An Entity with this legal name already exists."}
            )
        # --- NEW: Prevent setting invoiceNumber on creation ---
        # If the user tried to send an invoiceNumber in their POST request,
        # remove it so the database defaults to 1.
        if "invoiceNumber" in serializer.validated_data:
            serializer.validated_data.pop("invoiceNumber")
        save_kwargs = {"createdBy": user, "updatedBy": user}
        new_logo = serializer.validated_data.get("companyLogo")
        if new_logo:
            save_kwargs["companyLogo"] = compress_image(new_logo)
        serializer.save(**save_kwargs)
        log_action_create(
            user, "Entity", serializer.validated_data.get("legalEntityName")
        )

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        legalEntityName = serializer.validated_data.get("legalEntityName")
        if legalEntityName != serializer.instance.legalEntityName:
            exist = Entity.objects.filter(
                legalEntityName=legalEntityName, isDeleted=False
            )
            if exist.exists():
                raise ValidationError(
                    {"error": "Entity with the same legalEntityName already exists."}
                )
        # Fetch the existing object from the database to get the old image
        old_instance = self.get_object()
        new_logo = serializer.validated_data.get("companyLogo")
        save_kwargs = {"updatedBy": user}
        # Check if we have a new logo, an old logo exists, and they aren't the exact same file
        if (
            new_logo
            and old_instance.companyLogo
            and old_instance.companyLogo != new_logo
        ):
            # save=False ensures we don't prematurely save the model before serializer.save()
            old_instance.companyLogo.delete(save=False)
            save_kwargs["companyLogo"] = compress_image(new_logo)
        serializer.save(**save_kwargs)
        log_action_update(
            user, "Entity", serializer.validated_data.get("legalEntityName")
        )

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        if instance.companyLogo:
            instance.companyLogo.delete(save=False)
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Entity", instance.legalEntityName)


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
        log_action_create(user, "TimeZone", serializer.validated_data.get("name"))

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
        log_action_update(user, "TimeZone", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "TimeZone", instance.name)
