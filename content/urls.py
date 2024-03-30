from django.urls import path
from .views import UploadFeed, Profile, Main, UploadReply, ToggleLike, ToggleBookmark, analyze_image_tags

urlpatterns = [
    path('upload', UploadFeed.as_view()),
    path('reply', UploadReply.as_view()),
    path('like', ToggleLike.as_view()),
    path('bookmark', ToggleBookmark.as_view()),
    path('profile', Profile.as_view()),
    path('main', Main.as_view()),
    path('analyze_image_tags/', analyze_image_tags, name='analyze_image_tags'),

]

