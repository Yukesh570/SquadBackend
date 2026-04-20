import csv
import io
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from squad.task import process_campaign_contacts_task
from squad.utils.authenticators import JWTAuthentication
from django.db import transaction
from django.utils.dateparse import parse_datetime
import openpyxl
from squadServices.helper.action import (
    log_action_create,
    log_action_delete,
    log_action_update,
)
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.campaign import Campaign, CampaignContact, Template
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.smpp.smppSMS import SMSMessage
from squadServices.models.users import UserLog
from squadServices.serializer.campaignSerializer import (
    CampaignContactSerializer,
    CampaignSerializer,
    TemplateSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.exceptions import ValidationError
from django.core.files.storage import default_storage


def is_valid_contact(contact):
    return contact.isdigit() and 7 <= len(contact) <= 15


class CampaignFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Campaign
        fields = ["name", "objective", "content", "template", "schedule"]


class CampaignContactViewSet(viewsets.ModelViewSet):
    queryset = CampaignContact.objects.all()
    serializer_class = CampaignContactSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return CampaignContact.objects.filter(campaign__id=self.kwargs.get("pk"))


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name", "objective", "template", "schedule"]
    filterset_class = CampaignFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return Campaign.objects.filter(isDeleted=False)

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user

        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            existingCampaign = Campaign.objects.filter(name=name, isDeleted=False)
            if existingCampaign.exists():
                raise ValidationError(
                    {"error": "Campaign with the same name already exists."}
                )

        serializer.save(updatedBy=self.request.user)
        log_action_update(user, "Campaign", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Campaign", instance.name)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        name = data.get("name")
        module = self.kwargs.get("module")
        vendor = data.get("vendor")
        check_permission(self, "write", module)

        contacts_data = data.pop("contacts", None)
        if isinstance(contacts_data, list) and len(contacts_data) == 1:
            contacts_data = contacts_data[0]

        templateId = data.get("template")
        objective = data.get("objective")
        content = data.get("content")
        scheduleValue = data.get("schedule")
        file = request.FILES.get("csvFile")

        # 1. Validate Campaign Name
        existingCampaign = Campaign.objects.filter(name__iexact=name, isDeleted=False)
        if existingCampaign.exists():
            return Response(
                {"error": "Campaign with the same name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_instance = None
        if templateId:
            template_instance = get_object_or_404(Template, id=templateId)

        # 2. Save the Campaign object instantly
        with transaction.atomic():
            campaign = Campaign.objects.create(
                template=template_instance,
                schedule=scheduleValue,
                objective=objective,
                content=content,
                vendor=Vendor.objects.get(id=vendor),
                name=name,
                createdBy=self.request.user,
                updatedBy=self.request.user,
            )
            serializer = self.get_serializer(campaign)

        # 3. Figure out the text to send
        # message_text = (
        #     content
        #     if content
        #     else (template_instance.content if template_instance else "")
        # )
        message_text = content

        # 4. Save file temporarily for Celery (if uploaded)
        file_path = None
        if file:
            file_path = default_storage.save(f"tmp/campaigns/{file.name}", file)

        if not file and not contacts_data:
            return Response(
                {"error": "Please provide a file or manual contacts."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        print("vendor!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", vendor)
        # 5. FIRE AND FORGET: Hand off to Celery
        process_campaign_contacts_task.delay(
            campaign_id=campaign.id,
            file_path=file_path,
            contacts_string=contacts_data,
            user_id=self.request.user.id,
            message_text=message_text,
            vendor_id=vendor,
        )

        log_action_create(self.request.user, "Campaign", name)

        # 6. Instantly tell the frontend it was a success!
        return Response(
            {
                "campaign": serializer.data,
                "message": "Campaign created successfully! Contacts are being processed in the background.",
            },
            status=status.HTTP_202_ACCEPTED,  # 202 is the industry standard for "Accepted and processing in background"
        )


class TemplateFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Template
        fields = ["name"]


class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["name"]
    filterset_class = TemplateFilter

    def get_queryset(self):

        if self.action == "list":
            return Template.objects.filter(isDeleted=False)
        return super().get_queryset()

    def perform_create(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "write", module)
        exist = Template.objects.filter(
            name__iexact=serializer.validated_data.get("name"), isDeleted=False
        )
        if exist.exists():
            raise ValidationError(
                {"error": "Template with the same name already exists."}
            )
        serializer.save(createdBy=user, updatedBy=user)
        log_action_create(user, "Template", serializer.validated_data.get("name"))

    def perform_update(self, serializer):
        module = self.kwargs.get("module")
        user = self.request.user
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            existingCampaign = Template.objects.filter(name=name, isDeleted=False)
            if existingCampaign.exists():
                raise ValidationError(
                    {"error": "Template with the same name already exists."}
                )
        serializer.save(updatedBy=user)
        log_action_update(user, "Template", serializer.validated_data.get("name"))

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
        log_action_delete(user, "Template", instance.name)
