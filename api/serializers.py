from django.contrib.auth.models import User
from rest_framework import serializers
from .models import *


# -----------------------
# User
# -----------------------
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}
        # le champ password ne doit pas être affiché dans la réponse POST

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


# -----------------------
# Actor
# -----------------------
class ActorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Actor
        fields = ['id', 'first_name', 'last_name', 'full_name', 'bio']

    def get_full_name(self, obj):
        if obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.first_name


# -----------------------
# Casting (relation Movie <-> Actor)
# -----------------------
class CastingSerializer(serializers.ModelSerializer):
    actor = ActorSerializer(read_only=True)
    actor_id = serializers.PrimaryKeyRelatedField(
        queryset=Actor.objects.all(), source='actor', write_only=True
    )

    class Meta:
        model = Casting
        fields = ['id', 'actor', 'actor_id', 'character_name', 'order']


# -----------------------
# Comment
# -----------------------
class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'movie', 'author', 'author_username', 'text', 'created_at']
        read_only_fields = ['id', 'author', 'author_username', 'created_at','movie']

    def get_author_username(self, obj):
        return obj.author.username if obj.author else None

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Le commentaire est vide.")
        if len(value) > 2000:
            raise serializers.ValidationError("Trop long (max 2000 caractères).")
        return value


# -----------------------
# Like
# -----------------------
class LikeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'user', 'movie', 'liked', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'user']

    def create(self, validated_data):
        """
        Crée ou met à jour le like pour que chaque user ait au plus une ligne par film.
        (La vue peut aussi utiliser get_or_create + toggle.)
        """
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError("Utilisation réservée aux utilisateurs authentifiés.")
        user = request.user
        movie = validated_data.get('movie')
        liked = validated_data.get('liked', True)
        obj, created = Like.objects.get_or_create(user=user, movie=movie, defaults={'liked': liked})
        if not created:
            obj.liked = liked
            obj.save()
        return obj


# -----------------------
# Rating
# -----------------------
class RatingSerializer(serializers.ModelSerializer):
    # on n'expose pas 'movie' ni 'user' en écriture — ils seront injectés côté view
    class Meta:
        model = Rating
        fields = ['id', 'score', 'created_at', 'updated_at']  # adapte si ton modèle a d'autres champs
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_score(self, value):
        # S'assurer que la note est entre 1 et 10 (ou l'échelle que tu utilises)
        try:
            v = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError(_("La note doit être un entier."))
        if v < 0 or v > 10:
            raise serializers.ValidationError(_("La note doit être comprise entre 0 et 10."))
        return v


# -----------------------
# Movie - listes & détails
# -----------------------
class MovieListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes"""
    avg_rating = serializers.FloatField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    poster = serializers.ImageField(read_only=True)
    release_date = serializers.DateField(read_only=True)

    class Meta:
        model = Movie
        fields = ['id', 'title_fr', 'title_original', 'poster', 'release_date', 'likes_count', 'avg_rating']


class MovieDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour affichage d'un film"""
    actors = CastingSerializer(source='movie_casts', many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    avg_rating = serializers.FloatField(read_only=True)
    poster = serializers.ImageField(read_only=True)
    cover_image = serializers.ImageField(read_only=True)
    duration = serializers.SerializerMethodField()
    user_liked = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        # inclure les champs principaux + relations utiles en lecture
        fields = [
            'id', 'title_fr', 'title_original', 'origin_country', 'duration_minutes', 'duration',
            'director', 'description', 'release_date',
            'poster', 'cover_image',
            'likes_count', 'avg_rating',
            'actors', 'comments',
            'user_liked', 'user_rating',
            'created_at', 'updated_at'
        ]

    def get_duration(self, obj):
        # renvoie chaîne lisible "1h 32m"
        return obj.duration_display()

    def get_user_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.user_liked(request.user)

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return obj.user_rating(request.user)


# -----------------------
# Movie - création / modification (write)
# -----------------------
class MovieCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer / mettre à jour un film.
    - actors can be set by providing a list of dicts: [{"actor_id": pk, "character_name":"X", "order":0}, ...]
    - poster / cover_image are writable ImageFields
    """
    # accepts nested cast for creation/update (write-only)
    cast = CastingSerializer(source='movie_casts', many=True, required=False, write_only=True)
    poster = serializers.ImageField(required=False, allow_null=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Movie
        fields = [
            'id', 'title_fr', 'title_original', 'origin_country', 'duration_minutes',
            'director', 'description', 'release_date',
            'poster', 'cover_image',
            'cast',
        ]

    def create(self, validated_data):
        cast_data = validated_data.pop('movie_casts', [])
        movie = Movie.objects.create(**validated_data)
        # create Casting entries if provided
        for item in cast_data:
            actor = item.get('actor')
            character_name = item.get('character_name', '')
            order = item.get('order', 0)
            Casting.objects.create(movie=movie, actor=actor, character_name=character_name, order=order)
        return movie

    def update(self, instance, validated_data):
        cast_data = validated_data.pop('movie_casts', None)
        # update simple fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if cast_data is not None:
            # remplacer le casting actuel par le nouveau
            instance.movie_casts.all().delete()
            for item in cast_data:
                actor = item.get('actor')
                character_name = item.get('character_name', '')
                order = item.get('order', 0)
                Casting.objects.create(movie=instance, actor=actor, character_name=character_name, order=order)
        return instance