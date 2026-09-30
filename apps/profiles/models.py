from django.conf import settings
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    name = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(upload_to="profile_pics/", blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"