from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class NavItem(models.Model):
    label = models.CharField(max_length=50)
    url = models.CharField(max_length=200)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, default="Home")  # 👈 New field

    def __str__(self):
        return self.label


class NavUserRelation(models.Model):
    userType = models.CharField(max_length=50)
    navigateId=models.ForeignKey(NavItem , on_delete=models.DO_NOTHING)
    read=models.BooleanField(default=False)
    write=models.BooleanField(default=False)
    delete=models.BooleanField(default=False)
    put=models.BooleanField(default=False)

    def __str__(self):
        return self.userType

   
