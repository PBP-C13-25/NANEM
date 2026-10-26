from django.db import models
from django.contrib.auth.models import User

class PlantCollection(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    title = models.CharField(max_length=100)
    description = models.TextField()
    photo = models.ImageField(upload_to='plant_collections/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_collections', blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.likes.count()