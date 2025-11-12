# Service Finder - Local Services Marketplace

A Python-based web application for finding and booking local services like plumbers, electricians, painters, and carpenters.

## Features

- **Customer Portal**: Browse, search, and book nearby services
- **Service Provider Portal**: List services and manage bookings
- **Location-based Search**: Find services within a specified radius
- **Ratings & Reviews**: Rate and review services after booking
- **Responsive Design**: Mobile-friendly interface with dark theme
- **Fake Payment Gateway**: Support for online and cash payments

## Technology Stack

- **Backend**: Django, MySQL, Django REST Framework
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap
- **Database**: MySQL 8.0
- **Containerization**: Docker & Docker Compose
- **Authentication**: Token-based authentication

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd servicefinder
```

### 2. Build and Run with Docker

#### For Windows:

```cmd
# Build and start all services
docker-compose up --build

# Run in detached mode (background)
docker-compose up --build -d
```

#### For Ubuntu/Linux:

```bash
# Build and start all services
sudo docker-compose up --build

# Run in detached mode (background)
sudo docker-compose up --build -d
```

### 3. Initialize Database

Once the containers are running, initialize the database:

#### Windows:
```cmd
# Run migrations
docker-compose exec web python manage.py migrate

# Create fake data
docker-compose exec web python manage.py populate_fake_data

# Create superuser (optional)
docker-compose exec web python manage.py createsuperuser
```

#### Ubuntu/Linux:
```bash
# Run migrations
sudo docker-compose exec web python manage.py migrate

# Create fake data
sudo docker-compose exec web python manage.py populate_fake_data

# Create superuser (optional)
sudo docker-compose exec web python manage.py createsuperuser
```

### 4. Access the Application

- **Web Application**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin
- **MySQL Database**: localhost:3306

## Default Test Accounts

After running `populate_fake_data`, you can use these accounts:

### Customers:
- Username: `customer1` to `customer10`
- Password: `password123`

### Service Providers:
- Username: `provider1` to `provider5`
- Password: `password123`

## Docker Services

The application consists of two main services:

### Web Service (Django)
- **Port**: 8000
- **Environment**: Production-ready with Gunicorn
- **Volume**: `./backend:/app` (for development)

### Database Service (MySQL)
- **Port**: 3306
- **Database**: `servicefinder`
- **Username**: `serviceuser`
- **Password**: `servicepass`
- **Root Password**: `rootpass`

## Development

### Local Development Setup

For local development without Docker:

1. **Install Python Dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

2. **Set Environment Variables**:
```bash
# Create .env file with USE_SQLITE=True for local development
echo "USE_SQLITE=True" >> .env
```

3. **Run Migrations**:
```bash
python manage.py migrate
```

4. **Create Fake Data**:
```bash
python manage.py populate_fake_data
```

5. **Start Development Server**:
```bash
python manage.py runserver
```

### Useful Docker Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs web
docker-compose logs db

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose build web

# Execute commands in running container
docker-compose exec web python manage.py shell

# Remove all containers and volumes
docker-compose down -v
```

## Project Structure

```
servicefinder/
├── backend/
│   ├── servicefinder_backend/    # Django project settings
│   ├── usermgmt/                 # User management app
│   ├── servicemgmt/              # Service management app
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── docker-compose.yml
└── README.md
```

## Environment Variables

Key environment variables in `backend/.env`:

- `USE_SQLITE`: Set to `False` for MySQL, `True` for SQLite
- `DJANGO_SECRET_KEY`: Django secret key
- `DJANGO_DEBUG`: Debug mode (True/False)
- `MYSQL_DATABASE`: Database name
- `MYSQL_USER`: Database user
- `MYSQL_PASSWORD`: Database password
- `MYSQL_HOST`: Database host (use `db` for Docker)

## Troubleshooting

### Common Issues:

1. **Port Already in Use**:
   - Change ports in `docker-compose.yml`
   - Or stop conflicting services

2. **Database Connection Issues**:
   - Ensure MySQL container is running
   - Check environment variables in `.env`

3. **Permission Issues (Linux)**:
   - Use `sudo` with docker commands
   - Or add user to docker group

4. **Container Build Failures**:
   - Clear Docker cache: `docker system prune`
   - Rebuild: `docker-compose build --no-cache`

### Getting Help

- Check container logs: `docker-compose logs [service-name]`
- Verify container status: `docker-compose ps`
- Access container shell: `docker-compose exec web bash`

## License

This project is for educational purposes.
