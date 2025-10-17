from tortoise import fields
from tortoise.models import Model


class Client(Model):
    id = fields.IntField(pk=True)
    telegram_credentials = fields.ForeignKeyField(
        "models.TelegramCredentials", related_name="client", on_delete=fields.CASCADE
    )
    users_count = fields.IntField(default=0)
    working = fields.BooleanField(default=True)
    is_master = fields.BooleanField(default=False)
    phone_number = fields.CharField(max_length=32, null=True)
    master_client = fields.ForeignKeyField(
        "models.Client",
        related_name="child_clients",
        null=True,
        on_delete=fields.CASCADE,
    )


class TelegramCredentials(Model):
    id = fields.IntField(pk=True)
    api_id = fields.IntField()
    api_hash = fields.CharField(max_length=255)
    device_model = fields.CharField(max_length=255)
    system_version = fields.CharField(max_length=50)
    app_version = fields.CharField(max_length=50)
    lang_code = fields.CharField(max_length=10)
    system_lang_code = fields.CharField(max_length=10)
    lang_pack = fields.CharField(max_length=10)
