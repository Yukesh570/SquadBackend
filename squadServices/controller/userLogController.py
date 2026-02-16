from rest_framework.permissions import IsAuthenticated

from rest_framework import viewsets
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission

from squadServices.models.notificationModel.notification import Notification


from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.permissions import AllowAny
from squadServices.models.users import UserLog
from squadServices.serializer.userLogSerializer import UserLogSerializer


class UserLogFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = UserLog
        fields = ["title"]


class UserLogViewSet(viewsets.ModelViewSet):
    queryset = UserLog.objects.all()
    serializer_class = UserLogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserLogFilter

    def get_queryset(self):
        if self.action == "list":

            return UserLog.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):

        user = self.request.user

        serializer.save(user=user, createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):

        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
