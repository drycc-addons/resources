# Generated migration for Drycc Resources API

import api.utils
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('uuid', models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, verbose_name='UUID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('app_id', models.CharField(db_index=True, max_length=63, validators=[api.utils.validate_label])),
                ('workspace_id', models.CharField(db_index=True, max_length=63)),
                ('name', models.CharField(max_length=63, validators=[api.utils.validate_label])),
                ('plan', models.CharField(max_length=128)),
                ('data', models.JSONField(blank=True, default=dict)),
                ('status', models.TextField(blank=True, null=True)),
                ('binding', models.TextField(blank=True, null=True)),
                ('options', models.JSONField(blank=True, default=dict)),
            ],
            options={
                'ordering': ['-created'],
                'get_latest_by': 'created',
            },
        ),
        migrations.AddIndex(
            model_name='resource',
            index=models.Index(fields=['app_id', 'workspace_id'], name='api_resource_app_ws_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='resource',
            unique_together={('app_id', 'name')},
        ),
    ]