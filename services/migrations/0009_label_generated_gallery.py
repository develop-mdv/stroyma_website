from pathlib import PurePosixPath

from django.db import migrations


def label_generated_gallery(apps, schema_editor):
    ServicePhoto = apps.get_model('services', 'ServicePhoto')
    for photo in ServicePhoto.objects.using(schema_editor.connection.alias).filter(
        service__slug='kolirovka', title__startswith='Пример работы '
    ):
        # Only the gallery files inserted by tools/attach_gallery.py.
        filename = PurePosixPath(photo.image.name).name
        if filename.startswith('gallery_kolirovka_'):
            photo.title = photo.title.replace('Пример работы ', 'Иллюстрация услуги ', 1)
            photo.save(using=schema_editor.connection.alias, update_fields=['title'])


class Migration(migrations.Migration):
    dependencies = [('services', '0008_review_service_copy')]
    operations = [migrations.RunPython(label_generated_gallery, migrations.RunPython.noop)]
