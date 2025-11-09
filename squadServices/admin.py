from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from squadServices.models.campaign import Campaign, CampaignContact, Template
from squadServices.models.navItem import NavItem, NavUserRelation
from squadServices.models.users import User


class CustomUserAdmin(UserAdmin):
    model = User
    # Add your custom fields to fieldsets and list_display
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("phone", "userType")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("phone", "userType")}),
    )
    list_display = ("id","phone", "userType") + UserAdmin.list_display 
    search_fields = UserAdmin.search_fields + ("phone", "userType")


class NavItemAdmin(admin.ModelAdmin):
    model = NavItem
    list_display = ("label", "url","parent", "order", "is_active")
    ordering = ["order"]
class NavUserRelationAdmin(admin.ModelAdmin):
    model = NavUserRelation
    list_display = ("id","userType", "navigateId", "read", "write", "delete", "put")
    search_fields = ("userType", "navigateId__label")



class CampaignAdmin(admin.ModelAdmin):
    model = Campaign
    list_display = ("id","name", "objective", "content", "schedule")
    search_fields = ("name", "navigateId__label")

class CampaignContactAdmin(admin.ModelAdmin):
    model = CampaignContact
    list_display = ("id","campaign", "contactNumber")
    search_fields = ("contactNumber","campaign")

class TemplateAdmin(admin.ModelAdmin):
    model = Template
    list_display = ("id","name")



admin.site.register(User, CustomUserAdmin)
admin.site.register(NavItem, NavItemAdmin)
admin.site.register(NavUserRelation, NavUserRelationAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(CampaignContact, CampaignContactAdmin)
admin.site.register(Template, TemplateAdmin)


