from django.contrib import admin
from .models import Request, RequestHistory

# Register your models here.


admin.site.register(Request)
admin.site.register(RequestHistory)