from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('services', '0006_alter_service_image_alter_servicephoto_image_and_more'),
    ]

    operations = [
        migrations.DeleteModel(name='ServiceVideo'),
    ]
