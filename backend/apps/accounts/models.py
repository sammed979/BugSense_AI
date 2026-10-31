from django.conf import settings
from django.db import models


class AIProviderSettings(models.Model):
    """Non-secret per-user provider preference; credentials stay in backend env."""
    MODE_CHOICES = [('gemini', 'Google Gemini'), ('openai', 'OpenAI'), ('local', 'Local Repair Engine'), ('automatic', 'Automatic Fallback')]
    PROVIDER_CHOICES = [('gemini', 'Google Gemini'), ('openai', 'OpenAI')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_provider_settings')
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default='gemini')
    primary_provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default='gemini')
    secondary_provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default='openai')
    automatic_fallback = models.BooleanField(default=False)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.primary_provider == self.secondary_provider:
            raise ValidationError({'secondary_provider': 'Choose a different secondary provider.'})



