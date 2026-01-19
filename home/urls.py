from django.contrib import admin
from django.urls import path
from home import views 

urlpatterns = [
    path("", views.allchats, name="all-chats"),
    path("login", views.loginUser, name="login"),
    path("logout", views.logoutUser, name="logout"),
    path("all-chats", views.allchats, name="all-chats"),
    path("featured-groups", views.featuredgroups, name="featured-groups"),
    path("about", views.about, name="about"),
    path("avatar-selection", views.avatarselection, name="avatar-selection"),
    path("edit-profile", views.editprofile, name="edit-profile"),
    path("register", views.registerUser, name="register"),
    path("setup-profile", views.setupProfile, name="setup-profile"),

]
