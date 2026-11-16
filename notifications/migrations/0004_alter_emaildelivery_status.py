from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notifications", "0003_emaildelivery")]

    operations = [
        migrations.AlterField(
            model_name="emaildelivery",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("SENT", "Sent"),
                    ("FAILED", "Failed"),
                    ("EXPIRED", "Expired"),
                ],
                default="PENDING",
                max_length=10,
            ),
        ),
    ]
