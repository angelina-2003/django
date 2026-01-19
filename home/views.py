from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages 
from django.contrib.auth.decorators import login_required


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


def registerUser(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # basic validation
        if not username or not password1 or not password2:
            messages.error(request, "All field are required")
            return redirect("/register")
        
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("/register")
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("/register")
        
        # create user 
        user = User.objects.create_user(
            username=username,
            password=password1
        )

        #log user in
        login(request, user)

        # redirect to profile setup
        return redirect("/setup-profile")
    
    return render(request, "register.html")



@login_required
def setupProfile(request):
    profile = request.user.profile

    if request.method == "POST":
        
        profile.display_name = request.POST.get("name")
        profile.age = request.POST.get("age")
        profile.gender = request.POST.get("gender")
        profile.preference = request.POST.get("interested_in")

        profile.save()

        return redirect("/all-chats")

    return render(request, "setup-profile.html")