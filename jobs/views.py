from django.shortcuts import render
from django.core.paginator import Paginator
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Job
from .serializers import JobSerializer

class JobViewSet(ListModelMixin, GenericViewSet):
    queryset = Job.objects.filter(is_active=True).order_by('-parsed_date', '-id')
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["company"]
    search_fields = ["job_title"]

def job_board(request):
    company_filter = request.GET.get("company")
    jobs = Job.objects.filter(is_active=True).order_by("-parsed_date")
    
    if company_filter:
        jobs = jobs.filter(company=company_filter)

    paginator = Paginator(jobs, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "jobs/job_board.html", {
        "page_obj": page_obj,
        "company_filter": company_filter
    })