from django.contrib import admin
from .models import Agent, Assignment, AssignmentDetail

admin.site.register(Agent)
admin.site.register(Assignment)
admin.site.register(AssignmentDetail)
