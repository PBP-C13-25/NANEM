from urllib import request

from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden

from .models import PlantCollection, Comment
from .form import PlantCollectionCreateForm, PlantCollectionUpdateForm, CommentForm

# READ: feed semua user dan quest
def collection_page(request):
    collection = PlantCollection.objects.all().order_by('-created_at')
    return render(request, 'plant_collection/index.html', {'collection': collection})

# CREATE : tambah koleksi tanaman
@login_required
def plant_create(request):
    if request.method == 'POST':
        form = PlantCollectionCreateForm(request.POST, request.FILES)
        if form.is_valid():
            plant = form.save(commit=False)
            plant.owner = request.user
            plant.save()
        return redirect('plant_detail', pk=plant.pk)
    return render(request, 'plants_collection/plant_form.html', {'form': form, 'title': 'Tambah Tanaman'})

# UPDATE: edit koleksi tanaman hanya judul dan deskripsi 
@login_required
def plant_update(request, pk):
    plant = get_object_or_404(PlantCollection, pk=pk, owner=request.user)
    form = PlantCollectionUpdateForm(request.POST or None, instance=plant)
    if form.is_valid():
        form.save()
        return redirect('plant_detail', pk=plant.pk)
    return render(request, 'plants_collection/plant_form.html',
                  {'form': form, 'title': 'Edit Tanaman', 'plant': plant})

# DELETE: hapus koleksi tanaman
@login_required
def plant_delete(request, pk):
    plant = get_object_or_404(PlantCollection, pk=pk, owner=request.user)
    if request.method == 'POST':
        plant.photo.delete(save=False)      
        plant.delete()
        return redirect('collection_page')
    return render(request, 'plants_collection/plant_confirm_delete.html', {'plant': plant})

# READ: detail + komentar
def plant_detail(request, pk):
    plant = get_object_or_404(PlantCollection, pk=pk)
    liked = request.user.is_authenticated and plant.likes.filter(user=request.user).exists()
    return render(request, 'plants_collection/plant_detail.html', {
        'plant': plant,
        'comments': plant.comments.select_related('user'),
        'comment_form': CommentForm(),
        'liked': liked,
    })

#COMMENT: tambah komentar pada koleksi tanaman
@login_required
@require_POST
def add_comment(request, pk):
    plant = get_object_or_404(PlantCollection, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.user = request.user
        comment.plant = plant
        comment.save()
    return redirect('plant_detail', pk=pk)

#DELETE: hapus komentar pada koleksi tanaman
@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    # boleh dihapus oleh penulis komentar atau pemilik tanaman
    if request.user in (comment.user, comment.plant.owner):
        plant_pk = comment.plant.pk
        comment.delete()
        return redirect('plant_detail', pk=plant_pk)
    return HttpResponseForbidden("Anda tidak diperbolehkan untuk menghapus komentar ini.")

# LIKE: toggle like/unlike koleksi tanaman
@login_required
@require_POST
def toggle_like(request, pk):
    plant = get_object_or_404(PlantCollection, pk=pk)
    if request.method == 'POST':
        if request.user in plant.likes.all():
            plant.likes.remove(request.user)
        else:
            plant.likes.add(request.user)
    return redirect('plant_detail', pk=pk) 


# READ: koleksi milik satu user (profil)
# def user_plants(request, username):
#     plants = PlantCollection.objects.filter(owner__username=username)
#     return render(request, 'plants_collection/user_plants.html',
#                   {'plant': plants, 'username': username})
