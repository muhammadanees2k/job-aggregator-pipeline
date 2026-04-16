from django.contrib import admin
from .models import Job, ScraperLog

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'company', 'parsed_date', 'is_active')
    list_filter = ('company', 'is_active', 'parsed_date')
    search_fields = ('job_title', 'company')

@admin.register(ScraperLog)
class ScraperLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'status', 'jobs_added', 'message')
    list_filter = ('status', 'timestamp')
    search_fields = ('message',)
    
    # Prevent creating, editing, or deleting logs manually from the admin panel
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False