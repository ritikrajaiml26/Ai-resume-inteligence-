# AI Resume Intelligence Platform

A production-ready AI-powered ATS Resume Analyzer & Resume Generator built with Django, Django REST Framework, Tailwind CSS, spaCy, NLTK, and OpenAI.

## Features

- User authentication with registration, login, logout, and password reset
- Resume upload support for PDF and DOCX
- Manual resume builder with sections for skills, education, experience, projects, certifications, and achievements
- Job description analysis with keyword extraction and required skill detection
- AI-powered resume optimization and summary generation
- ATS score engine with analytics and suggestions
- Multi-template resume preview and PDF export via WeasyPrint
- Responsive modern dashboard with animations and live preview
- Deployment-ready architecture with PostgreSQL and environment variables

## Setup

1. Clone the repository
2. Create and activate a Python virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy the example environment file

```bash
copy .env.example .env
```

4. Update `.env` with your `SECRET_KEY`, `DATABASE_URL`, and `OPENAI_API_KEY`

5. Install spaCy model and NLP data

```bash
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

6. Run migrations

```bash
python manage.py migrate
```

7. Create a superuser

```bash
python manage.py createsuperuser
```

8. Run the server

```bash
python manage.py runserver
```

## Deployment

- Use PostgreSQL for production
- Set `DEBUG=False`
- Configure `ALLOWED_HOSTS`
- Serve static files with WhiteNoise or a CDN
- Use Render, Heroku, or other cloud provider

## Environment Variables

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `OPENAI_API_KEY`

## Notes

This project is designed to be modular and scalable, with separate application layers for user management, resumes, AI engines, ATS scoring, templates, and analytics.
