import csv
import io
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from squad.utils.authenticators import JWTAuthentication
from django.db import transaction
from django.utils.dateparse import parse_datetime
import openpyxl
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from squadServices.models.campaign import Campaign, CampaignContact, Template
from squadServices.serializer.campaignSerializer import (
    CampaignContactSerializer,
    CampaignSerializer,
    TemplateSerializer,
)
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from rest_framework.exceptions import ValidationError


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
        check_permission(self, "put", module)
        name = serializer.validated_data.get("name")
        if name != serializer.instance.name:
            existingCampaign = Campaign.objects.filter(name=name, isDeleted=False)
            if existingCampaign.exists():
                raise ValidationError(
                    {"error": "Campaign with the same name already exists."}
                )

        serializer.save(updatedBy=self.request.user)

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        name = data.get("name")
        module = self.kwargs.get("module")

        check_permission(self, "write", module)

        contacts_data = data.pop("contacts", None)
        if isinstance(contacts_data, list) and len(contacts_data) == 1:
            contacts_data = contacts_data[0]
        templateId = data.get("template")
        objective = data.get("objective")
        content = data.get("content")
        scheduleValue = data.get("schedule")
        file = request.FILES.get("csvFile")
        template_instance = None
        existingCampaign = Campaign.objects.filter(name__iexact=name, isDeleted=False)
        if existingCampaign.exists():
            return Response(
                {"error": "Campaign with the same name already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if templateId:
            template_instance = get_object_or_404(Template, id=templateId)
        with transaction.atomic():
            reponse = Campaign.objects.create(
                template=template_instance,
                schedule=scheduleValue,
                objective=objective,
                content=content,
                name=name,
                createdBy=self.request.user,
                updatedBy=self.request.user,
            )
            serializer = self.get_serializer(reponse)
            campaignId = reponse.id
            contactsData = contacts_data

            campaign = Campaign.objects.get(id=campaignId)
            # campaign = response

            createdContacts = []
            invalidContacts = []
            duplicateInInput = []
            seenInputs = set()

            if file:
                fileName = file.name
                if fileName.endswith(".csv"):
                    try:
                        decodedFile = file.read().decode("utf-8")
                    except UnicodeDecodeError:
                        file.seek(0)
                        decodedFile = file.read().decode("latin1")

                    ioString = io.StringIO(decodedFile)
                    reader = csv.DictReader(ioString)

                    for row in reader:
                        row_lower = {k.lower(): v for k, v in row.items()}

                        for contact in row:
                            contact = row_lower.get("contact", "").strip()
                            if contact and contact in seenInputs:
                                duplicateInInput.append(contact)
                            else:
                                seenInputs.add(contact)
                                if is_valid_contact(contact):
                                    createdContacts.append(
                                        CampaignContact(
                                            campaign=campaign, contactNumber=contact
                                        )
                                    )
                                else:
                                    invalidContacts.append(contact)
                elif fileName.endswith(".xlsx"):
                    wb = openpyxl.load_workbook(file)
                    ws = wb.active
                    # Assumes column header in the first row
                    headers = [
                        str(cell.value).lower()
                        for cell in next(ws.iter_rows(min_row=1, max_row=1))
                    ]
                    contact_idx = (
                        headers.index("contact") if "contact" in headers else None
                    )
                    if contact_idx is not None:
                        for row in ws.iter_rows(min_row=2):  # skip header
                            contact = (
                                str(row[contact_idx].value).strip()
                                if row[contact_idx].value
                                else ""
                            )
                            if contact and contact in seenInputs:
                                duplicateInInput.append(contact)
                            elif contact:
                                seenInputs.add(contact)
                                if is_valid_contact(contact):
                                    createdContacts.append(
                                        CampaignContact(
                                            campaign=campaign, contactNumber=contact
                                        )
                                    )
                                else:
                                    invalidContacts.append(contact)
            else:
                contactsData = contactsData
                if not contactsData:
                    raise ValidationError(
                        {"error": "contacts field is required and cannot be empty."}
                    )

                if contactsData:

                    print("contactsData-------", contactsData)
                    contacts = [c.strip() for c in contactsData.split(",") if c.strip()]

                    for contact in contacts:
                        if contact in seenInputs:
                            duplicateInInput.append(contact)
                        else:
                            seenInputs.add(contact)
                            if is_valid_contact(contact):
                                createdContacts.append(
                                    CampaignContact(
                                        campaign=campaign, contactNumber=contact
                                    )
                                )
                            else:
                                invalidContacts.append(contact)

            if createdContacts:
                CampaignContact.objects.bulk_create(createdContacts)
        createdContactNumbers = [c.contactNumber for c in createdContacts]

        return Response(
            {
                "campaign": serializer.data,
                "created": createdContactNumbers,
                "invalidContacts": invalidContacts,
                "duplicateInInput": duplicateInInput,
            },
            status=status.HTTP_201_CREATED,
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

    def perform_destroy(self, instance):
        module = self.kwargs.get("module")
        check_permission(self, "delete", module)
        user = self.request.user
        instance.isDeleted = True
        instance.updatedBy = user
        instance.save()
