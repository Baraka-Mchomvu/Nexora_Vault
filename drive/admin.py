from django.contrib import admin

from .models import File, Folder, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "quota_bytes")


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "parent", "is_trashed", "created_at")
    list_filter = ("is_trashed",)
    search_fields = ("name", "owner__username")


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "folder", "size", "is_trashed", "created_at")
    list_filter = ("is_trashed",)
    search_fields = ("name", "owner__username")
