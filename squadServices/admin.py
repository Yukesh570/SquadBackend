from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

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
    list_display = UserAdmin.list_display + ("phone", "userType")
    search_fields = UserAdmin.search_fields + ("phone", "userType")


class NavItemAdmin(admin.ModelAdmin):
    model = NavItem
    list_display = ("label", "url", "order", "is_active")
    ordering = ["order"]
class NavUserRelationAdmin(admin.ModelAdmin):
    model = NavUserRelation
    list_display = ("userType", "navigateId", "read", "write", "delete", "put")
    search_fields = ("userType", "navigateId__label")
admin.site.register(User, CustomUserAdmin)
admin.site.register(NavItem, NavItemAdmin)
admin.site.register(NavUserRelation, NavUserRelationAdmin)

