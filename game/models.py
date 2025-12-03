import string
import random
from django.db import models
from django.contrib.postgres.fields import ArrayField

def generate_unique_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase, k=length))

class Room(models.Model):
    code = models.CharField(max_length=6, unique=True)
    player1 = models.CharField(max_length=50, blank=True, null=True)
    player2 = models.CharField(max_length=50, blank=True, null=True)
    current_turn = models.CharField(max_length=10, blank=True, null=True)
    player1_grid = models.JSONField(default=list)
    player2_grid = models.JSONField(default=list)
    rematch_votes = models.JSONField(default=list)

    def __str__(self):
        return self.code
