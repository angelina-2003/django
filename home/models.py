from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    display_name = models.CharField(max_length=122, blank=True)
    avatar = models.CharField(max_length=122, default="default")

    age = models.PositiveIntegerField(null=True, blank=True)

    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
    ]
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        null=True,
        blank=True
    )

    PREFERENCE_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
        ("both", "Both"),
    ]
    preference = models.CharField(
        max_length=20,
        choices=PREFERENCE_CHOICES,
        null=True,
        blank=True
    )

    hush_points = models.PositiveIntegerField(default=0)
    
    # Gift counts
    love_letter_count = models.PositiveIntegerField(default=0)
    clove_count = models.PositiveIntegerField(default=0)
    golden_heart_count = models.PositiveIntegerField(default=0)
    pearl_count = models.PositiveIntegerField(default=0)
    
    # Message color (hex code, default to purple-blue theme)
    message_color = models.CharField(max_length=7, default="#4a3a6f", blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class PrivateChat(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats_started")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user1", "user2")

    def __str__(self):
        return f"Chat between {self.user1.username} and {self.user2.username} "
    

class Group(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default="👥", blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_groups")
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, through='GroupMember', related_name='group_memberships')

    def __str__(self):
        return f"{self.name} (Group)"

    def is_member(self, user=None):
        # If called from template without user parameter, use stored value from view
        if user is None:
            if hasattr(self, '_user_is_member'):
                return self._user_is_member
            # Fallback - return False if no user provided and no stored value
            return False
        # If called with user parameter, check stored value first (avoids caching issues)
        if hasattr(self, '_user_is_member'):
            # Creator is always a member
            if hasattr(self, '_user_is_creator') and self._user_is_creator and self.creator_id == user.id:
                return True
            # Return stored membership status if checking the same user context
            return self._user_is_member
        # Otherwise, query the database directly
        return GroupMember.objects.filter(group=self, user=user).exists()

    def is_creator(self, user=None):
        # If called from template without user parameter, use stored value from view
        if user is None:
            if hasattr(self, '_user_is_creator'):
                return self._user_is_creator
            return False
        # If called with user parameter, check stored value first (avoids caching issues)
        if hasattr(self, '_user_is_creator'):
            return self._user_is_creator
        # Otherwise, check normally
        return self.creator == user


class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="group_members")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    chat = models.ForeignKey(PrivateChat, on_delete=models.CASCADE, related_name="favorited_by", null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="favorited_by", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "chat"), ("user", "group")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.chat and not self.group:
            raise ValidationError("Favorite must have either a chat or a group")
        if self.chat and self.group:
            raise ValidationError("Favorite cannot have both a chat and a group")

    def __str__(self):
        if self.chat:
            return f"{self.user.username} favorited chat {self.chat.id}"
        return f"{self.user.username} favorited group {self.group.name}"


class Message(models.Model):
    chat = models.ForeignKey(PrivateChat, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.chat and not self.group:
            raise ValidationError("Message must have either a chat or a group")
        if self.chat and self.group:
            raise ValidationError("Message cannot have both a chat and a group")

    def __str__(self):
        return f"{self.sender.username}: {self.text[:30]}"

