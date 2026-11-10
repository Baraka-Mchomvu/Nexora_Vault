from django.conf import settings

from .models import Profile


def storage(request):
    base = {"allow_signup": settings.ALLOW_SIGNUP}
    if not request.user.is_authenticated:
        return base
    profile, _ = Profile.objects.get_or_create(user=request.user)
    used = profile.used_bytes()
    quota = profile.quota_bytes
    percent = min(100, round(used * 100 / quota)) if quota else 0
    base.update({"storage_used": used, "storage_quota": quota, "storage_percent": percent})
    return base
