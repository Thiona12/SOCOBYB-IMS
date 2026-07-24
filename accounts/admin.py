from django.contrib import admin
from .models import User, Shop, Role, Permission, UserRole, RolePermission, UserPermission

admin.site.register(User)
admin.site.register(Shop)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(UserRole)
admin.site.register(RolePermission)
admin.site.register(UserPermission)
