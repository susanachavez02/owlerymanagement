from django.db import migrations

def create_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.get_or_create(name='Admin')
    Role.objects.get_or_create(name='Attorney')
    Role.objects.get_or_create(name='Client')

def reverse_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.filter(name__in=['Admin', 'Attorney', 'Client']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_onboardingkey_roles'),
    ]

    operations = [
        migrations.RunPython(create_roles, reverse_roles),
    ]