from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from squad.utils.jwt_helpers import create_jwt_token
from django.contrib.auth import get_user_model

from squadServices.serializer.userSerializer import RegisterSerializer, UserSerializer
from rest_framework.permissions import AllowAny

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(generics.GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token = create_jwt_token(user)
        return Response({
            "token": token,
            "user": UserSerializer(user).data
        })
