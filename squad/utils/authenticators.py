from typing import Optional, Tuple

import jwt
from django.conf import settings
from django.core.cache import cache
from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from squadServices.models.users import User




class JWTAuthentication(BaseAuthentication):
    """
    JWT based authentication class
    """

    def authenticate(self, request: Request) -> Optional[Tuple[str, str]]:
        token: str = request.META.get("HTTP_AUTHORIZATION", "")
        if not token:
            return None
        try:
            split_token = token.split(" ")
        except AttributeError:
            raise exceptions.AuthenticationFailed("Invalid Token")
        match split_token:
            case ["Bearer", token]:
                try:
                    payload = jwt.decode(
                        token, settings.SECRET_KEY, algorithms=["HS256"]
                    )

                except InvalidSignatureError:
                    raise exceptions.AuthenticationFailed("Token verification failed")
                except DecodeError:
                    raise exceptions.AuthenticationFailed("Token decode failed")
                except ExpiredSignatureError:
                    raise exceptions.AuthenticationFailed("Token expired")
            case _:
                # if "token" doesn't have Bearer,
                # it is probably API-KEY and authenticated by API-KEY authenticator
                return None
        userId = payload.get("userId")
        if not userId:
            raise exceptions.AuthenticationFailed("Invalid token payload")

        try:
            user_instance = User.objects.get(id=userId)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found or deleted")

        return user_instance, token
