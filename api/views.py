from django.shortcuts import render
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from rest_framework.permissions import AllowAny, IsAuthenticated
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


class MovieCommentsListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        movie_id = self.kwargs.get('movie_id')
        return Comment.objects.filter(movie_id=movie_id).select_related('author')

    def perform_create(self, serializer):
        movie_id = self.kwargs.get('movie_id')
        movie = generics.get_object_or_404(Movie, pk=movie_id)
        serializer.save(author=self.request.user if self.request.user.is_authenticated else None, movie=movie)


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

    def post(self, request, movie_id, *args, **kwargs):
        movie = get_object_or_404(Movie, pk=movie_id)
        serializer = RatingSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        score = serializer.validated_data['score']

        # soit on met à jour, soit on crée
        rating, created = Rating.objects.update_or_create(
            user=request.user,
            movie=movie,
            defaults={'score': score}
        )

        # recalcul de la moyenne
        agg = Rating.objects.filter(movie=movie).aggregate(avg=Avg('score'))
        avg = agg['avg'] or 0.0
        movie.avg_rating = avg
        movie.save(update_fields=['avg_rating'])

        data = {
            'rating': RatingSerializer(rating).data,
            'avg_rating': avg
        }
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
