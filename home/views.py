from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import PrivateChat, Message
from django.db.models import Q, Max


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
    messages.success(request, "You have been logged out successfully.")
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


@login_required
def search_user(request):
    query = request.GET.get("q", "").strip()

    if not query: 
        return JsonResponse({"results": []})
    
    users = User.objects.filter(
        username__icontains=query
    ).exclude(id=request.user.id)[:10]

    results = []

    for user in users:
        results.append({
            "id":user.id,
            "username":user.username,
        })

    return JsonResponse({"results": results})


@login_required
def start_chat(request):
    if request.method != "POST":
        return redirect("/all-chats")

    other_user_id = request.POST.get("user_id")
    other_user = get_object_or_404(User, id=other_user_id)

    # prevent chatting with yourself
    if other_user == request.user:
        return redirect("/all-chats")

    # ensure consistent ordering (important!)
    user1, user2 = sorted(
        [request.user, other_user],
        key=lambda u: u.id
    )

    chat, created = PrivateChat.objects.get_or_create(
        user1=user1,
        user2=user2
    )

    return redirect(f"/chat/{chat.id}/")


@login_required
def chat_room(request, chat_id):
    chat = get_object_or_404(PrivateChat, id=chat_id)
    
    # Ensure user is part of this chat
    if request.user not in [chat.user1, chat.user2]:
        return redirect("/all-chats")
    
    # Handle message sending
    if request.method == "POST":
        message_text = request.POST.get("message", "").strip()
        if message_text:
            from .models import Message
            Message.objects.create(
                chat=chat,
                sender=request.user,
                text=message_text
            )
        return redirect(f"/chat/{chat_id}/")
    
    # Get other user
    other_user = chat.user2 if chat.user1 == request.user else chat.user1
    
    return render(request, "chat-room.html", {
        "chat": chat,
        "other_user": other_user
    })


@login_required
def allchats(request):
    chats = (
        PrivateChat.objects
        .filter(Q(user1=request.user) | Q(user2=request.user))
        .annotate(last_message_time=Max("messages__created_at"))
        .order_by("-last_message_time")
    )

    # Get selected chat if chat_id is provided
    selected_chat = None
    other_user = None
    chat_id = request.GET.get('chat_id')
    
    if chat_id:
        try:
            selected_chat = get_object_or_404(PrivateChat, id=chat_id)
            # Ensure user is part of this chat
            if request.user in [selected_chat.user1, selected_chat.user2]:
                other_user = selected_chat.user2 if selected_chat.user1 == request.user else selected_chat.user1
        except:
            selected_chat = None

    # Handle message sending
    if request.method == "POST" and selected_chat:
        message_text = request.POST.get("message", "").strip()
        if message_text:
            from .models import Message
            Message.objects.create(
                chat=selected_chat,
                sender=request.user,
                text=message_text
            )
        return redirect(f"/all-chats?chat_id={selected_chat.id}")

    return render(request, "all-chats.html", {
        "chats": chats,
        "selected_chat": selected_chat,
        "other_user": other_user
    })


@login_required
def poll_messages(request, chat_id):
    # Get the chat and ensure user is part of it
    try:
        chat = get_object_or_404(PrivateChat, id=chat_id)
        if request.user not in [chat.user1, chat.user2]:
            return JsonResponse({"error": "Unauthorized"}, status=403)
    except:
        return JsonResponse({"error": "Chat not found"}, status=404)

    last_id = request.GET.get("last_id")

    # Filter messages for this chat only
    messages = Message.objects.filter(chat_id=chat_id).order_by("id")

    # Filter by last_id if provided
    if last_id:
        try:
            last_id_int = int(last_id)
            messages = messages.filter(id__gt=last_id_int)
        except (ValueError, TypeError):
            # Invalid last_id, ignore it and return all messages
            pass

    data = []
    for msg in messages:
        data.append({
            "id": msg.id,
            "text": msg.text,
            "sender": msg.sender.username,
            "is_me": msg.sender == request.user,
            "created_at": msg.created_at.strftime("%H:%M"),
        })

    return JsonResponse({"messages": data})


