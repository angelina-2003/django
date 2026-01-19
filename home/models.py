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

