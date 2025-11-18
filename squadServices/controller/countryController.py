import json
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from squadServices.models.navItem import NavItem
from squadServices.serializer.countrySerializer import CountrySerializer, CurrencySerializer, EntitySerializer, StateSerializer, TimeZoneSerializer
from squadServices.serializer.navSerializer import (
    NavItemSerializer,
)
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError



class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        print("nam===============e",name)
        exist = Country.objects.filter(name__iexact=name, isDeleted=False)
        print("exist===============e",exist)

        if exist.exists():
            raise ValidationError({"error": "Country with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user

        check_permission(self, 'put', module)
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()



class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        country=serializer.validated_data.get("country")
        print("nam===============e",country)
        exist = State.objects.filter(country=country, isDeleted=False)
        print("exist===============e",exist)

        if exist.exists():
            raise ValidationError({"error": "State for the selected country already exists."})
        serializer.save(createdBy=user, updatedBy=user) 
    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user

        check_permission(self, 'put', module)
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()


class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()



class TimeZoneViewSet(viewsets.ModelViewSet):
    queryset = TimeZone.objects.all()
    serializer_class = TimeZoneSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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
        serializer.save( updatedBy=user) 
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

