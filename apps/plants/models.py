from django.db import models

class Plant(models.Model):
    CATEGORY_CHOICES = [
        ("sayur", "Sayur"),
        ("buah", "Buah"),
        ("herbal", "Herbal"),
        ("hias", "Hias"),
    ]
    SUNLIGHT_CHOICES = [
        ("full_sun", "Full sun"),
        ("partial_shade", "Partial shade"),
        ("shade", "Shade"),
    ]
    SPACE_NEEDED_CHOICES = [
        ("small", "Small"),
        ("medium", "Medium"),
        ("large", "Large"),
    ]

    perenual_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=200)
    scientific_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Temperature in Celsius, humidity in percent, rainfall in mm/day.
    temp_min = models.FloatField(null=True, blank=True)
    temp_max = models.FloatField(null=True, blank=True)
    humidity_min = models.FloatField(null=True, blank=True)
    humidity_max = models.FloatField(null=True, blank=True)
    rainfall_min = models.FloatField(null=True, blank=True)
    rainfall_max = models.FloatField(null=True, blank=True)

    supports_soil = models.BooleanField(default=True)
    supports_hydroponic = models.BooleanField(default=False)
    sunlight = models.CharField(max_length=20, choices=SUNLIGHT_CHOICES)
    space_needed = models.CharField(max_length=10, choices=SPACE_NEEDED_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
