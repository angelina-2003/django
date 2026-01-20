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
    

class Message(models.Model):
    chat=models.ForeignKey(PrivateChat, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User,on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username}: {self.text[:30]}"