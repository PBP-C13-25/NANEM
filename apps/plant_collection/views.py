from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import DeleteView, ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import OwnedQuerysetMixin
from .models import PlantCollection
from .forms import PlantCollectionForm

class CollectionListView(LoginRequiredMixin, ListView):
    model = PlantCollection
    template_name = "plant_collection/index.html"
    context_object_name = "posts"
    def get_queryset(self):
        # Langsung gabungkan query optimasi
        return (
            PlantCollection.objects
            .select_related("owner")
            .prefetch_related("likes")
            .order_by("-created_at")
        )

class CollectionDetailView(LoginRequiredMixin,  DetailView):
    model = PlantCollection
    template_name = "plant_collection/plant_detail.html"
    context_object_name = "post"

class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = PlantCollection
    form_class = PlantCollectionForm
    template_name = "plant_collection/plant_form.html"
    success_url = reverse_lazy('collection:index')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Postingan berhasil dibuat!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.warning(self.request, "Gagal menyimpan! Harap lengkapi field yang masih kosong dan lampirkan foto.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        return context

class CollectionUpdateView(LoginRequiredMixin, OwnedQuerysetMixin, UpdateView):
    model = PlantCollection
    form_class = PlantCollectionForm
    template_name = "plant_collection/plant_form.html"
    owner_field = "owner" 
    
    def form_valid(self, form):
        messages.success(self.request, "Postingan berhasil diperbarui.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('collection:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context
    
class CollectionDeleteView(LoginRequiredMixin, OwnedQuerysetMixin, DeleteView):
    model = PlantCollection
    template_name = "plant_collection/plant_confirm_delete.html"
    success_url = reverse_lazy('collection:index')
    owner_field = "owner"

    def form_valid(self, form):
        messages.success(self.request, f"Postingan {self.object.title} berhasil dihapus.")
        return super().form_valid(form)

class ToggleLikeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(PlantCollection, pk=pk)
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            is_liked = False
        else:
            post.likes.add(request.user)
            is_liked = True
        return JsonResponse({'is_liked': is_liked, 'like_count': post.likes.count()})