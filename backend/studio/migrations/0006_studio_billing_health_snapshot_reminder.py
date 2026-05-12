import datetime

from django.db import migrations, models
from django.utils import timezone


def seed_studio_billing(apps, schema_editor):
    StudioBilling = apps.get_model("studio", "StudioBilling")
    if StudioBilling.objects.filter(pk=1).exists():
        return
    StudioBilling.objects.create(
        pk=1,
        paid_until=timezone.now() + datetime.timedelta(days=3650),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0005_appointment_payload_duration_privacy"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudioBilling",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("paid_until", models.DateTimeField(help_text="Acesso ao sistema liberado ate este instante (UTC logico com USE_TZ).")),
                ("payment_cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("last_payment_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("last_payment_attempt_ok", models.BooleanField(blank=True, null=True)),
                ("last_payment_attempt_note", models.CharField(blank=True, max_length=500)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name_plural": "Studio billing",
            },
        ),
        migrations.AddField(
            model_name="appointment",
            name="health_snapshot",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Copia da ficha de saude no momento da criacao do agendamento (DVP HU06).",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="reminder_email_sent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Quando o lembrete por e-mail (30 min antes) foi enviado (HU18).",
                null=True,
            ),
        ),
        migrations.RunPython(seed_studio_billing, migrations.RunPython.noop),
    ]
