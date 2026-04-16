from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "company", "job_title", "parsed_date", "apply_link", "last_seen"]

    