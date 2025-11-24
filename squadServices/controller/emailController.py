from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.email import EmailHost, EmailTemplate
from squadServices.models.navItem import NavUserRelation
from squadServices.serializer.emailSerializer import EmailHostSerializer, EmailTemplateSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters


class EmailHostFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')  
    owner = django_filters.CharFilter(field_name='owner__username', lookup_expr='icontains')
    smtpHost = django_filters.CharFilter(lookup_expr='icontains')  
    smtpPort = django_filters.NumberFilter()
    smtpUser = django_filters.CharFilter(lookup_expr='icontains')  
    security = django_filters.CharFilter(lookup_expr='icontains')  

    class Meta:
        model = EmailHost
        fields = ['name', 'owner', 'smtpHost', 'smtpPort', 'smtpUser','security']

class EmailHostViewSet(viewsets.ModelViewSet):
    serializer_class = EmailHostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmailHostFilter

    def get_queryset(self):
        # Only allow access to EmailHosts owned by the requesting user
        module = self.kwargs.get('module')
        check_permission(self, 'read', module)
        return EmailHost.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist = EmailHost.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "EmailHost with this name already exists."})
        serializer.save(owner=user,createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        check_permission(self, 'put', module)
        user = self.request.user
        serializer.save(updatedBy=user)
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

class EmailTemplateFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')  


    class Meta:
        model = EmailTemplate
        fields = ['name']


class EmailTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']
    filterset_class = EmailTemplateFilter
    def get_queryset(self):
        # Only allow access to EmailHosts owned by the requesting user
        module = self.kwargs.get('module')
        check_permission(self, 'read', module)
        return EmailTemplate.objects.filter(isDeleted=False)

    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        print("asdfasdfasdf",module)
        user = self.request.user
        check_permission(self, 'write', module)
        name=serializer.validated_data.get("name")
        exist = EmailTemplate.objects.filter(name__iexact=name, isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "EmailTemplate with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user)


    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        check_permission(self, 'put', module)
        user = self.request.user
        serializer.save(updatedBy=user)
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

