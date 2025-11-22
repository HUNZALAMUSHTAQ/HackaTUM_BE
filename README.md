# User Management API

A simple FastAPI backend with SQLite database for managing users and their preferences.

## Features

- User management with fields: Name, Age, Gender, Sporty Cars, Location
- Preferences management with question types (boolean/text), questions, answers, and frustration tracking
- RESTful API endpoints

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation (Swagger)

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs` - Interactive API documentation with try-it-out functionality
- **ReDoc**: `http://localhost:8000/redoc` - Alternative API documentation
- **OpenAPI Schema**: `http://localhost:8000/openapi.json` - Raw OpenAPI JSON schema

The Swagger UI provides:
- Complete API endpoint documentation
- Request/response schemas with examples
- Interactive testing interface
- Try-it-out functionality for all endpoints

## Endpoints

### Create User
- **POST** `/users`
- Request body:
```json
{
  "name": "John Doe",
  "age": 30,
  "gender": "Male",
  "sporty_cars": "Ferrari, Lamborghini",
  "location": "Munich",
  "preferences": [
    {
      "question_type": "boolean",
      "question_string": "Do you like fast cars?",
      "answer_string": "Yes",
      "frustrated": false
    }
  ]
}
```

### Get All Users
- **GET** `/users?skip=0&limit=100`

### Get User by ID
- **GET** `/users/{user_id}`

## Database

The SQLite database file (`app.db`) will be created automatically when you first run the application.

