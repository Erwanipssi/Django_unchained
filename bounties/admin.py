from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import BountyMission, Hunter, Sheriff, User, WantedPerson


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle métier", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle métier", {"fields": ("role",)}),
    )


admin.site.register(Hunter)
admin.site.register(Sheriff)
admin.site.register(WantedPerson)
admin.site.register(BountyMission)