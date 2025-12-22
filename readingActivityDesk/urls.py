# readingActivityDesk/urls.py
from django.urls import path
from . import views  # we'll add view classes in next step

urlpatterns = [
    path("in-progress/", views.InProgressListView.as_view()),
    path("finished/", views.FinishedListView.as_view()),
    path("progress/", views.ProgressUpsertView.as_view()),
    path("mark-finished/", views.MarkFinishedView.as_view()),
    path("item/", views.RemoveItemView.as_view()),
]