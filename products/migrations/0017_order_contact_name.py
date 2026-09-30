from django.db import migrations, models


def combine_customer_names(apps, schema_editor):
    OrderContact = apps.get_model('products', 'OrderContact')
    database = schema_editor.connection.alias
    batch = []
    for contact in OrderContact.objects.using(database).iterator(chunk_size=500):
        contact.name = ' '.join(
            part for part in (contact.first_name, contact.last_name) if part
        )
        batch.append(contact)
        if len(batch) >= 500:
            OrderContact.objects.using(database).bulk_update(batch, ['name'])
            batch.clear()
    if batch:
        OrderContact.objects.using(database).bulk_update(batch, ['name'])


class Migration(migrations.Migration):
    dependencies = [('products', '0016_order_snapshot_and_notification')]

    operations = [
        migrations.AddField(
            model_name='ordercontact',
            name='name',
            field=models.CharField(max_length=255, null=True, verbose_name='Имя или название организации'),
        ),
        migrations.RunPython(combine_customer_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='ordercontact',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Имя или название организации'),
        ),
        migrations.RemoveField(model_name='ordercontact', name='first_name'),
        migrations.RemoveField(model_name='ordercontact', name='last_name'),
    ]
