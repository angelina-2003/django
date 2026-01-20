from django.contrib import admin
from django.urls import path
from home import views 
from home.views import chat_room

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
    path("api/search-user/", views.search_user, name="search-user"),
    path("chat/<int:chat_id>/", chat_room, name="chat-room"),
    path("start-chat/", views.start_chat, name="start-chat"),
    path("api/poll-messages/<int:chat_id>/", views.poll_messages, name="poll-messages"),

]
