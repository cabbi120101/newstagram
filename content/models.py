from django.contrib.auth import get_user_model
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User  # Django의 기본 사용자 모델
from django.core.validators import FileExtensionValidator
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
import numpy as np
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions

# MobileNetV2 모델 로드
model = MobileNetV2(weights='imagenet')

# Create your models here.
class Feed(models.Model):
    content = models.TextField()    # 글내용
    image = models.ImageField(upload_to='images/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])  # 피드 이미지
    email = models.EmailField(default='')     # 글쓴이
    feed_number = models.IntegerField(default=0)  # 게시물 번호
    user_tags = models.TextField(blank=True)  # 사용자가 입력한 태그
    user_post = models.TextField(blank=True)  # 사용자가 입력한 게시글

class Like(models.Model):
    feed_id = models.IntegerField(default=0)
    email = models.EmailField(default='')
    is_like = models.BooleanField(default=True)


class Reply(models.Model):
    feed_id = models.IntegerField(default=0)
    email = models.EmailField(default='')
    reply_content = models.TextField()


class Bookmark(models.Model):
    feed_id = models.IntegerField(default=0)
    email = models.EmailField(default='')
    is_marked = models.BooleanField(default=True)


class AnalyzedImage(models.Model):
    user_name = models.CharField(max_length=150, null=True) # 사용자 이메일
    email = models.EmailField(null=True)  # 사용자 이메일
    content = models.TextField()    # 글내용
    image = models.ImageField(upload_to='images/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    img_tags = models.TextField(blank=True)
    user_tags = models.TextField(blank=True)  # 사용자가 입력한 태그
    feed = models.OneToOneField(Feed, on_delete=models.CASCADE, related_name='analyzed_image', null=True)

    def analyze_and_tag(self):
        try:
            # 이미지 불러오기 및 전처리
            img = Image.open(self.image)
            img = img.convert('RGB')  # 이미지를 RGB 형식으로 변환
            img = img.resize((224, 224))  # MobileNetV2 입력 크기에 맞게 조정
            img_array = np.array(img)
            img_array = preprocess_input(img_array)  # 이미지 전처리

            # 이미지 분류
            predictions = model.predict(np.expand_dims(img_array, axis=0))
            decoded_predictions = decode_predictions(predictions, top=3)[0]  # 상위 3개 예측 결과 반환

            # 분류된 결과를 태그로 변환
            img_tags = [label.replace("_", " ") for _, label, _ in decoded_predictions]
            self.img_tags = ", ".join(img_tags)  # 태그를 문자열로 변환하여 모델에 저장
            self.save()  # 변경 사항 저장
        except Exception as e:
            print(f"Error while analyzing image: {e}")
    
    def save(self, *args, **kwargs):
        # 사용자 정보를 저장하기 전에 호출되는 save 메서드를 오버라이드합니다.
        if self.user_name:  # 사용자 이름이 입력되지 않은 경우에만 사용자 정보를 저장합니다.
            try:
                user = get_user_model().objects.get(username=self.user_name)
                self.user_name = user  # 사용자 객체를 저장합니다.
            except get_user_model().DoesNotExist:
                # 사용자 객체가 없을 경우 처리할 내용을 여기에 추가합니다.
                pass

        if not self.email:  # 이메일이 입력되지 않은 경우에만 사용자의 이메일을 저장합니다.
            self.email = kwargs.pop('email', None)  # 인자로 전달된 이메일을 가져와서 저장합니다.

        super().save(*args, **kwargs)  # 부모 클래스의 save 메서드를 호출하여 기존 동작을 유지합니다.

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class FeedTagMapping(models.Model):
    feed = models.ForeignKey('AnalyzedImage', on_delete=models.CASCADE)
    tag = models.ForeignKey('Tag', on_delete=models.CASCADE)

    def __str__(self):
        return f"Feed: {self.feed.id}, Tag: {self.tag.name}"

