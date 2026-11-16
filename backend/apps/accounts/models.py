from django.conf import settings
from django.db import models


DEFAULT_AI_PROVIDER_SETTINGS = {
    'mode': 'openai',
    'primary_provider': 'openai',
    'secondary_provider': 'gemini',
    'automatic_fallback': False,
}


def default_ai_provider_settings():
    provider = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'openai')
    secondary = 'gemini' if provider == 'openai' else 'openai'
    defaults = dict(DEFAULT_AI_PROVIDER_SETTINGS)
    defaults.update(mode=provider, primary_provider=provider, secondary_provider=secondary)
    return defaults


class AIProviderSettings(models.Model):
    """Non-secret per-user provider preference; credentials stay in backend env."""
    MODE_CHOICES = [('gemini', 'Google Gemini'), ('openai', 'OpenAI'), ('local', 'Local Repair Engine'), ('automatic', 'Automatic Fallback')]
    PROVIDER_CHOICES = [('gemini', 'Google Gemini'), ('openai', 'OpenAI')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_provider_settings')
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default=DEFAULT_AI_PROVIDER_SETTINGS['mode'])
    primary_provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default=DEFAULT_AI_PROVIDER_SETTINGS['primary_provider'])
    secondary_provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default=DEFAULT_AI_PROVIDER_SETTINGS['secondary_provider'])
    automatic_fallback = models.BooleanField(default=DEFAULT_AI_PROVIDER_SETTINGS['automatic_fallback'])

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.primary_provider == self.secondary_provider:
            raise ValidationError({'secondary_provider': 'Choose a different secondary provider.'})

