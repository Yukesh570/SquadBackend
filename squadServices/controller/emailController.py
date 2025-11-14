from rest_framework import viewsets, permissions

from squadServices.helper.permissionHelper import check_permission
from squadServices.models.email import EmailHost, EmailTemplate
from squadServices.models.navItem import NavUserRelation
from squadServices.serializer.emailSerializer import EmailHostSerializer, EmailTemplateSerializer
from rest_framework.exceptions import PermissionDenied


class EmailHostViewSet(viewsets.ModelViewSet):
    serializer_class = EmailHostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only allow access to EmailHosts owned by the requesting user
        module = self.kwargs.get('module')
        check_permission(self, 'read', module)
        return EmailHost.objects.all()

    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        user = self.request.user
        check_permission(self, 'write', module)
        serializer.save(owner=user)

    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        check_permission(self, 'put', module)
        serializer.save()
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        instance.delete()


class EmailTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only allow access to EmailHosts owned by the requesting user
        module = self.kwargs.get('module')
        check_permission(self, 'read', module)
        return EmailTemplate.objects.all()

    def perform_create(self, serializer):
        module = self.kwargs.get('module')
        print("asdfasdfasdf",module)
        user = self.request.user
        check_permission(self, 'write', module)
        serializer.save()


    def perform_update(self, serializer):
        module = self.kwargs.get('module')
        check_permission(self, 'put', module)
        serializer.save()
    def perform_destroy(self, instance):
        module = self.kwargs.get('module')
        check_permission(self, 'delete', module)
        instance.delete()

