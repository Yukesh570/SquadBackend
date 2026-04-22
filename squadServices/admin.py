from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from squadServices.models.campaign import Campaign, CampaignContact, Template
from squadServices.models.clientModel.client import Client, ClientPolicy, IpWhitelist
from squadServices.models.company import Company, CompanyCategory, CompanyStatus
from django.utils.html import format_html

from squadServices.models.connectivityModel.smpp import SMPP
from squadServices.models.connectivityModel.verdor import Vendor, VendorPolicy
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from squadServices.models.detailedReport.detailedReport import DetailedSMSReport
from squadServices.models.email import EmailHost, EmailTemplate
from squadServices.models.finanace.invoice import ClientInvoice, VendorInvoice
from squadServices.models.mappingSetup.mappingSetup import MappingSetup
from squadServices.models.navItem import NavItem, NavUserRelation
from squadServices.models.network import Network
from squadServices.models.notificationModel.notification import Notification
from squadServices.models.operators.operators import OperatorNetworkCode, Operators
from squadServices.models.rateManagementModel.customerRate import CustomerRate
from squadServices.models.rateManagementModel.vendorRate import VendorRate
from squadServices.models.routeManager.customRoute import CustomRoute
from squadServices.models.smpp.smppSMS import (
    DLREvent,
    MessageAttempt,
    MessageAuditLog,
    MultipartBuffer,
    SMSMessage,
    SMSMessagePart,
)
from squadServices.models.transaction.transaction import (
    ClientTransaction,
    VendorTransaction,
)
from squadServices.models.users import User, UserLog, UserLoginHistory

from squadServices.models.finanace.invoiceSetup import InvoiceSetup


class CustomUserAdmin(UserAdmin):
    model = User
    # Add your custom fields to fieldsets and list_display
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("phone", "userType")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("phone", "userType")}),
    )
    list_display = ("id", "phone", "userType") + UserAdmin.list_display
    search_fields = UserAdmin.search_fields + ("phone", "userType")
    readonly_fields = ("createdAt", "updatedAt")


class UserLoginHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "ipAddress",
        "browser",
        "device",
        "loggedAt",
    )
    list_filter = ("browser", "device", "loggedAt")
    search_fields = ("user__username", "ipAddress")
    readonly_fields = ("loggedAt",)


class NavItemAdmin(admin.ModelAdmin):
    model = NavItem
    list_display = ("label", "url", "parent", "order", "is_active")
    ordering = ["order"]
    readonly_fields = ("createdAt", "updatedAt")


class NavUserRelationAdmin(admin.ModelAdmin):
    model = NavUserRelation
    list_display = ("id", "userType", "navigateId", "read", "write", "delete", "put")
    search_fields = ("userType", "navigateId__label")


class CampaignAdmin(admin.ModelAdmin):
    model = Campaign
    list_display = ("id", "name", "objective", "content", "schedule")
    search_fields = ("name", "navigateId__label")
    readonly_fields = ("createdAt", "updatedAt")


class CampaignContactAdmin(admin.ModelAdmin):
    model = CampaignContact
    list_display = ("id", "campaign", "contactNumber")
    search_fields = ("contactNumber", "campaign")


class TemplateAdmin(admin.ModelAdmin):
    model = Template
    list_display = ("id", "name")
    readonly_fields = ("createdAt", "updatedAt")


class EmailTemplateAdmin(admin.ModelAdmin):
    model = EmailTemplate
    list_display = ("id", "name", "subject", "emailServer")
    readonly_fields = ("createdAt", "updatedAt")


class NotificationAdmin(admin.ModelAdmin):
    model = Notification
    list_display = ("id", "title", "description")
    readonly_fields = ("createdAt", "updatedAt")


class UserLogAdmin(admin.ModelAdmin):
    model = UserLog
    list_display = ("id", "title", "action")
    readonly_fields = ("createdAt", "updatedAt")


class EmailHostAdmin(admin.ModelAdmin):
    model = EmailHost
    list_display = (
        "id",
        "name",
        "smtpHost",
        "smtpPort",
        "smtpUser",
        "isDeleted",
        "smtpPassword",
        "security",
    )
    search_fields = ("name", "smtpHost", "smtpUser")
    readonly_fields = ("createdAt", "updatedAt")


class companyCategoryAdmin(admin.ModelAdmin):
    model = CompanyCategory
    list_display = (
        "id",
        "name",
        "isDeleted",
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )
    search_fields = ("name",)
    readonly_fields = ("createdAt", "updatedAt")


class companyStatusAdmin(admin.ModelAdmin):
    model = CompanyStatus
    list_display = (
        "id",
        "name",
        "isDeleted",
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )
    search_fields = ("name",)
    readonly_fields = ("createdAt", "updatedAt")


class countryAdmin(admin.ModelAdmin):
    model = Country
    list_display = (
        "id",
        "iso2",
        "name",
        "countryCode",
        "region",
        "isActive",
        "subRegion",
        "isDeleted",
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )
    search_fields = ("name",)
    readonly_fields = ("createdAt", "updatedAt")


class stateAdmin(admin.ModelAdmin):
    model = State
    list_display = (
        "id",
        "name",
        "country",
        "isDeleted",
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )
    search_fields = ("name",)
    readonly_fields = ("createdAt", "updatedAt")


class currencyAdmin(admin.ModelAdmin):
    model = Currency
    list_display = (
        "id",
        "name",
        "country",
        "isDeleted",
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )
    search_fields = ("name",)
    readonly_fields = ("createdAt", "updatedAt")


class EntityAdmin(admin.ModelAdmin):
    # The columns shown on the main list page
    list_display = (
        "id",
        "companyName",
        "legalEntityName",
        "invoiceNumber",
        "emailAddress",
        "isDeleted",
        "createdAt",
    )

    # 🚨 CRITICAL FIX: We search by the new fields since 'name' is gone
    search_fields = ("companyName", "legalEntityName", "emailAddress", "phone")

    # Adds a handy filter sidebar on the right
    list_filter = ("isDeleted", "weekCommencing", "createdAt")

    # Fields that cannot be edited manually
    readonly_fields = ("createdAt", "updatedAt")

    # Organizes the detail view into clean, logical sections
    fieldsets = (
        (
            "Core Business Info",
            {
                "fields": (
                    "companyName",
                    "legalEntityName",
                    "companyLogo",
                    "invoiceNumber",
                    "weekCommencing",
                    "vatRegistrationNumber",
                )
            },
        ),
        (
            "Contact & Location",
            {"fields": ("emailAddress", "phone", "businessAddress")},
        ),
        ("Financial Details", {"fields": ("bankAccountDetail",)}),
        (
            "Audit & Tracking",
            {
                "fields": (
                    "isDeleted",
                    "createdBy",
                    "updatedBy",
                    "createdAt",
                    "updatedAt",
                ),
                "classes": (
                    "collapse",
                ),  # This hides the audit fields by default so the page looks cleaner!
            },
        ),
    )


class timeZoneAdmin(admin.ModelAdmin):
    model = TimeZone
    list_display = (
        "id",
        "name",
        "isDeleted",
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )
    search_fields = ("name",)
    readonly_fields = ("createdAt", "updatedAt")


class companyAdmin(admin.ModelAdmin):
    model = Company
    list_display = (
        "id",
        "name",
        "shortName",
        "phone",
        "category",
        "companyEmail",
        "supportEmail",
        "billingEmail",
        "ratesEmail",
        "lowBalanceAlertEmail",
        "country",
        "state",
        "category",
        "status",
        "currency",
        "timeZone",
        "businessEntity",
        "customerCreditLimit",
        "vatNumber",
        "vendorCreditLimit",
        "balanceAlertAmount",
        "referencNumber",
        "vatNumber",
        "address",
        "validityPeriod",
        "defaultEmail",
        "onlinePayment",
        "companyBlocked",
        "allowWhiteListedCards",
        "sendDailyReports",
        "allowNetting",
        "showHlrApi",
        "enableVendorPanel",
        "isDeleted",
        "createdBy",
        "createdAt",
        "updatedBy",
        "updatedAt",
        "address",
        "validityPeriod",
        "enableVendorPanel",
    )
    search_fields = (
        "name",
        "companyType",
        "emailType",
    )
    readonly_fields = ("createdAt", "updatedAt")


class connectivityAdmin(admin.ModelAdmin):
    model = SMPP
    list_display = (
        "id",
        "smppHost",
        "smppPort",
        "systemID",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("smppHost", "systemID")
    readonly_fields = ("createdAt", "updatedAt")


class vendorAdmin(admin.ModelAdmin):
    model = Vendor
    list_display = (
        "id",
        "profileName",
        "company",
        "smpp",
        "ratePlanName",
        "connectionType",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("company", "profileName")
    readonly_fields = ("createdAt", "updatedAt")


class clientAdmin(admin.ModelAdmin):
    model = Client
    list_display = (
        "id",
        "name",
        "company",
        "ratePlanName",
        "smppUsername",
        "status",
        "enableDlr",
        "route",
        "paymentTerms",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("company", "name")
    readonly_fields = ("createdAt", "updatedAt")


class vendorRateAdmin(admin.ModelAdmin):
    model = VendorRate
    list_display = (
        "id",
        "ratePlan",
        "currencyCode",
        "timeZone",
        "country",
        "MCC",
        "rate",
        "remark",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("ratePlan", "currencyCode")
    readonly_fields = ("createdAt", "updatedAt")


class customerRateAdmin(admin.ModelAdmin):
    model = CustomerRate
    list_display = (
        "id",
        "ratePlan",
        "currencyCode",
        "timeZone",
        "country",
        "MCC",
        "rate",
        "remark",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("ratePlan", "currencyCode")
    readonly_fields = ("createdAt", "updatedAt")


class NetworkAdmin(admin.ModelAdmin):
    model = Network
    list_display = (
        "id",
        "name",
        "MNC",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("name", "MNC")
    readonly_fields = ("createdAt", "updatedAt")


class MappingSetupAdmin(admin.ModelAdmin):
    model = MappingSetup
    list_display = (
        "id",
        "ratePlan",
        "country",
        "countryCode",
        "timeZone",
        "MNC",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("ratePlan", "MNC")
    readonly_fields = ("createdAt", "updatedAt")


class OperatorsAdmin(admin.ModelAdmin):
    model = Operators
    list_display = (
        "id",
        "name",
        "country",
        "operatorCode",
        "status",
        "notes",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    readonly_fields = ("createdAt", "updatedAt")


class CustomRouteAdmin(admin.ModelAdmin):
    model = CustomRoute
    list_display = (
        "id",
        "name",
        "status",
        "orginatingClient",
        "terminatingVendor",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("name", "status")
    readonly_fields = ("createdAt", "updatedAt")


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "destination",
        "status",
        "segmentNumber",  # Kept as your original CharField
        "characterCount",  # Kept as your original CharField
        "concatenated_reference",  # The new puzzle ID
        "sendClientDlr",
        "clientDlrPushed",
        "isDeleted",
        "queued_at",
    )
    search_fields = ("text", "destination", "status", "external_id")
    list_filter = ("status", "isDeleted")

    readonly_fields = (
        "external_id",
        "createdAt",
        "updatedAt",
        "queued_at",
        "submitted_at",
        "sent_at",
        "delivered_at",
        "failed_at",
    )


@admin.register(SMSMessagePart)
class SMSMessagePartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "part_no",
        "part_total",
        "udh_ref",
        "submit_status",  # Shows if this specific piece failed or delivered
        "vendor_msg_id",  # The telecom's tracking ID
        "last_submit_at",
    )
    search_fields = ("message__text", "vendor_msg_id", "message__destination")
    list_filter = ("submit_status",)

    # BinaryFields (short_message) MUST be readonly in Django Admin or it will crash.
    # We also lock down the automated timestamps.
    readonly_fields = (
        "short_message",
        "last_submit_at",
        "created_at",
        "updated_at",
        "submitted_at",
        "sent_at",
        "delivered_at",
        "failed_at",
    )


@admin.register(MessageAttempt)
class MessageAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "segment",
        "attempt_number",
        "provider",
        "status",
        "started_at",
    )
    search_fields = ("provider_message_id", "message__destination")
    list_filter = ("status", "provider")

    # Lock down the timestamps and JSON payloads
    readonly_fields = (
        "started_at",
        "completed_at",
        "request_payload",
        "response_payload",
    )


@admin.register(DLREvent)
class DLREventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "provider_message_id",
        "event_type",
        "segment_number",
        "received_at",
    )
    search_fields = ("provider_message_id", "message__destination")
    list_filter = ("event_type",)

    # DLRs are append-only logs, so the timestamp and payload should be strictly read-only
    readonly_fields = ("received_at", "raw_payload")


class IpWhiteListAdmin(admin.ModelAdmin):
    model = IpWhitelist
    list_display = (
        "id",
        "ip",
        "client",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("ip",)
    readonly_fields = ("createdAt", "updatedAt")


class ClientTransactionAdmin(admin.ModelAdmin):
    model = ClientTransaction
    list_display = (
        "id",
        "client",
        "message",
        "transactionType",
        "segments",
        "ratePerSegment",
        "amount",
        "balanceSpent",
        "description",
        "createdAt",
        "updatedAt",
        "isDeleted",
    )
    search_fields = ("ip",)
    readonly_fields = ("createdAt", "updatedAt")


class VendorTransactionAdmin(admin.ModelAdmin):
    model = VendorTransaction
    list_display = (
        "id",
        "vendor",
        "message",
        "transactionType",
        "segments",
        "ratePerSegment",
        "amount",
        "balanceSpent",
        "description",
        "createdAt",
        "updatedAt",
        "isDeleted",
    )
    search_fields = ("ip",)
    readonly_fields = ("createdAt", "updatedAt")


@admin.register(DetailedSMSReport)
class DetailedSMSReportAdmin(admin.ModelAdmin):
    # Columns to show in the list view
    list_display = (
        "request_time",
        "client",
        "destination",
        "vendor",
        # "formatted_margin",
        "colored_status",
        "vendor_msg_id",
    )

    # Sidebar filters
    list_filter = ("submitStatus", "client", "vendor", "request_time")

    # Search bar (searching across key identifiers)
    search_fields = ("destination", "vendor_msg_id", "text_message_id", "text")

    # Read-only fields (usually you don't want to edit financial logs manually)
    readonly_fields = ("request_time", "delivery_time")

    # Organize the detail view into sections
    fieldsets = (
        (
            "Identifiers",
            {"fields": ("message", "senderId", "text_message_id", "vendor_msg_id")},
        ),
        (
            "Message Content",
            {
                "fields": (
                    "text",
                    "part_total",
                    "destination",
                    "countryMCC",
                    "operatorMNC",
                )
            },
        ),
        ("Financials (Client)", {"fields": ("client", "clientRate", "client_charge")}),
        ("Financials (Vendor)", {"fields": ("vendor", "vendorRate", "vendor_charge")}),
        (
            "Status & Timing",
            {"fields": ("submitStatus", "request_time", "delivery_time")},
        ),
    )

    # # Custom method to show Margin with colors
    # def formatted_margin(self, obj):
    #     margin = obj.client_charge - obj.vendor_charge
    #     color = "green" if margin > 0 else "red"

    #     return format_html(
    #         '<span style="color: {}; font-weight: bold;">${}</span>', color, margin
    #     )

    # formatted_margin.short_description = "Margin"

    # Custom method to color-code the Status
    def colored_status(self, obj):

        colors = {
            "DELIVERED": "green",
            "FAILED": "red",
            "SUBMITTED": "orange",
            "QUEUED": "gray",
        }
        color = colors.get(obj.submitStatus, "black")
        return format_html('<b style="color: {};">{}</b>', color, obj.submitStatus)

    colored_status.short_description = "Status"


from django.contrib import admin


@admin.register(InvoiceSetup)
class InvoiceSetupAdmin(admin.ModelAdmin):
    # 1. Columns displayed in the main list view
    list_display = (
        "id",
        "get_company_name",
        "invoiceFrequency",
        "dueDays",
        "isTaxApplied",
        "isDeleted",
        "updatedAt",
    )

    # 2. Filters on the right sidebar
    list_filter = (
        "invoiceFrequency",
        "isTaxApplied",
        "isDeleted",
        "createdAt",
    )

    # 3. Search bar functionality (Searches inside the linked Company table too!)
    search_fields = (
        "company__name",
        "billingAddressOverride",
    )

    # 4. Prevent users from editing audit fields manually
    readonly_fields = (
        "createdAt",
        "updatedAt",
        "createdBy",
        "updatedBy",
    )

    # 5. Organize the detail view into clean, collapsible sections
    fieldsets = (
        (
            "Company & Entity Information",
            {
                "fields": (
                    "company",
                    "billingAddressOverride",
                    # Uncomment the next line if you kept the businessEntity field in this model
                    "businessEntity",
                )
            },
        ),
        (
            "Billing Configuration",
            {
                "fields": (
                    "invoiceFrequency",
                    "dueDays",
                )
            },
        ),
        (
            "Tax Information",
            {
                "fields": (
                    "isTaxApplied",
                    "tax",
                )
            },
        ),
        (
            "Audit Trail (Read Only)",
            {
                "classes": ("collapse",),  # Makes this section collapsible
                "fields": (
                    "isDeleted",
                    "createdBy",
                    "createdAt",
                    "updatedBy",
                    "updatedAt",
                ),
            },
        ),
    )

    # --- Custom Column Methods ---
    def get_company_name(self, obj):
        return obj.company.name if obj.company else "-"

    get_company_name.short_description = "Company Name"
    get_company_name.admin_order_field = (
        "company__name"  # Allows sorting by this column
    )

    # --- Automatic User Tracking ---
    def save_model(self, request, obj, form, change):
        """
        Automatically sets createdBy and updatedBy based on the logged-in admin user.
        """
        if getattr(obj, "createdBy", None) is None:
            obj.createdBy = request.user
        obj.updatedBy = request.user

        super().save_model(request, obj, form, change)


@admin.register(ClientInvoice)
class ClientInvoiceAdmin(admin.ModelAdmin):
    # 1. Columns displayed in the main list view
    list_display = (
        "invoiceNumber",
        "get_client_name",
        "totalAmount",
        "status",
        "billingPeriodStart",
        "billingPeriodEnd",
        "has_pdf",
    )

    # 2. Filters on the right sidebar
    list_filter = (
        "status",
        "isDeleted",
        "invoiceDate",
        "createdAt",
    )

    # 3. Search bar functionality
    search_fields = (
        "invoiceNumber",
        "client__name",
    )

    # 4. Prevent users from manually editing audit fields
    readonly_fields = (
        "createdAt",
        "updatedAt",
        "createdBy",
    )

    # 5. Organize the detail view into clean, collapsible sections
    fieldsets = (
        (
            "Invoice Core Details",
            {"fields": ("invoiceNumber", "accountManager", "client", "status")},
        ),
        (
            "Billing & Financials",
            {
                "fields": (
                    "totalAmount",
                    "invoiceDate",
                    "billingPeriodStart",
                    "billingPeriodEnd",
                )
            },
        ),
        ("Generated Documents", {"fields": ("invoicePdf",)}),
        (
            "Audit Trail (Read Only)",
            {
                "classes": ("collapse",),  # Makes this section collapsible
                "fields": ("isDeleted", "createdBy", "createdAt", "updatedAt"),
            },
        ),
    )

    # 6. Register our custom action
    actions = ["mark_as_paid", "mark_as_sent"]

    # --- Custom Column Methods ---
    def get_client_name(self, obj):
        return obj.client.name if obj.client else "-"

    get_client_name.short_description = "Client Name"
    get_client_name.admin_order_field = "client__name"

    def has_pdf(self, obj):
        """Displays a simple True/False icon indicating if the PDF has been generated"""
        return bool(obj.invoicePdf)

    has_pdf.boolean = True
    has_pdf.short_description = "PDF Ready"

    # --- Custom Admin Actions (Bulk Operations) ---
    @admin.action(description="Mark selected invoices as PAID")
    def mark_as_paid(self, request, queryset):
        updated_count = queryset.update(status="PAID")
        self.message_user(
            request, f"Successfully marked {updated_count} invoices as PAID."
        )

    @admin.action(description="Mark selected invoices as SENT")
    def mark_as_sent(self, request, queryset):
        updated_count = queryset.update(status="SENT")
        self.message_user(
            request, f"Successfully marked {updated_count} invoices as SENT."
        )

    # --- Automatic User Tracking ---
    def save_model(self, request, obj, form, change):
        """
        Automatically sets createdBy based on the logged-in admin user.
        """
        if getattr(obj, "createdBy", None) is None:
            obj.createdBy = request.user

        # If you added updatedBy to your ClientInvoice model, uncomment this:
        # obj.updatedBy = request.user

        super().save_model(request, obj, form, change)


@admin.register(VendorInvoice)
class VendorInvoiceAdmin(admin.ModelAdmin):
    # 1. Columns displayed in the main list view
    list_display = (
        "invoiceNumber",
        "get_vendor_name",
        "totalAmount",
        "status",
        "billingPeriodStart",
        "billingPeriodEnd",
        "has_pdf",
    )

    # 2. Filters on the right sidebar
    list_filter = (
        "status",
        "isDeleted",
        "invoiceDate",
        "createdAt",
    )

    # 3. Search bar functionality
    search_fields = (
        "invoiceNumber",
        "vendor__name",
    )

    # 4. Prevent users from manually editing audit fields
    readonly_fields = (
        "createdAt",
        "updatedAt",
        "createdBy",
    )

    # 5. Organize the detail view into clean, collapsible sections
    fieldsets = (
        (
            "Invoice Core Details",
            {"fields": ("invoiceNumber", "accountManager", "vendor", "status")},
        ),
        (
            "Billing & Financials",
            {
                "fields": (
                    "totalAmount",
                    "invoiceDate",
                    "billingPeriodStart",
                    "billingPeriodEnd",
                )
            },
        ),
        ("Generated Documents", {"fields": ("invoicePdf",)}),
        (
            "Audit Trail (Read Only)",
            {
                "classes": ("collapse",),  # Makes this section collapsible
                "fields": ("isDeleted", "createdBy", "createdAt", "updatedAt"),
            },
        ),
    )

    # 6. Register our custom action
    actions = ["mark_as_paid", "mark_as_sent"]

    # --- Custom Column Methods ---
    def get_vendor_name(self, obj):
        return obj.vendor.profileName if obj.vendor else "-"

    get_vendor_name.short_description = "Vendor Name"
    get_vendor_name.admin_order_field = "vendor__name"

    def has_pdf(self, obj):
        """Displays a simple True/False icon indicating if the PDF has been generated"""
        return bool(obj.invoicePdf)

    has_pdf.boolean = True
    has_pdf.short_description = "PDF Ready"

    # --- Custom Admin Actions (Bulk Operations) ---
    @admin.action(description="Mark selected invoices as PAID")
    def mark_as_paid(self, request, queryset):
        updated_count = queryset.update(status="PAID")
        self.message_user(
            request, f"Successfully marked {updated_count} invoices as PAID."
        )

    @admin.action(description="Mark selected invoices as SENT")
    def mark_as_sent(self, request, queryset):
        updated_count = queryset.update(status="SENT")
        self.message_user(
            request, f"Successfully marked {updated_count} invoices as SENT."
        )

    # --- Automatic User Tracking ---
    def save_model(self, request, obj, form, change):
        """
        Automatically sets createdBy based on the logged-in admin user.
        """
        if getattr(obj, "createdBy", None) is None:
            obj.createdBy = request.user

        # If you added updatedBy to your ClientInvoice model, uncomment this:
        # obj.updatedBy = request.user

        super().save_model(request, obj, form, change)


@admin.register(MessageAuditLog)
class MessageAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_message_info",
        "from_status",
        "to_status",
        "changed_by",
        "changed_at",
    )

    # Excellent for finding bottlenecks (e.g., filtering by 'changed_by' to see what the DLR worker did today)
    list_filter = ("to_status", "from_status", "changed_by", "changed_at")

    # Double-underscores let you search the audit log using the actual phone number or Vendor ID
    search_fields = (
        "message__message_id",
        "message__destination",
        "segment__vendor_msg_id",
        "changed_by",
        "reason",
    )

    # 1. Make all fields read-only so history cannot be rewritten
    readonly_fields = (
        "message",
        "segment",
        "from_status",
        "to_status",
        "changed_by",
        "reason",
        "changed_at",
    )

    # Sort newest first
    ordering = ("-changed_at",)

    # Helper function to make the list view cleaner and more informative
    def get_message_info(self, obj):
        if obj.message:
            return f"Msg {obj.message.id} ({obj.message.destination})"
        return "Unknown"

    get_message_info.short_description = "Parent Message"

    # # 2. SECURITY: Prevent admins from manually creating fake logs
    # def has_add_permission(self, request):
    #     return False

    # # 3. SECURITY: Prevent admins from deleting evidence/history
    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(MultipartBuffer)
class MultipartBufferAdmin(admin.ModelAdmin):
    # Columns shown in the main list view
    list_display = (
        "system_id",
        "destination",
        "ref_num",
        "part_num",
        "total_parts",
        "created_at",
    )

    # Adds a filter sidebar on the right
    list_filter = ("system_id", "created_at")

    # Adds a search bar at the top
    search_fields = ("system_id", "destination", "ref_num", "text_chunk")

    # Orders by newest first
    ordering = ("-created_at",)

    # Protects the timestamp from being edited
    readonly_fields = ("created_at",)

    # Optional: If you want to prevent staff from manually adding/editing chunks,
    # since this should only be controlled by the SMPP server.
    def has_add_permission(self, request):
        return False


@admin.register(VendorPolicy)
class VendorPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "vendor",
        "rateTps",
        "sendQueueLimit",
        "responseTimeout",
        "logLevel",
        "isDeleted",
    )
    search_fields = (
        "vendor__profileName",
        "vendor__name",
        "tlvTag",
    )  # Adjust vendor__ fields based on your Vendor model
    list_filter = ("logLevel", "isDeleted")
    readonly_fields = ("createdAt", "updatedAt")

    fieldsets = (
        ("Vendor Assignment", {"fields": ("vendor", "isDeleted")}),
        (
            "Number Formatting (TON/NPI)",
            {
                "fields": (
                    "sourceAddrTon",
                    "sourceAddrNpi",
                    "destAddrTon",
                    "destAddrNpi",
                    "addrTon",
                    "addrNpi",
                )
            },
        ),
        (
            "Speed & Queue Limits",
            {"fields": ("rateTps", "sendQueueLimit", "delayTime")},
        ),
        (
            "Timeouts & Heartbeats",
            {"fields": ("responseTimeout", "enquireLinkInterval", "connectionTimeout")},
        ),
        (
            "Retries & Recovery",
            {
                "fields": (
                    "connectionRetryDelay",
                    "connectionRetryCount",
                    "bindRetryDelay",
                    "bindRetryCount",
                    "connectionRecoveryDelay",
                )
            },
        ),
        ("Logging & Custom TLVs", {"fields": ("logLevel", "tlvTag", "tlvValue")}),
        (
            "Audit Log",
            {
                "fields": ("createdBy", "updatedBy", "createdAt", "updatedAt"),
                "classes": (
                    "collapse",
                ),  # Hides these by default to keep the form clean
            },
        ),
    )


@admin.register(ClientPolicy)
class ClientPolicyAdmin(admin.ModelAdmin):
    # What columns show up on the main list page
    list_display = (
        "client",
        "maxTps",
        "maxSessions",
        "maxWindowGlobal",
        "idleTimeoutSec",
        "isDeleted",
    )

    # Allows you to search by the client's name or SMPP username
    search_fields = ("client__name", "client__smppUsername")

    # Adds a filter sidebar on the right
    list_filter = ("isDeleted",)

    # Prevents admins from editing the auto-generated timestamps
    readonly_fields = ("createdAt", "updatedAt")

    # Groups the fields into beautiful sections on the detail page
    fieldsets = (
        ("Client Assignment", {"fields": ("client", "isDeleted")}),
        (
            "Throughput & Queueing",
            {
                "fields": ("maxTps", "maxQueueDepth"),
                "description": "Limits on how fast the client can send messages and how many can be queued.",
            },
        ),
        (
            "Session & Window Limits",
            {
                "fields": ("maxSessions", "maxWindowPerSession", "maxWindowGlobal"),
                "description": "Rules for concurrent TCP connections and unacknowledged messages (in-flight).",
            },
        ),
        (
            "Timeouts",
            {
                "fields": ("idleTimeoutSec", "submitTimeoutSec"),
                "description": "Rules for dropping dead connections and timing out vendor responses.",
            },
        ),
        (
            "Audit Log",
            {
                "fields": ("createdBy", "updatedBy", "createdAt", "updatedAt"),
                "classes": (
                    "collapse",
                ),  # Hides this section by default to keep the UI clean
            },
        ),
    )


@admin.register(OperatorNetworkCode)
class OperatorNetworkCodeAdmin(admin.ModelAdmin):
    # 1. High-visibility columns
    list_display = (
        "id",
        "get_country_iso",  # Custom method for cleaner look
        "operator",
        "MCC",
        "MNC",
        "networkName",
        "networkType",
        "isPrimary",
        "status",
    )

    # 2. Powerful sidebar filters
    list_filter = (
        "status",
        "networkType",
        "isPrimary",
        "country__name",  # Filter by country name
        "operator__name",  # Filter by operator name
    )

    # 3. Search anything
    search_fields = (
        "MCC",
        "MNC",
        "networkName",
        "operator__name",
        "country__name",
    )

    # 4. Grouping for better UX
    fieldsets = (
        ("Network Identity", {"fields": ("country", "operator", "networkName")}),
        ("Technical Codes", {"fields": ("MCC", "MNC", "networkType")}),
        ("Configuration", {"fields": ("isPrimary", "status")}),
        (
            "Timestamps",
            {
                "fields": ("createdAt", "updatedAt", "effectiveFrom", "effectiveTo"),
                "classes": ("collapse",),  # Hides these by default to save space
            },
        ),
    )

    readonly_fields = ("createdAt", "updatedAt")

    # 5. Helper method to show ISO code in list view
    @admin.display(description="Country")
    def get_country_iso(self, obj):
        return f"{obj.country.name} ({obj.country.iso2})"

    # 6. Optimization: Prevents N+1 query issues in admin
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("operator", "country")


admin.site.register(CustomRoute, CustomRouteAdmin)
admin.site.register(IpWhitelist, IpWhiteListAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(NavItem, NavItemAdmin)
admin.site.register(NavUserRelation, NavUserRelationAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(CampaignContact, CampaignContactAdmin)
admin.site.register(Template, TemplateAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(EmailHost, EmailHostAdmin)
admin.site.register(CompanyCategory, companyCategoryAdmin)
admin.site.register(CompanyStatus, companyStatusAdmin)
admin.site.register(Country, countryAdmin)
admin.site.register(State, stateAdmin)
admin.site.register(Currency, currencyAdmin)
admin.site.register(Entity, EntityAdmin)
admin.site.register(TimeZone, timeZoneAdmin)
admin.site.register(Company, companyAdmin)
admin.site.register(SMPP, connectivityAdmin)
admin.site.register(Vendor, vendorAdmin)
admin.site.register(Client, clientAdmin)
admin.site.register(VendorRate, vendorRateAdmin)
admin.site.register(CustomerRate, customerRateAdmin)
admin.site.register(Network, NetworkAdmin)
admin.site.register(MappingSetup, MappingSetupAdmin)
admin.site.register(Operators, OperatorsAdmin)
admin.site.register(UserLoginHistory, UserLoginHistoryAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserLog, UserLogAdmin)
admin.site.register(ClientTransaction, ClientTransactionAdmin)
admin.site.register(VendorTransaction, VendorTransactionAdmin)
