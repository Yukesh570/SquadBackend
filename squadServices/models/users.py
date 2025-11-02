from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class UserType(models.TextChoices):
    ADMIN = "ADMIN", "ADMIN" 
    SALES = "SALES", "SALES"
    SUPPORT = "SUPPORT", "SUPPORT"
    NOC = "NOC", "NOC"
    RATE = "RATE", "RATE"
    FINANCE = "FINANCE", "FINANCE"

class User(AbstractUser):
    # Your existing fields
    phone = models.CharField(max_length=25, null=True, blank=True)
    userType = models.CharField(max_length=20, choices=UserType.choices, default="SALES")

   
