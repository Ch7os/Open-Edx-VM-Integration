from django.urls import path

from .api.views import AdminInstanceView, LearnerLabView

urlpatterns = [
    path("<path:course_id>/<path:block_id>/<str:action>", LearnerLabView.as_view(), name="htblab-learner"),
    path("admin/instances", AdminInstanceView.as_view(), name="htblab-admin-list"),
    path("admin/<int:instance_id>/action", AdminInstanceView.as_view(), name="htblab-admin-action"),
]
