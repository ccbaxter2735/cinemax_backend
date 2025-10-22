# 🎬 CINEMAX — Backend (Django REST API)

API REST développée avec **Django** et **Django REST Framework** pour alimenter l’application CINEMAX.  
Elle gère les **films**, **acteurs**, **commentaires**, **notes** et l’**authentification** des utilisateurs.

---

## ⚙️ Fonctionnalités principales
- Gestion complète des **films** et **acteurs**  
- Authentification JWT  
- Ajout de **commentaires** et **notes** pour les films  
- Recherche globale (films et acteurs)  
- Stockage des images sur **Amazon S3**

---

## 🚀 Technologies
- **Django 5**
- **Django REST Framework**
- **PostgreSQL**
- **Amazon S3** (media & static files)
- **Render** (hébergement)

> ⚠️ Hébergé sur un compte gratuit Render — le premier chargement peut prendre quelques secondes.

---

## 🧪 Installation locale

```bash
git clone https://github.com/ton-compte/cinemax-backend.git
cd cinemax-backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
