from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import RegisterSerializers, UserUpdateSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import HasAPIKey
from django.core.cache import cache
import random
from .tasks import send_otp_email
from .models import UserProfiles, User
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Auth'])
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializers (data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            UserProfiles.objects.create(user=user)
            otp = random.randint(100000, 999999)
            cache.set(f"otp:{user.email}", otp, 300)
            send_otp_email.delay(user.email, otp)
            return Response({'message': 'User creates sucessfully check your email to verify'}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['Auth'])
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            profile = UserProfiles.objects.get(user = user)
            if not profile.is_email_verified:
                return Response({'error':'email not verified'}, status=status.HTTP_400_BAD_REQUEST)
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

@extend_schema(tags=['Auth'])
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({
        'username': request.user.username ,
        'email': request.user.email,
        })

@extend_schema(tags=['Auth'])
class ForgetPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)
        if not User.objects.filter(email=email).exists():
            return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)
        otp = random.randint(100000, 999999)
        cache.set(f"otp:{email}", otp, 300)
        send_otp_email.delay(email, otp)
        return Response({'message': 'OTP sent. Check email.'}, status=status.HTTP_200_OK)

@extend_schema(tags=['Auth'])
class ResetPassword(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        otp = request.data.get('otp')
        stored_otp = cache.get(f"otp:{email}")
        if not stored_otp:
            return Response({'messsage':"otp expired resend otp"}, status=status.HTTP_400_BAD_REQUEST)
        if str(stored_otp) != str(otp):
            return Response ({"message":"otp not matched"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            cache.delete(f"otp:{email}")
            return Response({"message":"new password created"}, status=status.HTTP_201_CREATED)

@extend_schema(tags=['Auth'])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout sucessfull'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error':"Inavlid toiken"}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=['Auth'])
class ResendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not User.objects.filter(email=email).exists():
            return Response({"error":"email not found"}, status=status.HTTP_400_BAD_REQUEST)
        profile = UserProfiles.objects.get(user__email=email)
        if profile.is_email_verified:
            return Response ({'message':"email already verified"}, status=status.HTTP_400_BAD_REQUEST)
        otp = random.randint(100000, 999999)
        cache.set(f"otp:{email}", otp)
        send_otp_email.delay(email, otp)
        return Response({"message":"otp resent"}, status=status.HTTP_200_OK)


@extend_schema(tags=['Auth'])
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not old_password or not new_password:
            return Response(
                {'error': "bothe old and new are required"}, status=status.HTTP_400_BAD_REQUEST
            )
        user= request.user

        if not user.check_password(old_password):
            return Response(
                {"error": "old passowrd is incorrect"}, status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save()
        return Response(
            {
                "message":"Passowrd changed successfully"
            }, status=status.HTTP_200_OK
        )
    
@extend_schema(tags=['Auth'])
class UpdateProfileView(APIView):
    permission_classes =[IsAuthenticated]
    def patch(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial= True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"profile updated sucessfully"}, status= status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['Auth'])
class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        stored_otp = cache.get(f"otp:{email}")
        if stored_otp is None:
            return Response({"message": "otp expired or not received"}, status=status.HTTP_400_BAD_REQUEST)
        elif str(stored_otp) == str(otp):
            user = User.objects.get(email=email)
            profile = UserProfiles.objects.get(user= user)
            profile.is_email_verified = True
            profile.save()
            cache.delete(f"otp:{email}")
            return Response({"message":"account verified"}, status=status.HTTP_200_OK)
        else:
            return Response({"message":"OTP not matched"}, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['Auth'])
class GoogleLoginView(APIView):
    def post(self, request):
        token = request.data.get('token')
        try:
            google_user = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            email = google_user['email']
            name = google_user['name']
            user, created = User.objects.get_or_create(email=email)
            refresh =  RefreshToken.for_user(user)
            return Response({
                'access' : str(refresh.access_token),
                'refresh': str(refresh),
                'created': created
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error":"invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        
