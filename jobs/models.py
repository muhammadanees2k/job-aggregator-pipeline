from django.db import models
from django.utils import timezone

class Job(models.Model):
    company = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    apply_link = models.URLField(max_length=700, unique=True)
    posted_date_raw = models.CharField(max_length=100, blank=True, null=True)
    parsed_date = models.DateField(blank=True, null=True)  # Mathematical date for perfect sorting
    last_seen = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        # Forces Django to always return newest dates first, falling back to ID
        ordering = ['-parsed_date', '-id']

    def __str__(self):
        return f"{self.job_title} at {self.company}"

class ScraperLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')])
    message = models.TextField()
    jobs_added = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Scraper Log"
        verbose_name_plural = "Scraper Logs"
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.status}] - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"