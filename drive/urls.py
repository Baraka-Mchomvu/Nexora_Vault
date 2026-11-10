from django.urls import path

from . import views

app_name = "drive"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("folder/<int:folder_id>/", views.dashboard, name="folder"),
    path("signup/", views.signup, name="signup"),

    path("folder/create/", views.create_folder, name="create_folder"),
    path("upload/", views.upload, name="upload"),

    path("file/<int:pk>/download/", views.download, name="download"),
    path("file/<int:pk>/rename/", views.rename_file, name="rename_file"),
    path("file/<int:pk>/trash/", views.trash_file, name="trash_file"),
    path("file/<int:pk>/share/", views.toggle_share, name="toggle_share"),
    path("folder/<int:pk>/rename/", views.rename_folder, name="rename_folder"),
    path("folder/<int:pk>/trash/", views.trash_folder, name="trash_folder"),

    path("trash/", views.trash, name="trash"),
    path("trash/restore/<str:kind>/<int:pk>/", views.restore, name="restore"),
    path("trash/delete/<str:kind>/<int:pk>/", views.delete_forever, name="delete_forever"),
    path("trash/empty/", views.empty_trash, name="empty_trash"),

    path("s/<str:token>/", views.shared, name="shared"),
]
