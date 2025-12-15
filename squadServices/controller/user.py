from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from squad.utils.jwt_helpers import create_jwt_token
from django.contrib.auth import get_user_model
from squad.utils.authenticators import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from squadServices.models.users import UserLoginHistory
from squadServices.serializer.userSerializer import (
    RegisterSerializer,
    UserLoginHistorySerializer,
    UserSerializer,
    UserWithLoginHistorySerializer,
)
from rest_framework.permissions import AllowAny

from squadServices.utils import get_browser_device, get_client_ip
from django.utils import timezone
from rest_framework.views import APIView

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(generics.GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )
        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        browser, device = get_browser_device(user_agent)
        UserLoginHistory.objects.create(
            user=user,
            ipAddress=ip,
            browser=browser,
            device=device,
            userAgent=user_agent,
        )
        token = create_jwt_token(user)
        return Response({"token": token, "user": UserSerializer(user).data})


class ChangePasswordView(generics.GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        oldPassword = request.data.get("oldPassword")
        newPassword = request.data.get("newPassword")

        if not user.check_password(oldPassword):
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(newPassword)
        user.save()

        return Response(
            {"detail": "Password changed successfully."}, status=status.HTTP_200_OK
        )


class EditUserView(generics.GenericAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def patch(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.user.userType != "ADMIN" and request.user.id != user.id:
            return Response(
                {"detail": "You are not authorized to edit this user."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "User updated successfully.", "user": serializer.data},
            status=status.HTTP_200_OK,
        )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserWithLoginHistorySerializer(request.user)
        return Response(serializer.data)
