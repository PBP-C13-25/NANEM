from django.shortcuts import render

# Create your views here.
def collection_page(request):
    return render(request, "plant_collection/index.html")