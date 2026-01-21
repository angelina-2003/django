from django.shortcuts import render, HttpResponse, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages 
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import PrivateChat, Message, Group, GroupMember, Favorite
from django.db.models import Q, Max
from django.db import OperationalError, connection


def home(request):
    """Landing page - redirects to register if anonymous, otherwise to all-chats"""
    if request.user.is_anonymous:
        return redirect("/register")
    return redirect("/all-chats")


def _has_group_id_column():
    """Helper function to check if group_id column exists in home_message table"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='home_group'")
            if not cursor.fetchone():
                return False
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='home_message'")
            if not cursor.fetchone():
                return False
            cursor.execute("PRAGMA table_info(home_message)")
            columns = [row[1] for row in cursor.fetchall()]
            return 'group_id' in columns
    except (OperationalError, Exception):
        return False


def allchats(request):
    """All chats page - requires authentication"""
    if request.user.is_anonymous:
        return redirect("/login")
    
    # Check if profile is complete (must have display_name, age, gender, preference, and avatar)
    if hasattr(request.user, 'profile'):
        profile = request.user.profile
        if not profile.display_name or not profile.age or not profile.gender or not profile.preference or profile.avatar == "default":
            messages.info(request, "Please complete your profile setup first")
            return redirect("/setup-profile")
    
    # Get private chats with messages
    private_chats = (
        PrivateChat.objects
        .filter(Q(user1=request.user) | Q(user2=request.user))
        .annotate(last_message_time=Max("messages__created_at"))
        .filter(last_message_time__isnull=False)
        .order_by("-last_message_time")
    )
    
    # Get groups user is member of with messages
    # Handle case where migrations haven't been run yet (group_id column missing)
    # NEVER create a queryset with messages annotation if group_id column doesn't exist
    groups = Group.objects.none()  # Default to empty
    
    # Only query groups if group_id column exists in home_message table
    # The annotation will fail if the column doesn't exist because Django tries to join the tables
    has_column = _has_group_id_column()
    if has_column:
        try:
            # Create queryset only after confirming column exists
            groups_query = (
                Group.objects
                .filter(members=request.user)
                .annotate(last_message_time=Max("messages__created_at"))
                .filter(last_message_time__isnull=False)
                .order_by("-last_message_time")
            )
            # Test evaluation to ensure query works
            try:
                _ = list(groups_query[:1])
                groups = groups_query
            except (OperationalError, Exception) as e:
                # Even though column check passed, query failed - likely column still missing
                groups = Group.objects.none()
        except (OperationalError, Exception):
            # If query creation fails for any reason, use empty queryset
            groups = Group.objects.none()

    # Get selected chat or group
    selected_chat = None
    selected_group = None
    other_user = None
    chat_id = request.GET.get('chat_id')
    group_id = request.GET.get('group_id')
    
    if chat_id:
        try:
            selected_chat = get_object_or_404(PrivateChat, id=chat_id)
            if request.user in [selected_chat.user1, selected_chat.user2]:
                other_user = selected_chat.user2 if selected_chat.user1 == request.user else selected_chat.user1
        except:
            selected_chat = None
    
    if group_id:
        # Only allow selected_group if group_id column exists (template will query messages)
        if not _has_group_id_column():
            selected_group = None
        else:
            try:
                # Get a fresh instance of the group - don't use prefetch to avoid caching
                selected_group = Group.objects.get(id=group_id)
                # Check membership - creator is always considered a member
                # Use a direct query to check membership to avoid caching issues
                is_creator = selected_group.creator_id == request.user.id
                is_member = GroupMember.objects.filter(group=selected_group, user=request.user).exists()
                
                # Store membership in the group object for template use
                # This ensures the template gets the correct membership status
                selected_group._user_is_creator = is_creator
                selected_group._user_is_member = is_member
                
                if is_creator or is_member:
                    # User is creator or member - allow access
                    # Test if we can actually query messages (double-check)
                    try:
                        _ = list(selected_group.messages.all()[:1])
                    except (OperationalError, Exception):
                        # Database column doesn't exist yet - migrations not run
                        selected_group = None
                else:
                    # User is not a member - allow viewing but not messaging (handled in template)
                    pass
            except Group.DoesNotExist:
                selected_group = None
            except (OperationalError, Exception):
                # If any error occurs, set to None
                selected_group = None

    # Handle message sending
    if request.method == "POST":
        message_text = request.POST.get("message", "").strip()
        if message_text:
            if selected_chat:
                Message.objects.create(
                    chat=selected_chat,
                    sender=request.user,
                    text=message_text
                )
                return redirect(f"/all-chats?chat_id={selected_chat.id}")
            elif selected_group:
                try:
                    if selected_group.is_member(request.user):
                        Message.objects.create(
                            group=selected_group,
                            sender=request.user,
                            text=message_text
                        )
                        return redirect(f"/all-chats?group_id={selected_group.id}")
                except Exception:
                    # Database column doesn't exist - migrations not run
                    messages.error(request, "Group messaging not available yet. Please run migrations.")
                    return redirect("/all-chats")

    # Always set membership info on selected_group for template use
    # Also pass as separate context variables for more reliable template access
    is_group_creator = False
    is_group_member = False
    
    if selected_group:
        if hasattr(request.user, 'id'):
            # Re-check membership to ensure it's always up to date (handles case where user just joined)
            is_creator = bool(selected_group.creator_id == request.user.id)
            is_member = bool(GroupMember.objects.filter(group=selected_group, user=request.user).exists())
            selected_group._user_is_creator = is_creator
            selected_group._user_is_member = is_member
            is_group_creator = is_creator
            is_group_member = is_member
        else:
            # Fallback for anonymous users
            selected_group._user_is_creator = False
            selected_group._user_is_member = False
    
    # Get filter from request
    filter_type = request.GET.get('filter', 'all')
    
    # Get user's favorites (handle case where table doesn't exist yet)
    favorite_chat_ids = set()
    favorite_group_ids = set()
    try:
        favorite_chat_ids = set(Favorite.objects.filter(user=request.user, chat__isnull=False).values_list('chat_id', flat=True))
        favorite_group_ids = set(Favorite.objects.filter(user=request.user, group__isnull=False).values_list('group_id', flat=True))
    except (OperationalError, Exception):
        # Table doesn't exist yet - migrations not run
        favorite_chat_ids = set()
        favorite_group_ids = set()
    
    # Apply filtering based on filter_type
    if filter_type == 'private':
        # Show only private chats
        groups = Group.objects.none()
    elif filter_type == 'group':
        # Show only groups
        private_chats = PrivateChat.objects.none()
    elif filter_type == 'heart':
        # Show only favorited chats and groups
        private_chats = private_chats.filter(id__in=favorite_chat_ids)
        if has_column and groups.exists():
            groups = groups.filter(id__in=favorite_group_ids)
        else:
            groups = Group.objects.none()
    # filter_type == 'all' shows both, no filtering needed
    
    # Get gift counts for other_user if private chat is selected
    other_user_gift_counts = {
        'love_letter': 0,
        'clove': 0,
        'golden_heart': 0,
        'pearl': 0,
    }
    if other_user and hasattr(other_user, 'profile'):
        other_user_gift_counts = {
            'love_letter': other_user.profile.love_letter_count,
            'clove': other_user.profile.clove_count,
            'golden_heart': other_user.profile.golden_heart_count,
            'pearl': other_user.profile.pearl_count,
        }
    
    return render(request, "all-chats.html", {
        "private_chats": private_chats,
        "groups": groups,
        "selected_chat": selected_chat,
        "selected_group": selected_group,
        "other_user": other_user,
        "is_group_creator": is_group_creator,
        "is_group_member": is_group_member,
        "filter_type": filter_type,
        "favorite_chat_ids": favorite_chat_ids,
        "favorite_group_ids": favorite_group_ids,
        "other_user_gift_counts": other_user_gift_counts,
    })


def about(request):
    return HttpResponse("This is about page")


@login_required
def featuredgroups(request):
    # This view is now just for the modal - actual search happens via API
    return render(request, "featured-groups.html")


@login_required
def search_groups(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse({"results": []})

    groups = Group.objects.filter(
        name__icontains=query
    )[:10]

    results = []
    for group in groups:
        results.append({
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "member_count": group.members.count(),
            "is_member": group.is_member(request.user),
        })

    return JsonResponse({"results": results})


@login_required
def create_group(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, "Group name is required")
            return render(request, "create-group.html")

        # Check if group_id column exists before creating group
        if not _has_group_id_column():
            messages.error(request, "Group features are not available yet. Please run migrations.")
            return render(request, "create-group.html")

        group = Group.objects.create(
            name=name,
            description=description,
            creator=request.user
        )
        # Creator automatically becomes a member - add them immediately
        GroupMember.objects.create(group=group, user=request.user)
        
        # Get a fresh instance to ensure ManyToMany relationship is loaded
        # refresh_from_db() doesn't refresh ManyToMany relationships
        group = Group.objects.get(id=group.id)
        
        return redirect(f"/all-chats?group_id={group.id}")

    return render(request, "create-group.html")


@login_required
def join_group(request, group_id):
    # Check if group_id column exists
    if not _has_group_id_column():
        messages.error(request, "Group features are not available yet. Please run migrations.")
        return redirect("/all-chats")
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == "POST":
        # Check membership using direct query to avoid caching issues
        is_already_member = GroupMember.objects.filter(group=group, user=request.user).exists()
        
        if not is_already_member:
            GroupMember.objects.create(group=group, user=request.user)
            messages.success(request, f"You joined {group.name}")
        else:
            messages.info(request, f"You are already a member of {group.name}")
        
        # Redirect - the allchats view will reload with fresh membership data
        return redirect(f"/all-chats?group_id={group.id}")
    
    return redirect("/all-chats")


@login_required
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    if group.is_member(request.user):
        if group.is_creator(request.user):
            messages.error(request, "Group creator cannot leave the group")
        else:
            GroupMember.objects.filter(group=group, user=request.user).delete()
            messages.success(request, f"You left {group.name}")
    
    return redirect("/all-chats")


def avatarselection(request):
    return render(request, "avatar-selection.html")


@login_required
def view_profile(request):
    """Display user's profile"""
    try:
        profile = request.user.profile
    except:
        # If profile doesn't exist, create one
        from .models import Profile
        profile = Profile.objects.create(user=request.user)
    
    # Ensure we have the latest data from database
    profile.refresh_from_db()
    
    # Get gift counts from profile
    gift_counts = {
        'love_letter': profile.love_letter_count,
        'clove': profile.clove_count,
        'golden_heart': profile.golden_heart_count,
        'pearl': profile.pearl_count,
    }
    
    return render(request, "profile.html", {"profile": profile, "gift_counts": gift_counts})


@login_required
def editprofile(request):
    """Edit user's profile"""
    profile = request.user.profile
    
    # List of available avatars
    available_avatars = ["brownbear", "cat", "cow", "gorilla", "lion", "panda", "panther", "smalldog"]
    
    if request.method == "POST":
        display_name = request.POST.get("display_name", "").strip()
        age = request.POST.get("age", "").strip()
        gender = request.POST.get("gender", "").strip()
        preference = request.POST.get("preference", "").strip()
        avatar = request.POST.get("avatar", "").strip()
        
        if display_name:
            profile.display_name = display_name
        if age:
            try:
                profile.age = int(age)
            except ValueError:
                pass
        if gender in ["male", "female"]:
            profile.gender = gender
        if preference in ["male", "female", "both"]:
            profile.preference = preference
        if avatar:
            profile.avatar = avatar
        
        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("/profile")
    
    return render(request, "edit-profile.html", {
        "profile": profile,
        "available_avatars": available_avatars
    })


def loginUser(request):
    # If already logged in, redirect to all-chats
    if not request.user.is_anonymous:
        return redirect("/all-chats")
    
    # check if user has entered correct credentials
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user) 
            return redirect("/all-chats")
        else: 
            messages.error(request, "Invalid username or password")
            return render(request, "login.html")
        
    return render(request, "login.html")


def logoutUser(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("/register")


def registerUser(request):
    # If already logged in, redirect to all-chats
    if not request.user.is_anonymous:
        return redirect("/all-chats")
    
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # basic validation
        if not username or not password1 or not password2:
            messages.error(request, "All fields are required")
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
    available_avatars = ["brownbear", "cat", "cow", "gorilla", "lion", "panda", "panther", "smalldog"]

    # Check if profile is already complete - redirect to all-chats if it is
    if profile.display_name and profile.age and profile.gender and profile.preference and profile.avatar != "default":
        messages.info(request, "Your profile is already complete")
        return redirect("/all-chats")

    if request.method == "POST":
        profile.display_name = request.POST.get("name", "").strip()
        
        age_str = request.POST.get("age", "").strip()
        if age_str:
            try:
                profile.age = int(age_str)
            except ValueError:
                pass
        
        gender = request.POST.get("gender", "").strip()
        if gender:
            profile.gender = gender
        
        preference = request.POST.get("interested_in", "").strip()
        if preference:
            profile.preference = preference

        # Avatar is required
        avatar = request.POST.get("avatar", "").strip()
        if avatar and avatar in available_avatars:
            profile.avatar = avatar
        else:
            messages.error(request, "Please select a valid avatar")
            return render(request, "setup-profile.html", {
                "available_avatars": available_avatars
            })

        profile.save()

        return redirect("/all-chats")

    return render(request, "setup-profile.html", {
        "available_avatars": available_avatars
    })


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

    # Redirect to all-chats with the chat_id to open the chat
    # The chat won't appear in the list until a message is sent
    return redirect(f"/all-chats?chat_id={chat.id}")


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
        avatar = "default"
        message_color = "#4a3a6f"  # Default color
        if hasattr(msg.sender, 'profile'):
            if msg.sender.profile.avatar:
                avatar = msg.sender.profile.avatar
            if msg.sender.profile.message_color:
                message_color = msg.sender.profile.message_color
        data.append({
            "id": msg.id,
            "text": msg.text,
            "sender": msg.sender.username,
            "user_id": msg.sender.id,
            "is_me": msg.sender == request.user,
            "avatar": avatar,
            "message_color": message_color,
            "created_at": msg.created_at.strftime("%H:%M"),
        })

    return JsonResponse({"messages": data})


@login_required
def poll_chats(request):
    """Poll for chat list updates - returns all chats and groups with last message info"""
    # Get private chats
    # Handle case where migrations haven't been run yet
    try:
        private_chats = (
            PrivateChat.objects
            .filter(Q(user1=request.user) | Q(user2=request.user))
            .annotate(last_message_time=Max("messages__created_at"))
            .filter(last_message_time__isnull=False)
            .order_by("-last_message_time")
        )
    except Exception:
        # If migrations haven't been run, return empty queryset
        private_chats = PrivateChat.objects.none()
    
    # Get groups
    groups = (
        Group.objects
        .filter(members=request.user)
        .annotate(last_message_time=Max("messages__created_at"))
        .filter(last_message_time__isnull=False)
        .order_by("-last_message_time")
    )

    chats_data = []
    
    # Process private chats
    for chat in private_chats:
        other_user = chat.user2 if chat.user1 == request.user else chat.user1
        last_message = chat.messages.last()
        
        other_user_avatar = "default"
        if hasattr(other_user, 'profile') and other_user.profile.avatar:
            other_user_avatar = other_user.profile.avatar
        
        chat_data = {
            "type": "private",
            "id": chat.id,
            "other_user": {
                "id": other_user.id,
                "username": other_user.username,
                "avatar": other_user_avatar,
            },
            "last_message": None,
            "last_message_time": chat.last_message_time.isoformat() if chat.last_message_time else None,
        }
        
        if last_message:
            chat_data["last_message"] = {
                "text": last_message.text,
                "sender_username": last_message.sender.username,
                "is_from_me": last_message.sender == request.user,
                "created_at": last_message.created_at.strftime("%H:%M"),
            }
        
        chats_data.append(chat_data)
    
    # Process groups
    for group in groups:
        last_message = group.messages.last()
        
        chat_data = {
            "type": "group",
            "id": group.id,
            "name": group.name,
            "member_count": group.members.count(),
            "last_message": None,
            "last_message_time": group.last_message_time.isoformat() if group.last_message_time else None,
        }
        
        if last_message:
            chat_data["last_message"] = {
                "text": last_message.text,
                "sender_username": last_message.sender.username,
                "is_from_me": last_message.sender == request.user,
                "created_at": last_message.created_at.strftime("%H:%M"),
            }
        
        chats_data.append(chat_data)
    
    # Sort by last_message_time
    chats_data.sort(key=lambda x: x["last_message_time"] if x["last_message_time"] else "", reverse=True)
    
    return JsonResponse({"chats": chats_data})


@login_required
def toggle_favorite(request):
    """Toggle favorite status for a chat or group"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Check if Favorite table exists
    try:
        # Try a simple query to check if table exists
        Favorite.objects.exists()
    except (OperationalError, Exception) as e:
        return JsonResponse({"error": f"Favorites feature not available. Please run migrations. Error: {str(e)}"}, status=503)
    
    chat_id = request.POST.get("chat_id")
    group_id = request.POST.get("group_id")
    
    if not chat_id and not group_id:
        return JsonResponse({"error": "chat_id or group_id required"}, status=400)
    
    if chat_id:
        try:
            chat = get_object_or_404(PrivateChat, id=chat_id)
            # Verify user is part of this chat
            if request.user not in [chat.user1, chat.user2]:
                return JsonResponse({"error": "Unauthorized"}, status=403)
            
            # Check if already favorited
            existing_favorite = Favorite.objects.filter(user=request.user, chat=chat).first()
            
            if existing_favorite:
                # Already favorited, remove it
                existing_favorite.delete()
                return JsonResponse({"favorited": False, "success": True})
            else:
                # Not favorited, create it
                try:
                    favorite = Favorite(user=request.user, chat=chat, group=None)
                    favorite.full_clean()  # Validate before saving
                    favorite.save()
                    return JsonResponse({"favorited": True, "success": True})
                except Exception as validation_error:
                    import traceback
                    return JsonResponse({"error": f"Validation error: {str(validation_error)}", "traceback": traceback.format_exc()}, status=400)
        except Exception as e:
            import traceback
            return JsonResponse({"error": str(e), "traceback": traceback.format_exc()}, status=400)
    
    elif group_id:
        try:
            group = get_object_or_404(Group, id=group_id)
            # Verify user is a member
            is_member = GroupMember.objects.filter(group=group, user=request.user).exists()
            is_creator = group.creator_id == request.user.id
            if not is_member and not is_creator:
                return JsonResponse({"error": "Unauthorized"}, status=403)
            
            # Check if already favorited
            existing_favorite = Favorite.objects.filter(user=request.user, group=group).first()
            
            if existing_favorite:
                # Already favorited, remove it
                existing_favorite.delete()
                return JsonResponse({"favorited": False, "success": True})
            else:
                # Not favorited, create it
                try:
                    favorite = Favorite(user=request.user, chat=None, group=group)
                    favorite.full_clean()  # Validate before saving
                    favorite.save()
                    return JsonResponse({"favorited": True, "success": True})
                except Exception as validation_error:
                    import traceback
                    return JsonResponse({"error": f"Validation error: {str(validation_error)}", "traceback": traceback.format_exc()}, status=400)
        except Exception as e:
            import traceback
            return JsonResponse({"error": str(e), "traceback": traceback.format_exc()}, status=400)
    
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def get_user_profile(request, user_id):
    """API endpoint to get user profile data"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Get profile data
        profile = user.profile
        gift_counts = {
            'love_letter': profile.love_letter_count,
            'clove': profile.clove_count,
            'golden_heart': profile.golden_heart_count,
            'pearl': profile.pearl_count,
        }
        
        return JsonResponse({
            'username': user.username,
            'display_name': profile.display_name,
            'avatar': profile.avatar,
            'age': profile.age,
            'gender': profile.gender,
            'hush_points': profile.hush_points,
            'gift_counts': gift_counts,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def update_group_description(request, group_id):
    """API endpoint to update group description"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        group = get_object_or_404(Group, id=group_id)
        
        # Check if user is the creator
        if group.creator != request.user:
            return JsonResponse({"error": "Only the group creator can update the description"}, status=403)
        
        import json
        data = json.loads(request.body)
        description = data.get('description', '').strip()
        
        group.description = description
        group.save()
        
        return JsonResponse({"success": True, "description": description})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def update_group_name(request, group_id):
    """API endpoint to update group name"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        group = get_object_or_404(Group, id=group_id)
        
        # Check if user is the creator
        if group.creator != request.user:
            return JsonResponse({"error": "Only the group creator can update the group name"}, status=403)
        
        import json
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        
        if not name:
            return JsonResponse({"error": "Group name cannot be empty"}, status=400)
        
        if len(name) > 255:
            return JsonResponse({"error": "Group name is too long (max 255 characters)"}, status=400)
        
        group.name = name
        group.save()
        
        return JsonResponse({"success": True, "name": name})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def update_group_icon(request, group_id):
    """API endpoint to update group icon (emoji)"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        group = get_object_or_404(Group, id=group_id)
        
        # Check if user is the creator
        if group.creator != request.user:
            return JsonResponse({"error": "Only the group creator can update the group icon"}, status=403)
        
        import json
        import re
        
        # Decode request body properly to handle emojis
        # Django's request.body is bytes, need to decode to string
        try:
            # Decode with UTF-8, handling surrogates properly
            if isinstance(request.body, bytes):
                body_str = request.body.decode('utf-8', errors='surrogatepass')
            else:
                body_str = str(request.body)
        except (UnicodeDecodeError, AttributeError):
            # Fallback: try with replace errors
            try:
                body_str = request.body.decode('utf-8', errors='replace')
            except:
                body_str = str(request.body)
        
        data = json.loads(body_str)
        icon = data.get('icon', '👥')
        
        # Ensure icon is a string and strip whitespace
        if isinstance(icon, str):
            icon = icon.strip()
        else:
            icon = str(icon).strip()
        
        # If empty, use default
        if not icon:
            icon = '👥'
        
        # Limit to single emoji/character (handle emojis properly)
        # Use list() to properly handle emojis which can be multiple code points
        icon_chars = list(icon)
        if len(icon_chars) > 1:
            icon = icon_chars[0]
        elif len(icon_chars) == 1:
            icon = icon_chars[0]
        
        # Block regular ASCII letters and numbers
        if icon and re.match(r'^[a-zA-Z0-9\s!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]+$', icon):
            return JsonResponse({"error": "Icon must be an emoji, not regular text"}, status=400)
        
        # Ensure the icon is properly encoded before saving
        # Convert any surrogate pairs to proper UTF-8
        try:
            # Encode and decode to normalize the emoji
            icon_bytes = icon.encode('utf-8', errors='surrogatepass')
            icon = icon_bytes.decode('utf-8', errors='replace')
        except:
            pass  # If encoding fails, use the icon as-is
        
        group.icon = icon or '👥'
        group.save()
        
        # Ensure the response is properly encoded
        response_data = {"success": True, "icon": group.icon}
        response = JsonResponse(response_data, json_dumps_params={'ensure_ascii': False})
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def update_message_color(request):
    """API endpoint to update user's message color"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        color = data.get('color', '').strip()
        
        # Validate hex color format
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            return JsonResponse({"error": "Invalid color format. Must be a hex color (e.g., #4a3a6f)"}, status=400)
        
        profile = request.user.profile
        profile.message_color = color
        profile.save()
        
        return JsonResponse({"success": True, "color": color})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def delete_chat(request, chat_id):
    """API endpoint to delete a private chat and all its messages"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        from home.models import PrivateChat, Message, Favorite
        
        chat = get_object_or_404(PrivateChat, id=chat_id)
        
        # Check if user is part of this chat
        if request.user not in [chat.user1, chat.user2]:
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        # Delete all messages in this chat
        Message.objects.filter(chat=chat).delete()
        
        # Delete all favorites for this chat
        Favorite.objects.filter(chat=chat).delete()
        
        # Delete the chat itself
        chat.delete()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def delete_group_chat(request, group_id):
    """API endpoint to leave/delete a group chat"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        from home.models import Group, GroupMember, Message, Favorite
        
        group = get_object_or_404(Group, id=group_id)
        
        # Check if user is a member
        if not group.members.filter(id=request.user.id).exists() and group.creator != request.user:
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        # If user is the creator, delete the entire group
        if group.creator == request.user:
            # Delete all messages
            Message.objects.filter(group=group).delete()
            # Delete all favorites
            Favorite.objects.filter(group=group).delete()
            # Delete all group members
            GroupMember.objects.filter(group=group).delete()
            # Delete the group
            group.delete()
        else:
            # Just remove the user from the group
            GroupMember.objects.filter(group=group, user=request.user).delete()
            # Delete user's favorites for this group
            Favorite.objects.filter(group=group, user=request.user).delete()
        
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

