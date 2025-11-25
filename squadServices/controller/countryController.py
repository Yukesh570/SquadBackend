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
from squadServices.serializer.countrySerializer import CountrySerializer, CurrencySerializer, EntitySerializer, StateSerializer, TimeZoneSerializer

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

class CountryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains') 
    countryCode = django_filters.CharFilter(lookup_expr='icontains')  
    MCC = django_filters.CharFilter(lookup_expr='icontains')  
 

    class Meta:
        model = Country
        fields = ['name', 'countryCode', 'MCC']

class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CountryFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return Country.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist = Country.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError({"error": "Country with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'put', module)
        name=serializer.validated_data.get("name")

        if name != serializer.instance.name:
            exist = Country.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError({"error": "Country with the same name already exists."})
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
    @action(detail=False, methods=['get'], url_path="downloadCsv")
    def csv(self, request, module=None):
        module = self.kwargs.get('module')
        check_permission(self, 'read', module)
        filtered_qs = self.filter_queryset(self.get_queryset())
        filter_dict = getattr(getattr(filtered_qs.query, 'where', None), 'children', [])
        print("filter_dict",filter_dict)
        return start_csv_export(self, request, 
                                module,
                                model_name="squadServices.Country",
                                fields=["id","name","countryCode","MCC","createdAt"],
                                filter_dict=filter_dict,)


class StateFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains') 
    countryName = django_filters.CharFilter(
        field_name='country__name',
        lookup_expr='icontains'
    )
    class Meta:
        model = State
        fields = ['name', 'countryName']
class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = StateFilter


    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return State.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist = State.objects.filter(name__iexact=name, isDeleted=False)

        if exist.exists():
            raise ValidationError({"error": "State for the selected country already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'put', module)
        name=serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = State.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError({"error": "State with the same name already exists."})
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

class CurrencyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains') 
    country_name = django_filters.CharFilter(
        field_name='country__name',
        lookup_expr='icontains'
    )
    class Meta:
        model = Currency
        fields = ['name', 'country_name']

class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CurrencyFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return Currency.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        country=serializer.validated_data.get("country")
        exist=Currency.objects.filter(country=country,isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "Currency for the selected country already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'put', module)
        name=serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Currency.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError({"error": "Currency with the same name already exists."})
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class EntityFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains') 

    class Meta:
        model = Entity
        fields = ['name']

class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = EntityFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return Entity.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist=Entity.objects.filter(name__iexact=name,isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "Entity for the selected country already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'put', module)
        name=serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = Entity.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError({"error": "Entity with the same name already exists."})
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class TimeZoneFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains') 

    class Meta:
        model = TimeZone
        fields = ['name']
class TimeZoneViewSet(viewsets.ModelViewSet):
    queryset = TimeZone.objects.all()
    serializer_class = TimeZoneSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = TimeZoneFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return TimeZone.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist=TimeZone.objects.filter(name__iexact=name,isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "TimeZone for the selected country already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'put', module)
        name=serializer.validated_data.get("name")
        if name != serializer.instance.name:
            exist = TimeZone.objects.filter(name__iexact=name, isDeleted=False)
            if exist.exists():
                raise ValidationError({"error": "TimeZone with the same name already exists."})
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

