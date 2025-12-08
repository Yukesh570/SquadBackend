import json
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from squad.task import sendEmailTask
from squad.utils.authenticators import JWTAuthentication
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.email import EmailTemplate
from squadServices.models.navItem import NavItem, NavUserRelation
from squadServices.models.users import UserType
from squadServices.serializer.navSerializer import (
    GetSerializer,
    NavItemSerializer,
    NavUserRelationSerializer,
)
from django.db.models import Max

from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
import django_filters


class NavItemFilter(django_filters.FilterSet):
    label = django_filters.CharFilter(lookup_expr="icontains")
    parent_label = django_filters.CharFilter(
        field_name="parent__label", lookup_expr="icontains"
    )

    class Meta:
        model = NavItem
        fields = ["label", "parent_label"]


def adjust_order(parent=None, new_order=None, exclude_id=None):
    """
    Adjusts orders of NavItems at the same level (same parent).
    If new_order is provided, shifts items >= new_order down by 1.
    """
    qs = NavItem.objects.filter(parent=parent, isDeleted=False).order_by("order")
    if exclude_id:
        qs = qs.exclude(id=exclude_id)

    if new_order is None:
        # Assign max order + 1
        max_order = qs.aggregate(Max("order"))["order__max"] or 0
        return max_order + 1
    else:
        # Shift items >= new_order down
        qs_to_shift = qs.filter(order__gte=new_order)
        for item in qs_to_shift:
            item.order += 1
            item.save()
        return new_order


class NavItemViewSet(viewsets.ModelViewSet):
    queryset = NavItem.objects.all()
    serializer_class = NavItemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = NavItemFilter

    def get_queryset(self):
        if self.action == "list":
            module = self.kwargs.get("module")
            check_permission(self, "read", module)

            return NavItem.objects.filter(is_active=True, isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        print("asdfasdfasdf", module)
        user = self.request.user
        check_permission(self, "write", module)
        label = serializer.validated_data.get("label")
        order = serializer.validated_data.get("order")

        exist = NavItem.objects.filter(label__iexact=label, isDeleted=False)
        if exist.exists():
            raise ValidationError({"error": "NavItem with this name already exists."})
        serializer.save(createdBy=user, updatedBy=user)
        parent = serializer.validated_data.get("parent")
        serializer.validated_data["order"] = adjust_order(parent, order)

        if parent:
            url = parent.url + "/" + serializer.validated_data.get("url")
            serializer.validated_data["url"] = url
        serializer.save(createdBy=user, updatedBy=user)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        check_permission(self, "put", module)
        instance = serializer.instance

        new_order = serializer.validated_data.get("order", instance.order)
        parent = serializer.validated_data.get("parent", instance.parent)

        label = serializer.validated_data.get("label")
        if label != serializer.instance.label:
            exist = NavItem.objects.filter(label__iexact=label, isDeleted=False)
            if exist.exists():
                raise ValidationError(
                    {"error": "NavItem with the same name already exists."}
                )
        if new_order != instance.order or parent != instance.parent:
            # Shift orders at old level (remove gap)
            old_siblings = (
                NavItem.objects.filter(parent=instance.parent, isDeleted=False)
                .exclude(id=instance.id)
                .order_by("order")
            )
            for idx, item in enumerate(old_siblings, start=1):
                item.order = idx
                item.save()

        # Adjust order at new level
        serializer.validated_data["order"] = adjust_order(
            parent, new_order, exclude_id=instance.id
        )

        user = self.request.user
        serializer.save(updatedBy=user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        siblings = NavItem.objects.filter(
            parent=instance.parent, isDeleted=False
        ).order_by("order")

        for idx, item in enumerate(siblings, start=1):
            item.order = idx
            item.save()


class GetNavUserRelationViewSet(viewsets.ModelViewSet):
    serializer_class = GetSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return NavItem.objects.filter(
            parent=None, is_active=True, isDeleted=False
        ).order_by("order")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["userType"] = self.request.user.userType
        return context

    def getByUserType(self, request, *args, **kwargs):
        userType = kwargs.get("userType")
        related_nav_ids = NavUserRelation.objects.filter(userType=userType).values_list(
            "navigateId", flat=True
        )
        nav_items = NavItem.objects.filter(
            id__in=related_nav_ids, parent=None, is_active=True, isDeleted=False
        ).order_by("order")

        serializer = self.get_serializer(
            nav_items, many=True, context={"userType": userType}
        )
        return Response(serializer.data)


class NavUserRelationViewSet(viewsets.ModelViewSet):
    queryset = NavUserRelation.objects.all()
    serializer_class = NavUserRelationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if self.action == "list":
            return NavUserRelation.objects.filter(
                userType=user.userType, navigateId__parent=None
            )
        return super().get_queryset()

    def create(self, request, *args, **kwargs):
        userType = request.data.get("userType")
        if not userType:
            return Response(
                {"error": "userType is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        navItems = NavItem.objects.filter(is_active=True, isDeleted=False)
        if NavUserRelation.objects.filter(userType=userType).exists():
            return Response(
                {"error": "userType already exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        relations = [
            NavUserRelation(
                userType=userType,
                navigateId=navItem,
                read=False,
                write=False,
                delete=False,
                put=False,
            )
            for navItem in navItems
        ]
        NavUserRelation.objects.bulk_create(relations)
        return Response(
            {"message": f"{len(relations)} NavUserRelation created for '{userType}'."},
            status=status.HTTP_201_CREATED,
        )

    def createSidebar(self, request, *args, **kwargs):
        label = request.data.get("label")
        userType = request.user.userType
        if not label:
            return Response(
                {"error": "label is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        navItems = NavItem.objects.filter(label=label, isDeleted=False).first()
        print("navItems", navItems.id)
        if NavUserRelation.objects.filter(navigateId=navItems.id).exists():
            return Response(
                {"error": "label already exists"}, status=status.HTTP_400_BAD_REQUEST
            )
        relations = [
            NavUserRelation(
                userType=value,
                navigateId=navItems,
                read=True,
                write=(value == UserType.ADMIN),
                delete=(value == UserType.ADMIN),
                put=(value == UserType.ADMIN),
            )
            for value, label in UserType.choices
        ]

        NavUserRelation.objects.bulk_create(relations)
        return Response(
            {"message": f"{len(relations)} NavUserRelation created for '{label}'."},
            status=status.HTTP_201_CREATED,
        )

    def getByUserType(self, request, *args, **kwargs):
        userType = kwargs.get("userType")
        relations = NavUserRelation.objects.filter(userType=userType)
        serializer = self.get_serializer(relations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_partial_update(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            return Response(
                {"error": "Expected a list of objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        userType = request.user.userType
        if userType != "ADMIN":
            return Response(
                {"error": "You are not authorized to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        updated_items = []
        for item in data:
            obj_id = item.get("id")
            if not obj_id:
                continue

            try:
                instance = NavUserRelation.objects.get(id=obj_id)
            except NavUserRelation.DoesNotExist:
                continue

            serializer = self.get_serializer(instance, data=item, partial=True)
            if serializer.is_valid():
                serializer.save()
                updated_items.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"updated": updated_items}, status=status.HTTP_200_OK)


@api_view(["POST"])
def sendMail(request):
    subject = request.data.get("subject")
    message = request.data.get("content")

    fromEmail = request.data.get("from_email")
    raw_recipient = request.data.get("recipient_list")
    emailHostId = request.data.get("email_host_id")  # new
    attachments = []
    if isinstance(raw_recipient, str):
        try:
            # Case: JSON-like list string
            recipientList = json.loads(raw_recipient)
            if isinstance(recipientList, str):
                # Single email inside quotes
                recipientList = [recipientList]
        except:
            # Case: single email, plain string
            recipientList = [raw_recipient]
        else:
            recipientList = raw_recipient
    for file_obj in request.FILES.getlist("attachments"):
        import base64

        attachments.append(
            {
                "name": file_obj.name,
                "type": file_obj.content_type,
                "content": base64.b64encode(file_obj.read()).decode("utf-8"),
            }
        )

    # If no file uploaded, send None
    if len(attachments) == 0:
        attachments = None

    sendEmailTask.delay(
        subject, message, fromEmail, recipientList, emailHostId, attachments
    )

    return Response({"detail": "Email task queued."}, status=status.HTTP_202_ACCEPTED)
