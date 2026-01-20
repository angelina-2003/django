from django.contrib import admin
from home.models import Profile, PrivateChat, Message, Group, GroupMember

# Register your models here.

admin.site.register(Profile)
admin.site.register(PrivateChat)
admin.site.register(Message)
admin.site.register(Group)
admin.site.register(GroupMember)