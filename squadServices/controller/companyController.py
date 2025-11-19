import json
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.company import Company, CompanyCategory, CompanyStatus
from squadServices.serializer.companySerializer import CompanyCategorySerializer, CompanySerializer, CompanyStatusSerializer

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError



class CompanyCategoryViewSet(viewsets.ModelViewSet):
    queryset = CompanyCategory.objects.all()
    serializer_class = CompanyCategorySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return CompanyCategory.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist = CompanyCategory.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "CompanyCategory with this name already exists."})
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



class CompanyStatusViewSet(viewsets.ModelViewSet):
    queryset = CompanyStatus.objects.all()
    serializer_class = CompanyStatusSerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return CompanyStatus.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        print("nam===============e",name)
        exist = CompanyStatus.objects.filter(name__iexact=name, isDeleted=False)
        print("exist===============e",exist)

        if exist.exists():
            raise ValidationError({"error": "CompanyStatus with this name already exists."})
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





class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    # 👇 Require JWT token authentication
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get('module')
            check_permission(self, 'read', module)
            return Company.objects.filter(isDeleted=False)
        return super().get_queryset()
    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        print("nam===============e",name)
        exist = Company.objects.filter(name__iexact=name, isDeleted=False)
        print("exist===============e",exist)

        if exist.exists():
            raise ValidationError({"error": "Company with this name already exists."})
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
