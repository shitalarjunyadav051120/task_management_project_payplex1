# Task Management System

A Django REST Framework based Task Management System with JWT Authentication, Role-Based Access Control, PostgreSQL, Redis, Celery, and Email Notifications.

## Features

- JWT Authentication
- Role-Based Access Control
  - Admin
  - Manager
  - Employee
- User Management
- Task Management
- Task Assignment
- Task Status Tracking
- Task Comments
- Task History Audit
- Email Notifications
- Celery Background Tasks
- Redis Message Broker
- PostgreSQL Database

---

## Tech Stack

- Python 3.12
- Django 5.x
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- JWT Authentication
- drf-spectacular (Swagger/OpenAPI)

---

## Project Structure

```text
apps/
├── authentication/
├── tasks/
├── notifications/

config/
manage.py
requirements.txt
```

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd task_management_project
```

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create `.env`

```env
SECRET_KEY=your_secret_key

DB_NAME=task_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
```

### Run Migrations

```bash
python manage.py migrate
```

### Create Superuser

```bash
python manage.py createsuperuser
```

---

## Start Services

### Django

```bash
python manage.py runserver
```

### Redis

```bash
sudo service redis-server start
```

### Celery

```bash
celery -A config worker -l info
```

---

## Authentication APIs

### Login

POST

```http
/api/v1/auth/login/
```

Payload

```json
{
  "email": "admin@example.com",
  "password": "Password123"
}
```

---

## User APIs

### Create User

POST

```http
/api/v1/auth/users/
```

---

## Task APIs

### Create Task

POST

```http
/api/v1/tasks/
```

### Get Tasks

GET

```http
/api/v1/tasks/
```

### Update Task Status

PATCH

```http
/api/v1/tasks/{id}/status/
```

---

## Notifications

Email notifications are sent when:

- Task is assigned
- Task status is updated

Notifications are processed asynchronously using Celery and Redis.

---

## Testing

### Run Tests

```bash
python manage.py test
```
Testing has been done by using postman
---

## Author

Shital Yadav