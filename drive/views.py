import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import SignupForm
from .models import File, Folder, Profile


# ---------- helpers ----------

def _folder_from_value(request, value):
    """Return the user's active folder for a POSTed id, or None for root."""
    if value and str(value).isdigit():
        return get_object_or_404(Folder, pk=int(value), owner=request.user, is_trashed=False)
    return None


def _back(folder):
    if folder:
        return redirect("drive:folder", folder_id=folder.id)
    return redirect("drive:home")


# ---------- auth ----------

def signup(request):
    if not settings.ALLOW_SIGNUP:
        raise Http404
    if request.user.is_authenticated:
        return redirect("drive:home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Profile.objects.get_or_create(user=user)
        login(request, user)
        return redirect("drive:home")
    return render(request, "registration/signup.html", {"form": form})


# ---------- browsing ----------

@login_required
def dashboard(request, folder_id=None):
    folder = None
    if folder_id:
        folder = get_object_or_404(Folder, pk=folder_id, owner=request.user, is_trashed=False)

    q = request.GET.get("q", "").strip()
    if q:
        folders = Folder.objects.filter(owner=request.user, is_trashed=False, name__icontains=q)
        files = File.objects.filter(owner=request.user, is_trashed=False, name__icontains=q)
    else:
        folders = Folder.objects.filter(owner=request.user, parent=folder, is_trashed=False)
        files = File.objects.filter(owner=request.user, folder=folder, is_trashed=False)

    return render(request, "drive/dashboard.html", {
        "folder": folder,
        "crumbs": folder.breadcrumbs() if folder else [],
        "folders": folders,
        "files": files,
        "q": q,
    })


# ---------- create / upload ----------

@login_required
@require_POST
def create_folder(request):
    parent = _folder_from_value(request, request.POST.get("parent"))
    name = request.POST.get("name", "").strip()[:255]
    if name:
        Folder.objects.create(owner=request.user, parent=parent, name=name)
        messages.success(request, f"Folder “{name}” created.")
    else:
        messages.error(request, "Enter a folder name.")
    return _back(parent)


@login_required
@require_POST
def upload(request):
    folder = _folder_from_value(request, request.POST.get("folder"))
    profile, _ = Profile.objects.get_or_create(user=request.user)
    used = profile.used_bytes()
    saved = 0

    for f in request.FILES.getlist("files"):
        if f.size > settings.MAX_UPLOAD_BYTES:
            limit_mb = settings.MAX_UPLOAD_BYTES // (1024 * 1024)
            messages.error(request, f"“{f.name}” is larger than the {limit_mb} MB file limit.")
            continue
        if used + f.size > profile.quota_bytes:
            messages.error(request, f"Not enough storage for “{f.name}”. Free up space or upgrade your plan.")
            continue
        File.objects.create(
            owner=request.user,
            folder=folder,
            name=f.name[:255],
            file=f,
            size=f.size,
            mime_type=(f.content_type or "")[:127],
        )
        used += f.size
        saved += 1

    if saved:
        messages.success(request, f"Uploaded {saved} file{'s' if saved != 1 else ''}.")
    return _back(folder)


# ---------- file actions ----------

@login_required
def download(request, pk):
    f = get_object_or_404(File, pk=pk, owner=request.user, is_trashed=False)
    return FileResponse(f.file.open("rb"), as_attachment=True, filename=f.name, content_type=f.guess_mime())


@login_required
@require_POST
def rename_file(request, pk):
    f = get_object_or_404(File, pk=pk, owner=request.user, is_trashed=False)
    name = request.POST.get("name", "").strip()[:255]
    if name:
        f.name = name
        f.save(update_fields=["name"])
    return _back(f.folder)


@login_required
@require_POST
def trash_file(request, pk):
    f = get_object_or_404(File, pk=pk, owner=request.user, is_trashed=False)
    f.is_trashed = True
    f.share_token = None  # trashing stops sharing
    f.save(update_fields=["is_trashed", "share_token"])
    messages.success(request, f"“{f.name}” moved to Trash.")
    return _back(f.folder)


@login_required
@require_POST
def toggle_share(request, pk):
    f = get_object_or_404(File, pk=pk, owner=request.user, is_trashed=False)
    if f.share_token:
        f.share_token = None
        messages.success(request, f"Sharing turned off for “{f.name}”.")
    else:
        f.share_token = secrets.token_hex(16)
        messages.success(request, f"Sharing turned on for “{f.name}”. Use Copy link in the list.")
    f.save(update_fields=["share_token"])
    return _back(f.folder)


# ---------- folder actions ----------

@login_required
@require_POST
def rename_folder(request, pk):
    folder = get_object_or_404(Folder, pk=pk, owner=request.user, is_trashed=False)
    name = request.POST.get("name", "").strip()[:255]
    if name:
        folder.name = name
        folder.save(update_fields=["name"])
    return _back(folder.parent)


@login_required
@require_POST
def trash_folder(request, pk):
    folder = get_object_or_404(Folder, pk=pk, owner=request.user, is_trashed=False)
    parent = folder.parent
    folder.set_trashed(True)
    File.objects.filter(owner=request.user, is_trashed=True).update(share_token=None)
    messages.success(request, f"Folder “{folder.name}” moved to Trash.")
    return _back(parent)


# ---------- trash ----------

@login_required
def trash(request):
    folders = Folder.objects.filter(owner=request.user, is_trashed=True).filter(
        Q(parent__isnull=True) | Q(parent__is_trashed=False)
    )
    files = File.objects.filter(owner=request.user, is_trashed=True).filter(
        Q(folder__isnull=True) | Q(folder__is_trashed=False)
    )
    return render(request, "drive/trash.html", {"folders": folders, "files": files})


@login_required
@require_POST
def restore(request, kind, pk):
    if kind == "file":
        f = get_object_or_404(File, pk=pk, owner=request.user, is_trashed=True)
        f.is_trashed = False
        f.save(update_fields=["is_trashed"])
    elif kind == "folder":
        folder = get_object_or_404(Folder, pk=pk, owner=request.user, is_trashed=True)
        folder.set_trashed(False)
    else:
        raise Http404
    messages.success(request, "Item restored.")
    return redirect("drive:trash")


@login_required
@require_POST
def delete_forever(request, kind, pk):
    if kind == "file":
        get_object_or_404(File, pk=pk, owner=request.user, is_trashed=True).delete()
    elif kind == "folder":
        get_object_or_404(Folder, pk=pk, owner=request.user, is_trashed=True).delete()
    else:
        raise Http404
    messages.success(request, "Deleted permanently.")
    return redirect("drive:trash")


@login_required
@require_POST
def empty_trash(request):
    for f in File.objects.filter(owner=request.user, is_trashed=True):
        f.delete()
    Folder.objects.filter(owner=request.user, is_trashed=True).delete()
    messages.success(request, "Trash emptied.")
    return redirect("drive:trash")


# ---------- public share link ----------

def shared(request, token):
    f = get_object_or_404(File, share_token=token, is_trashed=False)
    if request.GET.get("download"):
        return FileResponse(f.file.open("rb"), as_attachment=True, filename=f.name, content_type=f.guess_mime())
    return render(request, "drive/shared.html", {"file": f})
