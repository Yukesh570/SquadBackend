import django_filters
import num2words
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
from squadServices.models.finanace.invoice import ClientInvoice, VendorInvoice
from squadServices.models.finanace.invoiceSetup import InvoiceSetup
from squadServices.models.transaction.transaction import ClientTransaction
from squadServices.serializer.financeSerailizer.clientInvoiceSerializer import (
    ClientInvoiceSerializer,
)
from squadServices.serializer.financeSerailizer.generateIncoiveSerializer import (
    GenerateClientInvoiceRequestSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from num2words import num2words
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
        request=GenerateClientInvoiceRequestSerializer,
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
        serializer = GenerateClientInvoiceRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Extract Validated Data
        data = serializer.validated_data
        accountManager = data.get("accountManager")
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
            grand_total = float(calculated_amount) + float(tax_amount)
            amount_in_words = num2words(int(grand_total))
            # Do NOT save to the database. Just return the math so the frontend can display it.
            breakdown_data = [
                {
                    "particular": "Standard SMS",
                    "volume": total_sms_sent,
                    "charge": float(calculated_amount),
                }
            ]

            context = {
                "client": client,
                "client_name": client.company.name,
                "client_email": client.company.companyEmail,
                "client_phone": client.company.phone,
                "client_currency": client.company.currency,
                "client_address": client.company.address,  # Use your setupRule override if needed
                "breakdown": breakdown_data,
                "total_amount": calculated_amount,
                "tax_amount": tax_amount,
                "grand_total": grand_total,
                "amount_in_words": amount_in_words,
                "bank_details": "Global IME Bank",
                "invoice_number": "DRAFT-PREVIEW",  # Fake number for the preview
                "status": "DRAFT",
            }
            # 2. Render the HTML
            template = get_template("finance/invoice_pdf.html")
            html_string = template.render(context)

            # 3. Create the PDF in Memory (NO DATABASE!)
            pdf_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(
                BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer
            )

            if pisa_status.err:
                return Response(
                    {"error": "Failed to generate PDF preview"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # 4. CRITICAL: Rewind the buffer to the beginning before reading it!
            pdf_buffer.seek(0)

            # 5. Return the file directly to the browser
            response = FileResponse(pdf_buffer, content_type="application/pdf")
            response["Content-Disposition"] = 'inline; filename="Invoice-Preview.pdf"'

            return response

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
                    accountManager=accountManager,
                    billingPeriodStart=from_date,
                    billingPeriodEnd=to_date,
                    invoiceDate=invoice_date,
                    invoiceNumber=invoice_number,
                    totalAmount=calculated_amount,
                    totalSegments=total_sms_sent,
                    status="GENERATED",
                    createdBy=request.user,
                )

            # Build the breakdown data (Must be standard Python dictionaries/lists so Celery can serialize it)
            breakdown_data = [
                {
                    "particular": "Standard SMS",
                    "volume": total_sms_sent,
                    "charge": float(calculated_amount),
                }
            ]

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


class ClientInvoiceFilter(ExtendedFilterSet):

    client = django_filters.NumberFilter()

    class Meta:
        model = ClientInvoice
        fields = {
            "client__name": ["exact", "icontains", "isnull"],
            "accountManager__username": ["exact", "icontains", "isnull"],
            "invoiceNumber": ["exact", "icontains", "isnull"],
            "billingPeriodStart": ["exact", "gt", "lt", "range", "isnull"],
            "billingPeriodEnd": ["exact", "gt", "lt", "range", "isnull"],
            "invoiceDate": ["exact", "gt", "lt", "range", "isnull"],
            "totalAmount": ["exact", "gt", "lt", "range", "isnull"],
            "totalSegments": ["exact", "gt", "lt", "range", "isnull"],
            "createdAt": ["exact", "range", "gt", "lt"],
        }


class ClinetInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = ClientInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClientInvoiceFilter

    def get_queryset(self):
        module = self.kwargs.get("module")
        # check_permission(self, "read", module)
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
                f'attachment; filename="{invoice.invoiceNumber}.pdf"'
            )

            return response

        except FileNotFoundError:
            return Response(
                {"error": "The PDF file could not be found on the server."},
                status=status.HTTP_404_NOT_FOUND,
            )
