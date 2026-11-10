import mimetypes
import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def user_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1][:20]
    return f"user_{instance.owner_id}/{uuid.uuid4().hex}{ext}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    quota_bytes = models.BigIntegerField(default=settings.DEFAULT_QUOTA_BYTES)

    def used_bytes(self):
        return self.user.files.aggregate(total=models.Sum("size"))["total"] or 0

    def __str__(self):
        return f"Profile({self.user})"


class Folder(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders"
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    name = models.CharField(max_length=255)
    is_trashed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def breadcrumbs(self):
        trail, node = [], self
        while node:
            trail.append(node)
            node = node.parent
        return list(reversed(trail))

    def set_trashed(self, flag):
        """Trash or restore this folder and everything inside it."""
        stack = [self]
        while stack:
            folder = stack.pop()
            folder.is_trashed = flag
            folder.save(update_fields=["is_trashed"])
            folder.files.update(is_trashed=flag)
            stack.extend(folder.children.all())


class File(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files"
    )
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.CASCADE, related_name="files"
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=user_upload_path)
    size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=127, blank=True)
    is_trashed = models.BooleanField(default=False)
    share_token = models.CharField(max_length=32, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def guess_mime(self):
        return self.mime_type or mimetypes.guess_type(self.name)[0] or "application/octet-stream"


@receiver(post_delete, sender=File)
def delete_blob(sender, instance, **kwargs):
    """Remove the stored file from disk when its database row is deleted."""
    if instance.file:
        instance.file.delete(save=False)
