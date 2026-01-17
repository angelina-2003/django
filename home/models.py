from django.db import models

# Create your models here.

class Profile(models.Model):
    username = models.CharField(max_length=122)
    display_name = models.CharField(max_length=122)
    avatar = models.CharField(max_length=122)
    age = models.CharField(max_length=122)
    gender = models.CharField(max_length=122)
    preference = models.CharField(max_length=122)
    email = models.CharField(max_length=122)
    phone = models.CharField(max_length=12)
    hush_points = models.CharField(max_length=12)