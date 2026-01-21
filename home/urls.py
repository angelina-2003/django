from django.contrib import admin
from django.urls import path
from home import views 
from home.views import chat_room

urlpatterns = [
    path("", views.home, name="home"),  # Landing page - redirects to register or all-chats
    path("register", views.registerUser, name="register"),
    path("login", views.loginUser, name="login"),
    path("logout", views.logoutUser, name="logout"),
    path("all-chats", views.allchats, name="all-chats"),
    path("featured-groups", views.featuredgroups, name="featured-groups"),
    path("about", views.about, name="about"),
    path("avatar-selection", views.avatarselection, name="avatar-selection"),
    path("profile", views.view_profile, name="profile"),
    path("edit-profile", views.editprofile, name="edit-profile"),
    path("setup-profile", views.setupProfile, name="setup-profile"),
    path("api/search-user/", views.search_user, name="search-user"),
    path("api/search-groups/", views.search_groups, name="search-groups"),
    path("chat/<int:chat_id>/", chat_room, name="chat-room"),
    path("start-chat/", views.start_chat, name="start-chat"),
    path("api/poll-messages/<int:chat_id>/", views.poll_messages, name="poll-messages"),
    path("api/poll-chats/", views.poll_chats, name="poll-chats"),
    path("create-group/", views.create_group, name="create-group"),
    path("join-group/<int:group_id>/", views.join_group, name="join-group"),
    path("leave-group/<int:group_id>/", views.leave_group, name="leave-group"),
    path("api/toggle-favorite/", views.toggle_favorite, name="toggle-favorite"),
    path("api/user-profile/<int:user_id>/", views.get_user_profile, name="get-user-profile"),
    path("api/update-group-description/<int:group_id>/", views.update_group_description, name="update-group-description"),
    path("api/update-group-name/<int:group_id>/", views.update_group_name, name="update-group-name"),
    path("api/update-group-icon/<int:group_id>/", views.update_group_icon, name="update-group-icon"),
    path("api/update-message-color/", views.update_message_color, name="update-message-color"),
    path("api/delete-chat/<int:chat_id>/", views.delete_chat, name="delete-chat"),
    path("api/delete-group-chat/<int:group_id>/", views.delete_group_chat, name="delete-group-chat"),

]
