from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import AIProviderSettings

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'confirm_password', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        email = value.strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined')
        read_only_fields = ('id', 'is_active', 'date_joined')

    def validate_email(self, value):
        email = value.strip()
        queryset = User.objects.filter(email__iexact=email)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if email and queryset.exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return email


class AIProviderSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIProviderSettings
        fields = ('mode', 'primary_provider', 'secondary_provider', 'automatic_fallback')

    def validate(self, attrs):
        primary = attrs.get('primary_provider', getattr(self.instance, 'primary_provider', 'gemini'))
        secondary = attrs.get('secondary_provider', getattr(self.instance, 'secondary_provider', 'openai'))
        if primary == secondary:
            raise serializers.ValidationError({'secondary_provider': 'Choose a different secondary provider.'})
        return attrs
