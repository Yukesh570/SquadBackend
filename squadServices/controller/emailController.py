from rest_framework import viewsets, permissions

from squadServices.models.email import EmailHost
from squadServices.serializer.emailSerializer import EmailHostSerializer
from rest_framework.exceptions import PermissionDenied


class EmailHostViewSet(viewsets.ModelViewSet):
    serializer_class = EmailHostSerializer
    permission_classes = [permissions.IsAuthenticated]
    

    # def get_queryset(self):
    #     # Only allow access to EmailHosts owned by the requesting user
    #     return EmailHost.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        print("user",user)

        if getattr(user, "userType", "").upper() != "ADMIN":
            raise PermissionDenied("Only admin users can create Email Hosts.")

        serializer.save(owner=user)
