from tortoise import fields, models


class Channel(models.Model):
    id = fields.IntField(pk=True, generated=False)
    link = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    logo_id = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class ChannelStatistics(models.Model):
    id = fields.IntField(pk=True)
    channel = fields.ForeignKeyField("models.Channel", related_name="statistics")
    subscribers = fields.IntField()
    views_24h = fields.IntField()
    recorded_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("channel", "recorded_at")
    
    def __str__(self):
        return f"{self.channel.name} - {self.recorded_at}"