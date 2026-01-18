from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

# Create your views here.

def allchats(request):
    if request.user.is_anonymous:
        return redirect("/login")
    return render(request, "all-chats.html")

def about(request):
    return HttpResponse("This is about page")

def featuredgroups(request):
    return render (request, "featured-groups.html")

def avatarselection(request):
    return render(request, "avatar-selection.html")

def editprofile(request):
    return render(request, "edit-profile.html")


def loginUser(request):
    # check if user has entered correct credentials
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user) 
            return redirect("/all-chats")
        else: 
            return render(request, "login.html")
        
    return render(request, "login.html")

def logoutUser(request):
    logout(request)
    return redirect("/login")