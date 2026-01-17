from django.contrib import admin
from django.urls import path
from home import views 

urlpatterns = [
    path("", views.index, name="home"),
    path("chats", views.index, name="chats"),
    path("featured-groups", views.featuredgroups, name="featured-groups"),
    path("about", views.about, name="about"),
    path("avatar-selection", views.avatarselection, name="avatar-selection")
]
