from peewee import Model, IntegerField, BooleanField, FloatField
from db_utils.db import db

class Guild(Model):
    id = IntegerField(primary_key=True)
    loop_queue = BooleanField(null=False)
    shuffle_queue = BooleanField(null=False)
    volume = FloatField(default=1.0, null=False)  # Volume level (0.0 to 1.0)
    bass_boost = FloatField(default=0.0, null=False)  # Bass boost level (0.0 to 2.0)

    class Meta:
        database = db
        table_name = 'guilds'