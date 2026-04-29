from rest_framework.permissions import IsAuthenticated
from squad.utils.authenticators import JWTAuthentication
from rest_framework import viewsets
from squadServices.helper.permissionHelper import check_permission

from squadServices.models.generalSetting.generalSetting import GeneralSetting
from squadServices.serializer.generalSettingSerializer.generalSettingSerializer import (
    GeneralSettingSerializer,
)
from squadServices.helper.action import (
    log_action_update_setting,
)


class GeneralSettingView(viewsets.ModelViewSet):
    queryset = GeneralSetting.objects.all()
    serializer_class = GeneralSettingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "put", "patch"]

    def get_object(self):
        """
        ⚡️ This is the magic for Singletons!
        Because there is no ID in the URL, we explicitly tell DRF
        to fetch (or create) the master row for retrieve/update actions.
        """
        obj, created = GeneralSetting.objects.get_or_create(id=1)

        # Check 'read' permissions if they are doing a GET request
        if self.action == "retrieve":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)

        return obj

    def get_queryset(self):
        # We keep this just in case DRF needs it internally,
        # but get_object() handles the heavy lifting now.
        return GeneralSetting.objects.filter(id=1)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)

        serializer.save(updatedBy=user)
        log_action_update_setting(user, "GeneralSetting")
