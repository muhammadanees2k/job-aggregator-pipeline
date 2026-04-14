from django.db import models
from django.utils import timezone


class Job(models.Model):
    company = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    posted_date_raw = models.CharField(max_length=255)
    apply_link = models.URLField(max_length=700, unique=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.job_title} at {self.company}"
