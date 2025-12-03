from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import ClientProfile

from django.views.generic import TemplateView

class ClientLoginPage(TemplateView):
    template_name = "login.html"


@method_decorator(csrf_exempt, name="dispatch")
class ClientSignupView(APIView):
    """
    POST /api/auth/signup
    {
      "username": "jane",
      "password": "Password123!",
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
    Creates Django User + ClientProfile.
    Logs the client in (session).
    """
    def post(self, request):
        data = request.data
        username = data.get("username")
        password = data.get("password")
        name = data.get("name")
        email = data.get("email")

        if not all([username, password, name, email]):
            return Response({"detail": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            # Optional: enforce unique emails at User level
            return Response({"detail": "Email already used."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password, email=email)
        ClientProfile.objects.create(user=user, name=name, email=email)

        # Log in the new client
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)

        return Response({"detail": "Signup successful."}, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class ClientLoginView(APIView):
    """
    POST /api/auth/login
    { "username": "jane", "password": "Password123!" }
    Logs in the client (session).
    """
    def post(self, request):
        data = request.data
        username = data.get("username")
        password = data.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)

        login(request, user)
        return Response({"detail": "Logged in."}, status=status.HTTP_200_OK)


class ClientLogoutView(APIView):
    """
    POST /api/auth/logout
    Logs out the current user (client or staff).
    """
    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)