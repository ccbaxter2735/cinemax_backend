from django.shortcuts import render
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from rest_framework.views import APIView
from django.db.models import Avg

from .models import *
from .serializers import *

class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny,]


class CurrentUserView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)

class MovieListView(generics.ListAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]


class MovieDetailView(generics.RetrieveAPIView):
    queryset = Movie.objects.all()
    serializer_class = MovieDetailSerializer
    permission_classes = [permissions.AllowAny]



class MovieActorListCreateView(generics.ListCreateAPIView): 
    serializer_class = CastingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        movie_id = self.kwargs['movie_id']
        return Casting.objects.filter(movie_id=movie_id).select_related('actor')

class MovieCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        movie_id = self.kwargs['movie_id']
        movie = get_object_or_404(Movie, pk=movie_id)
        return movie.comments.all()

    def perform_create(self, serializer):
        movie_id = self.kwargs['movie_id']
        movie = get_object_or_404(Movie, pk=movie_id)
        # Lier éventuellement la note de l'utilisateur si elle existe
        from .models import Rating
        try:
            rating = Rating.objects.get(movie=movie, user=self.request.user)
        except Rating.DoesNotExist:
            rating = None
        serializer.save(author=self.request.user, movie=movie, rating=rating)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_like(request, movie_id):
    movie = get_object_or_404(Movie, pk=movie_id)
    user = request.user
    like, created = Like.objects.get_or_create(movie=movie, user=user)
    like.liked = not like.liked if not created else True
    like.save()
    return Response({
        "liked": like.liked,
        "likes_count": movie.likes_count
    })


class MovieRatingCreateUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, movie_id):
        movie = get_object_or_404(Movie, pk=movie_id)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        score = serializer.validated_data['score']

        # Crée ou met à jour la note
        rating, created = Rating.objects.update_or_create(
            user=request.user,
            movie=movie,
            defaults={'score': score}
        )

        # Recalcul de la moyenne
        avg = Rating.objects.filter(movie=movie).aggregate(avg=Avg('score'))['avg'] or 0.0
        movie.avg_rating = avg
        movie.save(update_fields=['avg_rating'])

        return Response({'rating': RatingSerializer(rating).data, 'avg_rating': avg})


class ActorMovieListView(generics.ListAPIView):
    """
    GET /api/actors/<actor_id>/movies/
    Retourne la liste des films où l'acteur apparaît.
    """
    serializer_class = MovieListSerializer
    permission_classes = [permissions.AllowAny]  # ou IsAuthenticatedOrReadOnly si tu veux restreindre

    def get_queryset(self):
        actor_id = self.kwargs.get('actor_id')
        # vérifier que l'acteur existe (404 si non)
        get_object_or_404(Actor, pk=actor_id)

        # Requête : tous les films liés via la table de liaison (Casting)
        qs = Movie.objects.filter(cast__id=actor_id).distinct()

        # optimisation optionnelle
        qs = qs.select_related()  # si tu as des FK directes

        return qs

# class ActorView(generics.RetrieveAPIView):
#     """
#     GET /api/actors/<pk>/  -> renvoie la fiche détaillée d'un acteur.
#     Permission: lecture publique, modification réservée (ici on n'expose que GET).
#     """
#     queryset = Actor.objects.all()
#     serializer_class = ActorSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]
#     lookup_field = "pk"

  
#     def get_queryset(self):
#         # si tu as des relations à précharger (ex: photo stockée ailleurs), adapte ici
#         return super().get_queryset()
