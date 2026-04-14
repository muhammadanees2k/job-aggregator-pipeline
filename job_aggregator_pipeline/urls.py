from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from jobs.views import JobViewSet, job_board

router = DefaultRouter()
router.register(r"jobs",  viewset=JobViewSet, basename="job")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('', job_board, name= "job_board")
]
