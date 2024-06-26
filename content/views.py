from uuid import uuid4
from django.shortcuts import render, redirect
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Feed, Reply, Like, Bookmark
from user.models import User
import os
from newstagram.settings import MEDIA_ROOT

# 태그 붙이기 기능을 위해 추가
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AnalyzedImage, Tag, FeedTagMapping
from django.conf import settings  # settings 추가

class Main(APIView):
    def get(self, request):
        email = request.session.get('email', None)

        if email is None:
            return render(request, "user/login.html")

        user = User.objects.filter(email=email).first()

        if user is None:
            return render(request, "user/login.html")

        feed_object_list = Feed.objects.all().order_by('-id')
        feed_list = []

        for feed in feed_object_list:
            user = User.objects.filter(email=feed.email).first()
            if user:
                reply_object_list = Reply.objects.filter(feed_id=feed.id)
                reply_list = []
                for reply in reply_object_list:
                    reply_user = User.objects.filter(email=reply.email).first()
                    if reply_user:
                        reply_list.append(dict(reply_content=reply.reply_content, nickname=reply_user.nickname))
                like_count = Like.objects.filter(feed_id=feed.id, is_like=True).count()
                is_liked = Like.objects.filter(feed_id=feed.id, email=email, is_like=True).exists()
                is_marked = Bookmark.objects.filter(feed_id=feed.id, email=email, is_marked=True).exists()
                profile_image = user.profile_image.url if user.profile_image else settings.MEDIA_URL + 'default_profile.png'
                feed_list.append(dict(id=feed.id,
                                    image=feed.image,
                                    content=feed.content,
                                    like_count=like_count,
                                    profile_image=profile_image,
                                    nickname=user.nickname,
                                    reply_list=reply_list,
                                    is_liked=is_liked,
                                    is_marked=is_marked
                                    ))

        return render(request, "newstagram/main.html", context=dict(feeds=feed_list, user=user))


## 이미지 분석 함수
from django.http import JsonResponse

def analyze_image_tags(request):
    if request.method == 'POST':
        # POST 요청에서 이미지 데이터를 받아옵니다.
        image_src = request.POST.get('imageSrc')

        # 이미지 분석 및 태그 작업을 수행하는 코드를 여기에 추가합니다.
        # 예시로, AnalyzedImage 모델에서 해당 이미지를 분석하고 태그를 가져오는 코드를 사용합니다.
        analyzed_tags = analyze_image(image_src)

        # 분석된 태그를 JSON 형식으로 응답합니다.
        return JsonResponse({'tags': analyzed_tags})

    # POST 요청이 아닌 경우, 잘못된 요청으로 간주하고 에러 응답을 반환합니다.
    return JsonResponse({'error': 'Invalid request'}, status=400)

## 자동 태깅 모델 tensorflow 사용
import tensorflow as tf
import numpy as np
from PIL import Image
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.applications.resnet50 import decode_predictions

def extract_tags_from_image(image_path):
    try:
        # 이미지 불러오기 및 전처리
        img = Image.open(image_path)
        img = img.resize((224, 224))  # ResNet 모델의 입력 크기에 맞게 조정
        img_array = np.array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)

        # ResNet50 모델 불러오기
        model = tf.keras.applications.ResNet50(weights='imagenet')

        # 이미지에서 태그 추출
        predictions = model.predict(img_array)
        decoded_predictions = decode_predictions(predictions, top=3)[0]  # 상위 3개의 예측을 가져옴

        # 추출된 태그 반환
        tags = [tag[1] for tag in decoded_predictions]  # 예측 결과에서 태그만 추출
        return tags
    except Exception as e:
        print(f"Error while extracting tags from image: {e}")
        return []


def analyze_image(image_src):
    # 이미지 분석 및 태그 작업을 수행하는 코드를 여기에 추가합니다.
    # 예시로, 이미지를 분석하고 태그를 추출하는 함수를 사용합니다.
    analyzed_tags = extract_tags_from_image(image_src)
    return analyzed_tags

## 이미지 태그를 저장하는 코드
class UploadFeed(APIView):
    def post(self, request):
        # 파일 불러오기
        file = request.FILES['file']
        
        # 게시물 번호 추출
        feed_number = request.data.get('feed_number', None)
        
        # 게시물 내용 추출
        content = request.data.get('content', '')

        # 현재 로그인한 사용자 가져오기
        user = request.user

        if user.is_authenticated:  # 사용자가 인증되어 있는 경우
            email = user.email
            user_name = user.nickname  # 사용자의 닉네임 가져오기
            user_post = request.data.get('user_post', '')  # 두 번째 모달에서 입력한 게시글 정보
            user_tags = request.data.get('user_tags', '')  # 두 번째 모달에서 입력한 태그 정보
        else:  # 사용자가 인증되어 있지 않은 경우, 빈 문자열로 처리
            email = ''
            user_name = ''
            user_post = ''
            user_tags = ''
        
        # 파일 이름에서 확장자 추출
        _, file_extension = os.path.splitext(file.name)

        # 이미지 저장 경로 설정
        uuid_name = uuid4().hex
        save_path = os.path.join(MEDIA_ROOT, f"{uuid_name}{file_extension}")

        # 이미지 저장
        with open(save_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 이미지 분석 및 태깅
        analyzed_image = AnalyzedImage.objects.create(image=save_path)
        analyzed_image.analyze_and_tag()

        # 분석된 이미지의 태그를 DB에 저장
        tags = analyzed_image.tags.split(', ')
        for tag_name in tags:
            tag, _ = Tag.objects.get_or_create(name=tag_name.strip())  # 태그가 이미 존재하면 가져오고, 없으면 생성
            FeedTagMapping.objects.create(feed=analyzed_image, tag=tag)  # 피드와 태그 간의 매핑 저장

        # 사용자가 입력한 태그 정보 저장
        if user_tags:
            user_tags = user_tags.split(',')
            for tag_name in user_tags:
                tag, _ = Tag.objects.get_or_create(name=tag_name.strip())
                FeedTagMapping.objects.create(feed=analyzed_image, tag=tag)

        # 게시물 번호와 사용자 정보 저장
        if feed_number:
            analyzed_image.feed_number = feed_number
        analyzed_image.save()

        # Feed 모델에 저장
        Feed.objects.create(content=content, image=save_path, email=email, user_name=user_name, user_post=user_post, user_tags=user_tags)

        return Response({'tags': analyzed_image.tags}, status=200)

        
class Profile(APIView):
    def get(self, request):
        email = request.session.get('email', None)

        if email is None:
            return render(request, "user/login.html")

        user = User.objects.filter(email=email).first()

        if user is None:
            return render(request, "user/login.html")

        feed_list = Feed.objects.filter(email=email)
        like_list = list(Like.objects.filter(email=email, is_like=True).values_list('feed_id', flat=True))
        like_feed_list = Feed.objects.filter(id__in=like_list)
        bookmark_list = list(Bookmark.objects.filter(email=email, is_marked=True).values_list('feed_id', flat=True))
        bookmark_feed_list = Feed.objects.filter(id__in=bookmark_list)

        # 사용자 정보와 관련된 필드 채우기
        for feed in feed_list:
            feed.user_post = feed.user_post or ''  # 기본값 설정
            feed.user_tags = feed.user_tags or ''  # 기본값 설정

        return render(request, 'content/profile.html', context=dict(feed_list=feed_list,
                                                                    like_feed_list=like_feed_list,
                                                                    bookmark_feed_list=bookmark_feed_list,
                                                                    user=user))


class UploadReply(APIView):
    def post(self, request):
        feed_id = request.data.get('feed_id', None)
        reply_content = request.data.get('reply_content', None)
        email = request.session.get('email', None)

        Reply.objects.create(feed_id=feed_id, reply_content=reply_content, email=email)

        return Response(status=200)


class ToggleLike(APIView):
    def post(self, request):
        feed_id = request.data.get('feed_id', None)
        favorite_text = request.data.get('favorite_text', True)

        if favorite_text == 'favorite_border':
            is_like = True
        else:
            is_like = False
        email = request.session.get('email', None)

        like = Like.objects.filter(feed_id=feed_id, email=email).first()

        if like:
            like.is_like = is_like
            like.save()
        else:
            Like.objects.create(feed_id=feed_id, is_like=is_like, email=email)

        return Response(status=200)


class ToggleBookmark(APIView):
    def post(self, request):
        feed_id = request.data.get('feed_id', None)
        bookmark_text = request.data.get('bookmark_text', True)
        print(bookmark_text)
        if bookmark_text == 'bookmark_border':
            is_marked = True
        else:
            is_marked = False
        email = request.session.get('email', None)

        bookmark = Bookmark.objects.filter(feed_id=feed_id, email=email).first()

        if bookmark:
            bookmark.is_marked = is_marked
            bookmark.save()
        else:
            Bookmark.objects.create(feed_id=feed_id, is_marked=is_marked, email=email)

        return Response(status=200)
