# Generated manually to change default provider to OpenAI

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_default_gemini_provider'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aiprovidersettings',
            name='mode',
            field=models.CharField(choices=[('gemini', 'Google Gemini'), ('openai', 'OpenAI'), ('local', 'Local Repair Engine'), ('automatic', 'Automatic Fallback')], default='openai', max_length=16),
        ),
        migrations.AlterField(
            model_name='aiprovidersettings',
            name='primary_provider',
            field=models.CharField(choices=[('gemini', 'Google Gemini'), ('openai', 'OpenAI')], default='openai', max_length=16),
        ),
    ]
