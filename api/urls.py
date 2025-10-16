from django.urls import path
from . import views


urlpatterns = [
    path("user/me/", views.CurrentUserView.as_view(), name="current-user"),
    
    # Liste des films
    path('movies/', views.MovieListView.as_view(), name='movie-list'),

    # Détail d'un film
    path('movies/<int:pk>/', views.MovieDetailView.as_view(), name='movie-detail'),

    # Création / listing des commentaires d'un film
    path('movies/<int:movie_id>/comments/', views.MovieCommentListCreateView.as_view(), name='movie-comments'),

    # Like / unlike toggle d'un film
    path('movies/<int:movie_id>/like/', views.toggle_like, name='movie-like'),

    # Notation d'un film
    path('movies/<int:movie_id>/rate/', views.MovieRatingCreateUpdateView.as_view(), name='movie-rating'),

]