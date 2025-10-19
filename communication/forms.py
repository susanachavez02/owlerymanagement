from django import forms
from .models import Message

class NewMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        # We only want the user to type these fields
        fields = ['subject', 'body']