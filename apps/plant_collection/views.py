from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import DeleteView, ListView, DetailView, CreateView, UpdateView, View
from apps.core.mixins import RegularUserRequiredMixin, OwnedQuerysetMixin 

from .models import PlantCollection
from .form import PlantCollectionForm

class CollectionListView(RegularUserRequiredMixin, ListView):
    model = PlantCollection
    template_name = "plant_collection/index.html"
    context_object_name = "posts"

class CollectionDetailView(RegularUserRequiredMixin, DetailView):
    model = PlantCollection
    template_name = "plant_collection/plant_detail.html"
    context_object_name = "post"

class CollectionCreateView(RegularUserRequiredMixin, CreateView):
    model = PlantCollection
    form_class = PlantCollectionForm
    template_name = "plant_collection/plant_form.html"
    success_url = reverse_lazy('collection:index')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class CollectionUpdateView(RegularUserRequiredMixin, OwnedQuerysetMixin, UpdateView):
    model = PlantCollection
    form_class = PlantCollectionForm
    template_name = "plant_collection/plant_form.html"
    owner_field = "owner" 
    
    def get_success_url(self):
        return reverse_lazy('collection:detail', kwargs={'pk': self.object.pk})
    
class CollectionDeleteView(RegularUserRequiredMixin, OwnedQuerysetMixin, DeleteView):
    model = PlantCollection
    template_name = "plant_collection/plant_confirm_delete.html"
    success_url = reverse_lazy('collection:index')
    owner_field = "owner"

class ToggleLikeView(RegularUserRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(PlantCollection, pk=pk)
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True
        return JsonResponse({'liked': liked, 'total_likes': post.total_likes})