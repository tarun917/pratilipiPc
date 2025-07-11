import uuid
from django.db import migrations
from django.db import models

def update_uuids(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            UPDATE creatorDesk_submissions
            SET id = INSERT(INSERT(INSERT(INSERT(id, 9, 0, '-'), 14, 0, '-'), 19, 0, '-'), 24, 0, '-')
            WHERE id NOT LIKE '________-____-____-____-____________';
        """)
        cursor.execute("""
            UPDATE creatorDesk_submissions
            SET id = 'test-uuid-0789-1234-5678-9012-345678901234'
            WHERE id = 'test-uuid-789';
        """)

class Migration(migrations.Migration):
    dependencies = [('creatorDesk', '0002_alter_submissions_status')]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE creatorDesk_creatorcomics DROP FOREIGN KEY creatorDesk_creatorc_submission_id_id_88917d6e_fk_creatorDe;"
        ),
        migrations.RunSQL(
            "ALTER TABLE creatorDesk_submissions MODIFY id CHAR(36);"
        ),
        migrations.RunPython(update_uuids),
        migrations.RunSQL(
            "ALTER TABLE creatorDesk_creatorcomics ADD FOREIGN KEY (submission_id_id) REFERENCES creatordesk_submissions(id);"
        ),
        migrations.AlterField(
            model_name='submissions',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False),
        ),
    ]