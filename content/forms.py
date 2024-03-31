from django import forms
from .models import AnalyzedImage

class AnalyzedImageForm(forms.ModelForm):
    class Meta:
        model = AnalyzedImage
        fields = ['content', 'image']  # 사용자 이름 필드를 포함시키지 않음

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.user_name = user.username  # 현재 로그인한 사용자의 닉네임을 사용자 이름 필드에 저장
        if commit:
            instance.save()
        return instance