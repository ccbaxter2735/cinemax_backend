from django.contrib import admin

# Register your models here.
from .models import Movie, Actor, Comment, Casting

admin.site.register(Movie)
admin.site.register(Actor)
admin.site.register(Casting)
admin.site.register(Comment)
