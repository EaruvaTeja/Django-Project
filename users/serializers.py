# Import Django's built-in User model (this is your database table)
from django.contrib.auth.models import User

# Import Django's authentication function to check passwords
from django.contrib.auth import authenticate, get_user_model

# Import Django's password validation (runs AUTH_PASSWORD_VALIDATORS)
from django.contrib.auth.password_validation import validate_password

# Import regex for username and name validation
import re

# Import the core DRF components
from rest_framework import serializers

# address import
from .models import Address


# ==================================================
# REGEX PATTERNS (defined once, reused everywhere)
# ==================================================
# Username: must start with a letter, then letters/digits/_/- allowed.
# Examples OK:   john, John_99, jane-doe, user123
# Examples BAD:  123john, _john, john@doe, john.doe
USERNAME_REGEX = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')

# Human name (first/last): must start with a letter, then letters/spaces/'-.
# Examples OK:   John, Mary Jane, O'Brien, Anne-Marie, St. John
# Examples BAD:  123John, @John
NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z\s'\-\.]*$")


# --------------------------------------------------
# 1. SERIALIZER FOR REGISTRATION (UserSerializer)
# --------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    # We explicitly define the password field to add validation rules.
    # 'write_only=True' means this field will be used for input (signup form)
    # but will NEVER be included in the JSON response (for security).
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        # Define which fields from the User model we want to accept in the API
        fields = ('username', 'email', 'password', 'first_name', 'last_name')

    # ------------------------------------------------------------------
    # FIELD VALIDATORS
    # DRF automatically calls validate_<field_name>(value) for each field.
    # Raise serializers.ValidationError to reject with a 400 response.
    # ------------------------------------------------------------------

    def validate_username(self, value):
        """
        Rules:
        - Length between 3 and 30 characters.
        - Must start with a letter (A-Z, a-z).
        - Subsequent characters may be letters, digits, underscore, or hyphen.
        """
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must be at least 3 characters long."
            )
        if len(value) > 30:
            raise serializers.ValidationError(
                "Username must be 30 characters or fewer."
            )
        if not USERNAME_REGEX.match(value):
            raise serializers.ValidationError(
                "Username must start with a letter and can only contain "
                "letters, numbers, underscores, and hyphens."
            )
        return value

    def validate_email(self, value):
        """
        Rules:
        - Django already validates the overall email format.
        - We additionally require the local part (before '@') to start
          with a letter — e.g. reject '123@gmail.com'.
        """
        value = value.strip().lower()

        local_part = value.split('@')[0] if '@' in value else ''

        if not local_part:
            raise serializers.ValidationError("Please enter a valid email.")
        if not local_part[0].isalpha():
            raise serializers.ValidationError(
                "Email must start with a letter (e.g. john@example.com)."
            )
        return value

    def validate_password(self, value):
        """
        Run Django's full password validation suite before the user is created.

        Without this, create_user() only hashes and saves the password —
        it does NOT run the validators listed in settings.AUTH_PASSWORD_VALIDATORS.

        Raises ValidationError with all failed messages at once.
        """
        validate_password(value)
        return value

    def validate_first_name(self, value):
        """
        Rules:
        - Optional (may be blank).
        - If provided: max 50 chars, letters/spaces/hyphens/apostrophes/periods.
        - Must start with a letter.
        """
        value = (value or '').strip()

        if len(value) > 50:
            raise serializers.ValidationError(
                "First name must be 50 characters or fewer."
            )
        if value and not NAME_REGEX.match(value):
            raise serializers.ValidationError(
                "First name must start with a letter and can only contain "
                "letters, spaces, hyphens, apostrophes, and periods."
            )
        return value

    def validate_last_name(self, value):
        """
        Same rules as first_name.
        """
        value = (value or '').strip()

        if len(value) > 50:
            raise serializers.ValidationError(
                "Last name must be 50 characters or fewer."
            )
        if value and not NAME_REGEX.match(value):
            raise serializers.ValidationError(
                "Last name must start with a letter and can only contain "
                "letters, spaces, hyphens, apostrophes, and periods."
            )
        return value

    # ------------------------------------------------------------------
    # OBJECT CREATION
    # ------------------------------------------------------------------

    def create(self, validated_data):
        """
        This function overrides the default 'save()' behavior.
        We use 'create_user' instead of 'create' because it automatically hashes the password.
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user



'''
# --------------------------------------------------
# 2. SERIALIZER FOR LOGIN (LoginSerializer)
# --------------------------------------------------
class LoginSerializer(serializers.Serializer):
    # Define the fields the client MUST send in the JSON request.
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        """
        This is the core validation logic for login.
        It extracts username/password and checks if they are correct.
        """
        username = data.get('username')
        password = data.get('password')

        if username and password:
            # Django's authenticate checks the database for a matching user
            user = authenticate(username=username, password=password)
            if user is None:
                # If authentication fails, raise a validation error
                raise serializers.ValidationError("Invalid username or password.")
            if not user.is_active:
                raise serializers.ValidationError("This user account is inactive.")
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

        # If validation passes, we attach the authenticated user object to the 
        # validated data so that our view can easily access it later.
        data['user'] = user
        return data
'''
# --------------------------------------------------
# 3. SERIALIZER FOR Profile (ProfileSerializer)
# --------------------------------------------------
User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Expose safe fields — now with email editable
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        # Only id and username stay locked
        read_only_fields = ('id', 'username')

    def validate_email(self, value):
        """
        Same rules as registration — email must start with a letter,
        and must be unique across users (excluding the current one).
        """
        value = value.strip().lower()

        # Format check — local part must start with a letter
        local_part = value.split('@')[0] if '@' in value else ''
        if not local_part:
            raise serializers.ValidationError("Please enter a valid email.")
        if not local_part[0].isalpha():
            raise serializers.ValidationError(
                "Email must start with a letter (e.g. john@example.com)."
            )

        # Uniqueness check — exclude the current user's own record
        qs = User.objects.filter(email=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This email is already in use by another account."
            )

        return value

# --------------------------------------------------
# 4. SERIALIZER FOR Address (AddressSerializer)
# --------------------------------------------------
class AddressSerializer(serializers.ModelSerializer):
    """
    Read/write serializer for the Address model.

    Enforces:
      - max 10 addresses per user
      - max 3 home, 3 office, 4 other
    """

    class Meta:
        model = Address
        fields = [
            'id',
            'address_type',
            'label',
            'full_name',
            'phone',
            'line1',
            'line2',
            'landmark',
            'city',
            'state',
            'pincode',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        user = self.context['request'].user
        instance = self.instance

        # Determine the type (from incoming data OR existing instance)
        address_type = attrs.get(
            'address_type',
            getattr(instance, 'address_type', 'home'),
        )

        # Total limit — only applies to creation
        if instance is None:
            total = Address.objects.filter(user=user).count()
            if total >= Address.MAX_ADDRESSES_PER_USER:
                raise serializers.ValidationError(
                    f"You can have at most {Address.MAX_ADDRESSES_PER_USER} addresses."
                )

        # Per-type limit
        type_limits = {
            'home': Address.MAX_HOME,
            'office': Address.MAX_OFFICE,
            'other': Address.MAX_OTHER,
        }
        max_for_type = type_limits[address_type]
        type_qs = Address.objects.filter(user=user, address_type=address_type)
        if instance is not None:
            type_qs = type_qs.exclude(pk=instance.pk)

        if type_qs.count() >= max_for_type:
            raise serializers.ValidationError(
                f"You can have at most {max_for_type} '{address_type}' "
                f"address{'es' if max_for_type != 1 else ''}."
            )

        return attrs
    
            