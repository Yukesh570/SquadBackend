import jwt

from datetime import timedelta
from django.utils import timezone
from django.conf import settings


def create_jwt_token(user):
    payload = {
        "userId": user.id,
        "username": user.username,
        "userType": user.userType,
        "exp": timezone.now() + timedelta(hours=200),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return token
