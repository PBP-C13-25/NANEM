from django.contrib import admin

from .models import Plant

# Temporary registration for manual data entry (including climate fields),
# not part of the required custom CRUD module.
admin.site.register(Plant)
