from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Q
from django.utils import timezone
from django.conf import settings



class Actor(models.Model):
    """
    Modèle pour un acteur.
    """
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    biography = models.TextField(blank=True)
    photo = models.ImageField(upload_to='actors/photos/', null=True, blank=True)

    def save(self, *args, **kwargs):
        # Remplir full_name si vide
        if not self.full_name:
            if self.first_name:
                self.full_name = f"{self.first_name} {self.last_name}"
            else:
                self.full_name = self.last_name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class Movie(models.Model):
    """
    Modèle principal pour un film.
    - duration: stocké sous forme de minutes (IntegerField) pour simplicité et calcul facile.
      On peut aussi utiliser DurationField si tu préfères timedelta.
    """
    title_fr = models.CharField("Titre (FR)", max_length=255)
    title_original = models.CharField("Titre original", max_length=255, blank=True)
    origin_country = models.CharField("Pays d'origine", max_length=100, blank=True)
    duration_minutes = models.PositiveIntegerField("Durée (minutes)", null=True, blank=True,
                                                   help_text="Durée du film en minutes (ex: 125)")
    director = models.CharField("Réalisateur", max_length=255, blank=True)
    description = models.TextField("Descriptif", blank=True)
    release_date = models.DateField("Date de sortie", null=True, blank=True)
    poster = models.ImageField("Affiche", upload_to='movies/posters/', null=True, blank=True)
    illustration = models.ImageField("Image d'illustration", upload_to='movies/illustrations/', null=True, blank=True)
    cast = models.ManyToManyField(Actor, through='Casting', related_name='movies', blank=True)

    # champs dénormalisés (optionnels) — seront tenus à jour par signaux
    likes_count = models.PositiveIntegerField(default=0)
    avg_rating = models.FloatField(null=True, blank=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-release_date', 'title_fr']

    def __str__(self):
        return self.title_fr or self.title_original or f"Movie {self.pk}"

    # --- helpers pour durée en heures/minutes ---
    @property
    def duration_h_m(self):
        """Retourne (hours, minutes) ou None si duration_minutes absent."""
        if self.duration_minutes is None:
            return None
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        return hours, minutes

    def duration_display(self):
        """Affichage lisible '1h 45m' ou '45m'"""
        hm = self.duration_h_m
        if hm is None:
            return ""
        h, m = hm
        if h:
            return f"{h}h {m}m"
        return f"{m}m"

    # --- statistiques basées sur les relations utilisateur ---
    def likes_count(self):
        """Nombre total de likes (True) pour ce film."""
        return Like.objects.filter(movie=self, liked=True).count()

    def average_rating(self):
        """Moyenne des notes (float) ou None si pas de notes."""
        agg = Rating.objects.filter(movie=self).aggregate(avg=Avg('score'))
        return agg['avg']  # None si pas de notes

    def user_liked(self, user):
        """Retourne True/False selon si l'utilisateur a liké ce film (ou None si pas d'objet)."""
        if not user or not user.is_authenticated:
            return False
        try:
            rel = Like.objects.get(movie=self, user=user)
            return bool(rel.liked)
        except Like.DoesNotExist:
            return False

    def user_rating(self, user):
        """Retourne la note donnée par l'utilisateur (int) ou None."""
        if not user or not user.is_authenticated:
            return None
        try:
            return Rating.objects.get(movie=self, user=user).score
        except Rating.DoesNotExist:
            return None


class Casting(models.Model):
    """
    Table intermédiaire entre Movie et Actor pour gérer le rôle (ex: 'Jean Valjean'),
    l'ordre d'apparition, etc.
    """
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    actor = models.ForeignKey(Actor, on_delete=models.CASCADE)
    role_name = models.CharField("Rôle", max_length=200, blank=True)
    order = models.PositiveIntegerField("Ordre", default=0)

    class Meta:
        unique_together = ('movie', 'actor', 'role_name')
        ordering = ['order']

    def __str__(self):
        if self.role_name:
            return f"{self.actor} as {self.role_name} ({self.movie})"
        return f"{self.actor} in {self.movie}"


class Like(models.Model):
    """
    Like par utilisateur : on garde l'information par user+movie.
    - Si l'utilisateur 'like', liked=True.
    - Si l'utilisateur 'unlike' on peut soit supprimer l'instance soit la mettre à False.
      Ici on stocke explicitement liked=True/False pour historique.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_likes')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='likes')
    liked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # optionnel : pourquoi l'utilisateur a liké, etc.
    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user} {'likes' if self.liked else 'does not like'} {self.movie}"


class Rating(models.Model):
    """
    Note donnée par un utilisateur pour un film.
    score: entier (1..10) — adapte selon ton système (1..5, 0..10, etc.)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_ratings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='ratings')
    score = models.PositiveSmallIntegerField() 
    review = models.TextField(blank=True)  # optionnel : commentaire
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'movie')

    def __str__(self):
        return f"{self.user} -> {self.score} for {self.movie}"


class Comment(models.Model):
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comment by {self.author or "anon"} on {self.movie}'