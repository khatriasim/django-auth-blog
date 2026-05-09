from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_otp_email(email, otp):
    send_mail(
        subject='verify yout email',
        message= f'yout OTP is : {otp} \n This otp expires in 5 minutes.',
        from_email='khatriasim111@gmail.com',
        recipient_list=[email],
    )