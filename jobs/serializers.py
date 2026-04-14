from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "company", "job_title", "posted_date_raw", "apply_link", "last_seen"]

    