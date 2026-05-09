# Django Blog API

## Features
- JWT Authentication
- Email OTP Verification
- Google Login
- Blog CRUD
- Comments & Likes
- Follow/Unfollow
- Notifications
- Caching (Redis)
- Celery Tasks
- Docker Setup

## Setup
1. Clone repo
2. Create .env file (see .env.example)
3. Run: docker compose up --build
4. Run: docker compose exec web python manage.py migrate
