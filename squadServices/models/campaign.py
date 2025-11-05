from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class objectiveType(models.TextChoices):
    Promotion= "Promotion"
    Announcement = "Announcement"
    Re_engagement = "Re_engagement"
 
class Template(models.Model):
    name = models.CharField(max_length=100)
    content = models.TextField()

    def __str__(self):
        return self.name
class Campaign(models.Model):
    name = models.CharField(max_length=100)
    objective = models.CharField(max_length=20, choices=objectiveType.choices)
    content=models.TextField(null=True, blank=True)
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, blank=True)

    schedule=models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.name
    
class CampaignContact(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='contacts')
    contactNumber = models.CharField(max_length=20)
    def __str__(self):
        return self.contactNumber



 

   
