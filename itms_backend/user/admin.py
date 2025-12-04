from django.contrib import admin
from .models import Role, Permission


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_key', 'role_name', 'status')
    search_fields = ('role_key', 'role_name')
    list_filter = ('status',)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('perm_key',)
    search_fields = ('perm_key',)
