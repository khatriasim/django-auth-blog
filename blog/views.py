from django.shortcuts import render
from rest_framework.views import APIView
from  rest_framework.response import Response
from  rest_framework import status
from rest_framework.permissions import IsAuthenticated
from  .models import Post, Comment, Like, Category, User, Follow, Notification, LikeComment
from .serializers import PostSerializer, CommentSerializer, CategorySerializer, NotificationSerializer
from .pagination import PostPagination
from django.db.models import Q
from .throttles import ListPostsAnnonThrottle, CreatePostUserThrottle
from django.db.models import F
from django.core.cache import cache
from .utils import invalidate_post_cache
from .permissions import IsAdminUser
from django.db import transaction
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['Blog'])
class CreatePostView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CreatePostUserThrottle]
    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    post = serializer.save(author=request.user)

                    invalidate_post_cache()
                    followers = Follow.objects.filter(following=request.user)
                    for follow in followers:
                        Notification.objects.create(user = follow.follower,
                                                    sender=request.user,
                                                    notification_type = 'new_post',
                                                    post=post)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error':'seomthing went wrong'}, status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['Blog'])
class ListPostsView(APIView):
    throttle_classes = [ListPostsAnnonThrottle]
    def get(self, request):
        search = request.query_params.get('search', None)
        author = request.query_params.get('author', None)
        cache_key = f"posts:{search}:{author}" 
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)
        posts= Post.objects.filter(status='published').order_by('-created_at')

        if search:
            posts=posts.filter(title__icontains=search)
                
            # Q( | Q(content__icontains=search))
        if author:
            posts=posts.filter(author__username__icontains=author)

        paginator = PostPagination()
        paginated_posts = paginator.paginate_queryset(posts, request)
        serializer = PostSerializer(paginated_posts, many=True)
        data = paginator.get_paginated_response(serializer.data).data
        cache.set(cache_key, data, 300)
        return Response(data)
    
@extend_schema(tags=['Blog'])
class AuthorPostsView(APIView):
    def get(self, request, username):
        posts = Post.objects.filter(author__username=username, status='published').order_by('-created_at')
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Blog'])
class MyPostView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        posts = Post.objects.filter(author = request.user)
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

@extend_schema(tags=['Blog'])
class EditPostVIew(APIView):
    permission_classes= [IsAuthenticated]
    def patch(self, request, pk):
        post = Post.objects.get(id=pk)
        if post.author != request.user:
            return Response({'message': "author not matched"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            invalidate_post_cache()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['Blog'])
class DeletePostView(APIView):
    permission_classes= [IsAuthenticated]
    def delete(self, request, pk):
        post = Post.objects.get(id = pk)
        if post.author != request.user:
            return Response({'message': "you can only delete your post"}, status=status.HTTP_403_FORBIDDEN)
        else: 
            post.delete()
            invalidate_post_cache()
            return Response({"message": "post delted successfully"}, status=status.HTTP_204_NO_CONTENT)



@extend_schema(tags=['Blog'])
class AddCommentView(APIView):
    permission_classes= [IsAuthenticated]
    def post(self, request, pk):
        post = Post.objects.get(id=pk)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(post=post, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['Blog'])
class ListCommentView(APIView):
    def get(self, request, pk):
        post = Post.objects.get(id=pk)
        comments = Comment.objects.filter(post=post)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

@extend_schema(tags=['Blog'])
class DeleteCommentView(APIView):
    permission_classes= [IsAuthenticated]
    def delete(self, request, pk):
        comment = Comment.objects.get(id=pk)
        if comment.author != request.user:
            return Response({'message': 'You can only delete your own comments'}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({'message':'comment deleted sucessfuly'}, status=status.HTTP_200_OK)
        

@extend_schema(tags=['Blog'])
class TogglePostLikeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        with transaction.atomic():
            post = Post.objects.select_for_update().get(id=pk)
            like, created = Like.objects.get_or_create(
                post=post,
                user=request.user
            )
            if created:
            # Notification.objects.create(
            #     user=post.author,
            #     sender=request.user,
            #     notification_type ='like',
            #     post=post
            # )
                return Response({'message':"post liked"}, status=status.HTTP_201_CREATED)
            else:
                like.delete()
                return Response({'message':"like removed"}, status=status.HTTP_200_OK)



@extend_schema(tags=['Blog'])
class ToggleCommentLikeView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        comment = Comment.objects.get(id=pk)
        like, created = LikeComment.objects.get_or_create(
            comment=comment,
            user=request.user
        )
        if created:
            # Notification.objects.create(
            #     user=post.author,
            #     sender=request.user,
            #     notification_type ='like',
            #     post=post
            # )
            return Response({'message':" comment liked"}, status=status.HTTP_201_CREATED)
        else:
            like.delete()
            return Response({'message':"like remove from comment "}, status=status.HTTP_200_OK)


@extend_schema(tags=['Blog'])
class CreateCategoryView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
@extend_schema(tags=['Blog'])
class ListCategoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
@extend_schema(tags=['Blog'])
class PostByCategoryView(APIView):
    def get(self, request, pk):
        try:
            category = Category.objects.get(id=pk)
        except Category.DoesNotExist:
            return Response(
                {'message': 'category not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        posts = Post.objects.filter(Categories=category, status='published')
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
@extend_schema(tags=['Blog'])
class FollowView(APIView):
    permission_classes =[IsAuthenticated]

    def post(self, request, username):
        target_username = User.objects.get(username=username)
        if target_username == request.user:
            return Response({'message':'you cant follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        follow, created = Follow.objects.get_or_create(
            following=target_username,
            follower=request.user
        )
        # print(f"created: {created}") 
        if created:
            # print("follow notification created") 
            return Response({"message":f"following {username}"}, status=status.HTTP_200_OK)
        follow.delete()
        return Response({"message":f"unfollowed {username}"}, status=status.HTTP_200_OK)
    

@extend_schema(tags=['Blog'])
class FollowersListView(APIView):
    def get(self, request, username):
        user = User.objects.get(username=username)
        followers = Follow.objects.filter(following=user)
        data = [f.follower.username for f in followers]
        return Response({"message": data, 'count':len(data)})
    

@extend_schema(tags=['Blog'])
class FollowingListView(APIView):
    def get(self, request, username):
        user = User.objects.get(username=username)
        following = Follow.objects.filter(follower=user)
        data = [f.following.username for f in following]
        return Response ({"message": data, "count":len(data)})
    

@extend_schema(tags=['Blog'])
class FeedView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        following = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
        posts = Post.objects.filter(author__in=following, status='published').order_by('-created_at')
        serialzer = PostSerializer(posts , many=True)
        return Response(serialzer.data, status=status.HTTP_200_OK)
    

@extend_schema(tags=['Blog'])
class ListNotification(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        notification = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notification, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['Blog'])
class MarkAsReadView(APIView):
    permission_classes= [IsAuthenticated]
    def patch(self, request, pk):
        notification = Notification.objects.get(id=pk)
        if notification.user != request.user:
            return Response({"error":"not your notification"}, status=status.HTTP_400_BAD_REQUEST)
        notification.is_read = True
        notification.save()
        return Response({"message":"marked as read"}, status=status.HTTP_200_OK)
        
@extend_schema(tags=['Blog'])
class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response ({"message":"all marked as read"}, status=status.HTTP_200_OK)
    
@extend_schema(tags=['Blog'])
class PostDetailView(APIView):
    def get(self, request, pk):
        post = Post.objects.get(id= pk)
        # cache_key =f"views:{request.user.id}:{pk}"
        # if not cache.get(cache_key):
        #     # Post.objects.filter(id=pk).update(views=F('views') + 1)
        #     cache.set(cache_key, True, 3600)
        serializer = PostSerializer(post, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)
