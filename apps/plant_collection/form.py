from django import forms
from .models import PlantCollection, Comment


class PlantCollectionCreateForm(forms.ModelForm):
    class Meta:
        model = PlantCollection
        fields = ['title', 'description', 'photo']

class PlantCollectionUpdateForm(forms.ModelForm):
    class Meta:
        model = PlantCollection
        fields = ['title', 'description'] 

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Tulis komentar...'})}