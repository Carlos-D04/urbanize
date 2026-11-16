from django.contrib import admin

from .models import EmailDelivery


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "status", "attempts", "last_attempted_at")
    list_filter = ("status",)
    ordering = ("-created_at", "-pk")
    readonly_fields = (
        "notification",
        "status",
        "attempts",
        "last_attempted_at",
        "sent_at",
        "last_error",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
