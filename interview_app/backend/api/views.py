from django.shortcuts import render
from .models import User
import pyotp
from django.conf import settings
from .serializers import MyTOPS, RegistrationSerializer
from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.shortcuts import redirect
import random
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken


def generate_otp():
    otp =""
    for i in range (6):
        otp += str(random.randint(0,9))
    return otp

def send_otp_email(user_email, otp):
    subject = 'Your OTP for Login'
    message = f'Your OTP is: {otp}'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user_email]
    send_mail(subject, message, from_email, recipient_list)

def update_otp_time(email, otp):
    User = get_user_model()
    try:
        user = User.objects.get(email=email)
        user.otp = otp
        user.otp_time = timezone.now() + timedelta(minutes=10)
        user.save()
        return True, 
    except User.DoesNotExist:
        return False,
    
class MyTokenObtainPairView(TokenObtainPairView):

    serializer_class = MyTOPS

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        access = response.data.get('access') 
        refresh = response.data.get('refresh') 

        email = request.data.get('email')

        if access and refresh:
            otp = generate_otp()
            print("Generated OTP:", otp)
            send_otp_email(email, otp)
            update_otp_time(email, otp)
            return Response({'otp created'}, status=status.HTTP_200_OK)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protectedView(request):
    output = f"Welcome {request.user.username}"
    return Response({'response':output}, status=status.HTTP_200_OK)

@api_view(['GET'])
def view_all_routes(request):
    data = [
        'api/token/refresh/',
        'api/register/',
        'api/verifyLogin',
        'api/token/'
    ]

    return Response(data)



@csrf_exempt
@api_view(['GET', 'POST'])
def verify_login_otp(request):
    email = request.data.get('email')
    User = get_user_model()
    stored_otp = None
    otp_time = None
    user = User.objects.get(email=email)
    refresh = RefreshToken.for_user(user)
    refresh['email'] = str(user.email)
    refresh['name'] = user.first_name +' '+ user.last_name
    refresh['username'] = user.username

    token= {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
    stored_otp = user.otp
    otp_time = user.otp_time

    submitted_otp = request.data.get('otp')
    current_time = timezone.now()
    # print(otp_time, current_time, stored_otp, submitted_otp)
    if submitted_otp == stored_otp:
        if otp_time >= current_time:
            return Response(token, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'otp has expired'}, status=status.HTTP_500_EXPIRED_OTP)
    else:
        return Response({'message': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)



