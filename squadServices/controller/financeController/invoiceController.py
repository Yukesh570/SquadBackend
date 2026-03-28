import django_filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum
from datetime import datetime
import uuid

# Adjust imports based on your exact file structure
from squad.task import generate_invoice_pdf_task
from squadServices.controller.companyController import ExtendedFilterSet
from squadServices.models.clientModel.client import Client
from squadServices.models.finanace.invoice import ClientInvoice
from squadServices.models.finanace.invoiceSetup import InvoiceSetup
from squadServices.models.transaction.transaction import ClientTransaction
from squadServices.serializer.financeSerailizer.clientInvoiceSerializer import (
    ClientInvoiceSerializer,
)
from squadServices.serializer.financeSerailizer.generateIncoiveSerializer import (
    GenerateInvoiceRequestSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse

from django_filters.rest_framework import DjangoFilterBackend
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.helper.permissionHelper import check_permission
from rest_framework import viewsets, permissions
from squadServices.helper.action import (
    log_action_create,
    log_action_delete,
    log_action_update,
)

from django.shortcuts import get_object_or_404
from django.http import FileResponse


class GenerateClientInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=GenerateInvoiceRequestSerializer,
        responses={
            200: OpenApiResponse(description="Preview data successfully returned"),
            201: OpenApiResponse(description="Invoice generated and saved to database"),
            400: OpenApiResponse(description="Validation Error (e.g., bad dates)"),
        },
        summary="Generate or Preview a Client Invoice",
        description="Pass action='PREVIEW' to calculate totals without saving. Pass action='GENERATE' to officially create the invoice record.",
    )
    def post(self, request):
        # 1. Catch and Validate the Form Data
        serializer = GenerateInvoiceRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Extract Validated Data
        data = serializer.validated_data
        client = data["client"]
        from_date = data["fromDate"]
        to_date = data["toDate"]
        invoice_date = data["invoiceDate"]

        # Check if the frontend sent {"action": "PREVIEW"} or {"action": "GENERATE"}
        action_type = request.data.get("action", "GENERATE").upper()
        # tax
        setupRule = InvoiceSetup.objects.filter(
            company=client.company, isDeleted=False
        ).first()

        tax_amount = 0
        if setupRule and setupRule.isTaxApplied:
            tax_amount = setupRule.tax

        # 3. CALCULATE THE TOTAL AMOUNT (The core billing logic)
        # We query the ClientTransaction table for all records in this date range
        transaction_summary = ClientTransaction.objects.filter(
            client=client,
            transactionType="DEDUCTION",
            createdAt__date__gte=from_date,
            createdAt__date__lte=to_date,
            isDeleted=False,
        ).aggregate(
            total_cost=Sum(
                "amount"
            ),  # Assuming your transaction model has a 'cost' or 'amount' field
            total_sms=Sum("segments"),  # Optional: Good for displaying on the invoice
        )

        # If they sent 0 messages, the sum might be None, so we default to 0.00
        calculated_amount = transaction_summary["total_cost"] or 0.00
        total_sms_sent = transaction_summary["total_sms"] or 0

        # --- PREVIEW LOGIC ---
        if action_type == "PREVIEW":
            # Do NOT save to the database. Just return the math so the frontend can display it.
            return Response(
                {
                    "message": "Preview generated successfully.",
                    "clientName": client.name,
                    "billingPeriod": f"{from_date} to {to_date}",
                    "totalSms": total_sms_sent,
                    "totalAmount": calculated_amount,
                    "status": "DRAFT",
                },
                status=status.HTTP_200_OK,
            )

        # --- GENERATE LOGIC ---
        # Generate a unique Invoice Number (e.g., INV-20260315-A1B2)
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:4].upper()
        invoice_number = f"INV-{date_str}-{unique_id}"

        # Save to the database safely using an atomic transaction
        try:
            with transaction.atomic():
                invoice = ClientInvoice.objects.create(
                    client=client,
                    billingPeriodStart=from_date,
                    billingPeriodEnd=to_date,
                    invoiceDate=invoice_date,
                    invoiceNumber=invoice_number,
                    totalAmount=calculated_amount,
                    status="GENERATED",
                    createdBy=request.user,
                )

                # TODO: Trigger Celery Task here to generate the actual PDF
                # generate_invoice_pdf_task.delay(invoice.id)
            # Build the breakdown data (Must be standard Python dictionaries/lists so Celery can serialize it)
            breakdown_data = [
                {
                    "particular": "Standard SMS",
                    "volume": total_sms_sent,
                    "charge": float(calculated_amount),
                }
            ]

            # 🔥 Send it to Celery! Notice we pass invoice.id, NOT the invoice object
            generate_invoice_pdf_task.delay(
                invoice.id, breakdown_data, tax_amount=tax_amount
            )
            return Response(
                {
                    "message": "Invoice generated successfully.",
                    "invoiceId": invoice.id,
                    "invoiceNumber": invoice.invoiceNumber,
                    "totalAmount": invoice.totalAmount,
                    "status": invoice.status,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to generate invoice: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ClinetInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = ClientInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        module = self.kwargs.get("module")
        check_permission(self, "read", module)
        return ClientInvoice.objects.filter(isDeleted=False)


class DownloadInvoicePDFView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiResponse(description="PDF File Stream"),
            404: OpenApiResponse(description="PDF not generated yet or file missing"),
        },
        summary="Download or View Invoice PDF",
        description="Returns the actual PDF file. Use this in an <iframe> or download link.",
    )
    def get(self, request, invoice_id):
        # 1. Fetch the invoice record
        invoice = get_object_or_404(ClientInvoice, id=invoice_id)

        # 2. Check if Celery has actually finished generating it yet!
        if not invoice.invoicePdf or not invoice.invoicePdf.name:
            return Response(
                {
                    "error": "The PDF for this invoice is still generating or does not exist."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Open the file and stream it securely to the user
        try:
            # .open() grabs the file whether it is stored locally or on AWS S3
            file_handle = invoice.invoicePdf.open("rb")

            response = FileResponse(file_handle, content_type="application/pdf")

            # 'inline' tells the browser to open it in a new tab.
            # Change to 'attachment' if you want to force a download directly to their computer.
            response["Content-Disposition"] = (
                f'inline; filename="{invoice.invoiceNumber}.pdf"'
            )

            return response

        except FileNotFoundError:
            return Response(
                {"error": "The PDF file could not be found on the server."},
                status=status.HTTP_404_NOT_FOUND,
            )
