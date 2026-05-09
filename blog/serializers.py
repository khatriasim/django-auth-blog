from rest_framework import serializers
from .models import Post, Comment, Category, Notification
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


class PostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    categories = CategorySerializer(many=True, read_only=True)

    def get_author(self, obj):
        return obj.author.username

    class Meta:
        model = Post
        fields = ['id', 'title', 'content', 'author', 'status','views', 'created_at', 'categories', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']



class CommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    def get_author(self, obj):
        return obj.author.username
    class Meta:
        model = Comment
        fields = ['author', 'content', 'post', 'created_at']
        read_only_fields = ['created_at', 'author', 'id', 'post']

class NotificationSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()

    def get_sender(self, obj):
        return obj.sender.username
    
    class Meta:
        model = Notification
        fields = ['id', 'post', 'user', 'sender', 'created_at', 'notification_type', 'is_read']