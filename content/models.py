from django.db import models


# Create your models here.
class Feed(models.Model):
    content = models.TextField()    # 글내용
    image = models.TextField()  # 피드 이미지
    email = models.EmailField(default='')     # 글쓴이


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


from django.db import models
from django.core.validators import FileExtensionValidator
from PIL import Image
import numpy as np
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input, decode_predictions

# MobileNetV2 모델 로드
model = MobileNetV2(weights='imagenet')

class AnalyzedImage(models.Model):
    image = models.ImageField(upload_to='images/', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    tags = models.TextField(blank=True)

    def analyze_and_tag(self):
        # 이미지 불러오기 및 전처리
        img = Image.open(self.image)
        img = img.resize((224, 224))  # MobileNetV2 입력 크기에 맞게 조정
        img_array = np.array(img)
        img_array = preprocess_input(img_array)
        img_array = np.expand_dims(img_array, axis=0)

        # 이미지 분류
        predictions = model.predict(img_array)
        decoded_predictions = decode_predictions(predictions, top=3)[0]  # 상위 3개 예측 결과 반환

        # 분류된 결과를 태그로 변환
        tags = [label.replace("_", " ") for _, label, _ in decoded_predictions]
        self.tags = ", ".join(tags)  # 태그를 문자열로 변환하여 모델에 저장
        self.save()  # 변경 사항 저장

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.tags:  # 이미지가 저장되면서 태그가 생성되지 않았을 경우에만 분석 및 태깅 수행
            self.analyze_and_tag()
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class FeedTagMapping(models.Model):
    feed = models.ForeignKey('AnalyzedImage', on_delete=models.CASCADE)
    tag = models.ForeignKey('Tag', on_delete=models.CASCADE)

    def __str__(self):
        return f"Feed: {self.feed.id}, Tag: {self.tag.name}"