from rest_framework import viewsets, permissions

from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.email import EmailHost, EmailTemplate
from squadServices.models.navItem import NavUserRelation
from squadServices.serializer.emailSerializer import EmailHostSerializer, EmailTemplateSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError


class EmailHostViewSet(viewsets.ModelViewSet):
    serializer_class = EmailHostSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

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


class EmailTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

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

