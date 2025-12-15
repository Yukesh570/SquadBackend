from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from squadServices.models.campaign import Campaign, CampaignContact, Template
from squadServices.models.clientModel.client import Client
from squadServices.models.company import Company, CompanyCategory, CompanyStatus

from squadServices.models.connectivityModel.smpp import SMPP
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from squadServices.models.email import EmailHost, EmailTemplate
from squadServices.models.mappingSetup.mappingSetup import MappingSetup
from squadServices.models.navItem import NavItem, NavUserRelation
from squadServices.models.network import Network
from squadServices.models.operators.operators import Operators
from squadServices.models.rateManagementModel.customerRate import CustomerRate
from squadServices.models.rateManagementModel.vendorRate import VendorRate
from squadServices.models.users import User, UserLoginHistory


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
    list_display = ("id", "name")
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
        "name",
        "countryCode",
        "MCC",
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


class entityAdmin(admin.ModelAdmin):
    model = Entity
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
        "company",
        "profileName",
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
        "status",
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
        "MNC",
        "isDeleted",
        "createdAt",
        "updatedAt",
    )
    search_fields = ("ratePlan", "MNC")
    readonly_fields = ("createdAt", "updatedAt")


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
admin.site.register(Entity, entityAdmin)
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
