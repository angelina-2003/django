from django.contrib import admin
from home.models import Profile, PrivateChat, Message

# Register your models here.

admin.site.register(Profile)
admin.site.register(PrivateChat)
admin.site.register(Message)