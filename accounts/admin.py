from django.contrib import admin
from .models import Attachee

@admin.register(Attachee)
class AttacheeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('first_name', 'last_name', 'email')