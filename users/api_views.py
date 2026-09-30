# Import DRF's generic views (pre-built logic for common tasks)
from rest_framework import generics, status
# Import APIView for custom logic (like login)
from rest_framework.views import APIView
# Import Response to send JSON back to the client
from rest_framework.response import Response
# Import Django's User model to query the database
from django.contrib.auth.models import User
# Import the Serializers we just created in the same folder
from .serializers import UserSerializer, ProfileSerializer #LoginSerializer 
# Import the isauthenticated from DRF
from rest_framework.permissions import IsAuthenticated
# Import Refresh token for blacklist tokens while logout
from rest_framework_simplejwt.tokens import RefreshToken
# imports for addresses views
from django.shortcuts import get_object_or_404
from .models import Address
from .serializers import AddressSerializer

# --------------------------------------------------
# 1. REGISTRATION API VIEW
# --------------------------------------------------
# generics.CreateAPIView is a pre-built DRF class that handles POST requests
# to create new database records. We just tell it which Serializer and Model to use.
class RegisterAPIView(generics.CreateAPIView):
    """
    Handles user registration.
    URL: /api/users/register/
    Method: POST
    Request Body (JSON): {"username": "john", "password": "1234", "email": "john@mail.com"}
    Response: Returns the created user data (without password) or validation errors.
    """
    # Tell DRF which database model to use for creating the record
    queryset = User.objects.all()
    # Tell DRF which Serializer to use for validation and creation
    serializer_class = UserSerializer

'''
# --------------------------------------------------
# 2. LOGIN API VIEW
# --------------------------------------------------
# APIView is a base class. We use it when we need full manual control over the logic.

class LoginAPIView(APIView):
    """
    Handles user login.
    URL: /api/users/login/
    Method: POST
    Request Body (JSON): {"username": "john", "password": "1234"}
    Response: Returns user details (without password) or error messages.
    """
    def post(self, request):
        """
        This function runs when a POST request is made to this endpoint.
        'request.data' contains the JSON body sent by the client.
        """
        # Step 1: Pass the incoming JSON data to our LoginSerializer for validation
        serializer = LoginSerializer(data=request.data)

        # Step 2: Check if the data is valid (username exists, password matches)
        if serializer.is_valid():
            # If valid, the serializer's 'validate()' method attached the user object
            # to the validated data. We retrieve it here.
            user = serializer.validated_data['user']
            
            # Step 3: Return a success JSON response.
            # We manually construct the response with the user's details.
            return Response({
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }
            }, status=status.HTTP_200_OK)  # HTTP 200 OK means success
        
        # Step 4: If the serializer validation failed (wrong password, user not found),
        # we return the error messages as JSON with a 400 Bad Request status.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
'''

# --------------------------------------------------
# 3. User Profile API View
# --------------------------------------------------
class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/users/profile/   → return logged-in user's profile
    PATCH /api/users/profile/   → update logged-in user's profile
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Always return the currently authenticated user
        return self.request.user

# --------------------------------------------------
# 2. LOGIN API VIEW
# --------------------------------------------------
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'detail': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'detail': 'Logout successful.'},
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {'detail': 'Invalid or expired refresh token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

# ==================================================================
# ADDRESS API VIEWS
# ==================================================================

class AddressListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/addresses/   -> list this user's saved addresses
    POST /api/addresses/   -> create a new address
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/addresses/<pk>/
    PATCH  /api/addresses/<pk>/
    DELETE /api/addresses/<pk>/

    Ownership is enforced via the queryset — 404 for other users' addresses.
    """
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressSetDefaultAPIView(APIView):
    """
    POST /api/addresses/<pk>/set-default/

    Marks this address as the user's default. The model's save() handles
    unsetting the previous default atomically.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        address = get_object_or_404(
            Address,
            pk=pk,
            user=request.user,
        )
        address.is_default = True
        address.save(update_fields=['is_default'])
        return Response(
            AddressSerializer(address).data,
            status=status.HTTP_200_OK,
        )

    