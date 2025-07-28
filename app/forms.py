from django import forms

class DemandUploadForm(forms.Form):
    stock_lengths = forms.CharField()
    file = forms.FileField()