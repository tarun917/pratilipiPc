from django import forms


class EpisodeZipUploadForm(forms.Form):
    zip_file = forms.FileField(
        required=True,
        help_text="Upload a ZIP containing JPG/JPEG slices at the root."
    )