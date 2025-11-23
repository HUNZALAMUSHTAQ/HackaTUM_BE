from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import models
import schemas
from database import get_db, init_db
from celery_tasks import generate_questions_task, generate_vehicle_recommendation_task

app = FastAPI(
    title="User Management API",
    description="A simple REST API for managing users and their preferences using FastAPI and SQLite",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI documentation
    redoc_url="/redoc",  # ReDoc alternative documentation
    openapi_url="/openapi.json"  # OpenAPI schema URL
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get(
    "/",
    tags=["General"],
    summary="Root endpoint",
    description="Welcome endpoint for the API"
)
async def root():
    """
    Root endpoint that returns a welcome message.
    """
    return {"message": "Welcome to User Management API"}


@app.post(
    "/users",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Create a new user",
    description="Create a new user with their basic information and optional preferences. "
                "The user will be assigned a unique ID automatically.",
    responses={
        201: {
            "description": "User created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "John Doe",
                        "age": 30,
                        "gender": "Male",
                        "location": "Munich",
                        "driving_style": "sporty",
                        "fuel_preference": "electric",
                        "budget_sensitivity": "medium",
                        "risk_tolerance": "high",
                        "preferences": [
                            {
                                "id": 1,
                                "user_id": 1,
                                "status": "completed",
                                "created_at": "2024-01-01T00:00:00",
                                "updated_at": "2024-01-01T00:00:00",
                                "questions": [
                                    {
                                        "id": 1,
                                        "question_type": "choice",
                                        "category": "driving_style",
                                        "question": "What is your preferred driving style?",
                                        "options": ["sporty", "relaxed", "balanced"],
                                        "answer": "sporty",
                                        "answer_score": 4,
                                        "importance": 5,
                                        "frustrated": False
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        },
        400: {
            "description": "Bad request - Invalid input data"
        }
    }
)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user with optional preferences.
    
    - **name**: Full name of the user (required)
    - **age**: Age of the user, must be 0 or greater (required)
    - **gender**: Gender of the user (required)
    - **location**: Location of the user (required)
    - **driving_style**: Driving style preference - sporty, relaxed, balanced (optional)
    - **fuel_preference**: Fuel preference - petrol, hybrid, electric (optional)
    - **budget_sensitivity**: Budget sensitivity - low, medium, high (optional)
    - **risk_tolerance**: Risk tolerance - low, medium, high (optional)
    """
    # Create user
    db_user = models.User(
        name=user.name,
        age=user.age,
        gender=user.gender,
        location=user.location,
        driving_style=user.driving_style,
        fuel_preference=user.fuel_preference,
        budget_sensitivity=user.budget_sensitivity,
        risk_tolerance=user.risk_tolerance
    )
    
    db.add(db_user)
    db.flush()  # Flush to get the user ID
    
    db.commit()
    db.refresh(db_user)
    
    # Return user with empty preferences (since none were created)
    return schemas.UserResponse(
        id=db_user.id,
        name=db_user.name,
        age=db_user.age,
        gender=db_user.gender,
        location=db_user.location,
        driving_style=db_user.driving_style,
        fuel_preference=db_user.fuel_preference,
        budget_sensitivity=db_user.budget_sensitivity,
        risk_tolerance=db_user.risk_tolerance,
        preferences=[]
    )


@app.get(
    "/users",
    response_model=List[schemas.UserResponse],
    tags=["Users"],
    summary="Get all users",
    description="Retrieve a list of all users with pagination support. "
                "Returns users with their associated preferences.",
    responses={
        200: {
            "description": "List of users retrieved successfully"
        }
    }
)
def get_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Get all users with pagination.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    """
    if limit > 1000:
        limit = 1000
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    # Convert users with properly formatted preferences and questions
    result = []
    for user in users:
        preferences_data = []
        for pref in user.preferences:
            questions_data = []
            for q in pref.questions:
                questions_data.append({
                    "id": q.id,
                    "question_type": q.question_type,
                    "category": q.category,
                    "question": q.question,
                    "options": q.options_list,
                    "answer": q.answer,
                    "answer_score": q.answer_score,
                    "importance": q.importance,
                    "frustrated": q.frustrated
                })
            
            preferences_data.append(schemas.PreferenceResponse(
                id=pref.id,
                user_id=pref.user_id,
                status=pref.status,
                created_at=pref.created_at,
                updated_at=pref.updated_at,
                questions=[schemas.QuestionResponse(**q_data) for q_data in questions_data]
            ))
        
        result.append(schemas.UserResponse(
            id=user.id,
            name=user.name,
            age=user.age,
            gender=user.gender,
            location=user.location,
            driving_style=user.driving_style,
            fuel_preference=user.fuel_preference,
            budget_sensitivity=user.budget_sensitivity,
            risk_tolerance=user.risk_tolerance,
            preferences=preferences_data
        ))
    
    return result


@app.get(
    "/users/{user_id}",
    response_model=schemas.UserResponse,
    tags=["Users"],
    summary="Get user by ID",
    description="Retrieve a specific user by their unique ID along with all their preferences.",
    responses={
        200: {
            "description": "User found and returned successfully"
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            }
        }
    }
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get a specific user by ID.
    
    - **user_id**: The unique identifier of the user
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    # Convert user with properly formatted preferences and questions
    preferences_data = []
    for pref in user.preferences:
        questions_data = []
        for q in pref.questions:
            questions_data.append({
                "id": q.id,
                "question_type": q.question_type,
                "category": q.category,
                "question": q.question,
                "options": q.options_list,
                "answer": q.answer,
                "answer_score": q.answer_score,
                "importance": q.importance,
                "frustrated": q.frustrated
            })
        
        preferences_data.append(schemas.PreferenceResponse(
            id=pref.id,
            user_id=pref.user_id,
            status=pref.status,
            created_at=pref.created_at,
            updated_at=pref.updated_at,
            questions=[schemas.QuestionResponse(**q_data) for q_data in questions_data]
        ))
    
    return schemas.UserResponse(
        id=user.id,
        name=user.name,
        age=user.age,
        gender=user.gender,
        location=user.location,
        driving_style=user.driving_style,
        fuel_preference=user.fuel_preference,
        budget_sensitivity=user.budget_sensitivity,
        risk_tolerance=user.risk_tolerance,
        preferences=preferences_data
    )


# ==================== QUESTION ENDPOINTS ====================

@app.post(
    "/questions",
    response_model=schemas.QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Questions"],
    summary="Create a new question",
    description="Create a new question with question type, category, question text, and optional options.",
    responses={
        201: {
            "description": "Question created successfully"
        },
        400: {
            "description": "Bad request - Invalid input data"
        }
    }
)
def create_question(question: schemas.QuestionCreate, db: Session = Depends(get_db)):
    """
    Create a new question.
    
    - **question_type**: Type of question - boolean, text, scale, choice, multi_choice (required)
    - **category**: Category - driving_style, space, technology, fuel, risk, budget (required)
    - **question**: The question text (required)
    - **options**: List of available options for choice/multi_choice types (optional)
    - **answer**: Default or expected answer (optional)
    - **answer_score**: Default or expected score (optional)
    - **importance**: Default importance level 1-5 (default: 1)
    """
    db_question = models.Question(
        question_type=question.question_type,
        category=question.category,
        question=question.question,
        answer=question.answer,
        answer_score=question.answer_score,
        importance=question.importance
    )
    
    if question.options:
        db_question.set_options(question.options)
    
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    
    # Convert to response format with options_list -> options
    response_data = {
        "id": db_question.id,
        "question_type": db_question.question_type,
        "category": db_question.category,
        "question": db_question.question,
        "options": db_question.options_list,
        "answer": db_question.answer,
        "answer_score": db_question.answer_score,
        "importance": db_question.importance,
        "frustrated": db_question.frustrated
    }
    return schemas.QuestionResponse(**response_data)


@app.get(
    "/questions",
    response_model=List[schemas.QuestionResponse],
    tags=["Questions"],
    summary="Get all questions",
    description="Retrieve a list of all questions with pagination support.",
    responses={
        200: {
            "description": "List of questions retrieved successfully"
        }
    }
)
def get_questions(
    skip: int = 0,
    limit: int = 100,
    category: str = None,
    question_type: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all questions with optional filtering.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **category**: Filter by category (optional)
    - **question_type**: Filter by question type (optional)
    """
    if limit > 1000:
        limit = 1000
    
    query = db.query(models.Question)
    
    if category:
        query = query.filter(models.Question.category == category)
    if question_type:
        query = query.filter(models.Question.question_type == question_type)
    
    questions = query.offset(skip).limit(limit).all()
    # Convert to response format with options_list -> options
    return [
        schemas.QuestionResponse(
            id=q.id,
            question_type=q.question_type,
            category=q.category,
            question=q.question,
            options=q.options_list,
            answer=q.answer,
            answer_score=q.answer_score,
            importance=q.importance,
            frustrated=q.frustrated
        )
        for q in questions
    ]


@app.get(
    "/questions/{question_id}",
    response_model=schemas.QuestionResponse,
    tags=["Questions"],
    summary="Get question by ID",
    description="Retrieve a specific question by its unique ID.",
    responses={
        200: {
            "description": "Question found and returned successfully"
        },
        404: {
            "description": "Question not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Question not found"}
                }
            }
        }
    }
)
def get_question(question_id: int, db: Session = Depends(get_db)):
    """
    Get a specific question by ID.
    
    - **question_id**: The unique identifier of the question
    """
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    # Convert to response format with options_list -> options
    return schemas.QuestionResponse(
        id=question.id,
        question_type=question.question_type,
        category=question.category,
        question=question.question,
        options=question.options_list,
        answer=question.answer,
        answer_score=question.answer_score,
        importance=question.importance,
        frustrated=question.frustrated
    )


@app.put(
    "/questions/{question_id}",
    response_model=schemas.QuestionResponse,
    tags=["Questions"],
    summary="Update a question",
    description="Update an existing question by its ID.",
    responses={
        200: {
            "description": "Question updated successfully"
        },
        404: {
            "description": "Question not found"
        }
    }
)
def update_question(
    question_id: int,
    question: schemas.QuestionCreate,
    db: Session = Depends(get_db)
):
    """
    Update an existing question.
    
    - **question_id**: The unique identifier of the question to update
    - **question**: Updated question data
    """
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not db_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    db_question.question_type = question.question_type
    db_question.category = question.category
    db_question.question = question.question
    db_question.answer = question.answer
    db_question.answer_score = question.answer_score
    db_question.importance = question.importance
    
    if question.options:
        db_question.set_options(question.options)
    else:
        db_question.options = None
    
    db.commit()
    db.refresh(db_question)
    
    # Convert to response format with options_list -> options
    return schemas.QuestionResponse(
        id=db_question.id,
        question_type=db_question.question_type,
        category=db_question.category,
        question=db_question.question,
        options=db_question.options_list,
        answer=db_question.answer,
        answer_score=db_question.answer_score,
        importance=db_question.importance,
        frustrated=db_question.frustrated
    )


@app.delete(
    "/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Questions"],
    summary="Delete a question",
    description="Delete a question by its ID. This will also delete all associated preferences.",
    responses={
        204: {
            "description": "Question deleted successfully"
        },
        404: {
            "description": "Question not found"
        }
    }
)
def delete_question(question_id: int, db: Session = Depends(get_db)):
    """
    Delete a question by ID.
    
    - **question_id**: The unique identifier of the question to delete
    """
    db_question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not db_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    db.delete(db_question)
    db.commit()
    
    return None


# ==================== PREFERENCE ENDPOINTS ====================

@app.post(
    "/preferences",
    response_model=schemas.PreferenceCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Preferences"],
    summary="Create a new preference",
    description="Create a new preference session for a user. Questions will be generated in the background using Celery.",
    responses={
        201: {
            "description": "Preference created successfully, questions are being generated"
        },
        404: {
            "description": "User not found"
        }
    }
)
def create_preference(
    preference: schemas.PreferenceCreate,
    user_context: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new preference session for a user.
    
    - **user_id**: ID of the user (required)
    - **user_context**: Optional context about the user for AI question generation
    
    Questions will be generated asynchronously in the background.
    """
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == preference.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {preference.user_id} not found"
        )
    
    # Create preference
    db_preference = models.Preference(
        user_id=preference.user_id,
        status="pending"
    )
    
    db.add(db_preference)
    db.commit()
    db.refresh(db_preference)
    
    # Build user context string for AI
    if not user_context:
        user_context = f"User: {user.name}, Age: {user.age}, Gender: {user.gender}, Location: {user.location}"
        if user.driving_style:
            user_context += f", Driving Style: {user.driving_style}"
        if user.fuel_preference:
            user_context += f", Fuel Preference: {user.fuel_preference}"
        if user.budget_sensitivity:
            user_context += f", Budget Sensitivity: {user.budget_sensitivity}"
        if user.risk_tolerance:
            user_context += f", Risk Tolerance: {user.risk_tolerance}"
    
    # Trigger Celery task to generate questions
    task = generate_questions_task.delay(db_preference.id, user_context)
    
    return schemas.PreferenceCreateResponse(
        id=db_preference.id,
        user_id=db_preference.user_id,
        status=db_preference.status,
        created_at=db_preference.created_at,
        updated_at=db_preference.updated_at,
        task_id=task.id,
        message="Preference created. Questions are being generated in the background."
    )


@app.post(
    "/preferences/{preference_id}/generate-questions",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Preferences"],
    summary="Trigger question generation",
    description="Manually trigger question generation for a preference. This will run in the background.",
    responses={
        202: {
            "description": "Question generation started"
        },
        404: {
            "description": "Preference not found"
        }
    }
)
def trigger_question_generation(
    preference_id: int,
    user_context: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Manually trigger question generation for a preference.
    
    - **preference_id**: ID of the preference
    - **user_context**: Optional context about the user for AI question generation
    """
    preference = db.query(models.Preference).filter(models.Preference.id == preference_id).first()
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found"
        )
    
    # Build user context if not provided
    if not user_context and preference.user:
        user = preference.user
        user_context = f"User: {user.name}, Age: {user.age}, Gender: {user.gender}, Location: {user.location}"
        if user.driving_style:
            user_context += f", Driving Style: {user.driving_style}"
        if user.fuel_preference:
            user_context += f", Fuel Preference: {user.fuel_preference}"
    
    # Trigger Celery task
    task = generate_questions_task.delay(preference_id, user_context)
    
    return {
        "message": "Question generation started",
        "preference_id": preference_id,
        "task_id": task.id,
        "status": "generating"
    }


@app.get(
    "/preferences",
    response_model=List[schemas.PreferenceResponse],
    tags=["Preferences"],
    summary="Get all preferences",
    description="Retrieve a list of all preferences with pagination support.",
    responses={
        200: {
            "description": "List of preferences retrieved successfully"
        }
    }
)
def get_preferences(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all preferences with optional filtering.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **user_id**: Filter by user ID (optional)
    - **status**: Filter by status - pending, generating, completed, failed (optional)
    """
    if limit > 1000:
        limit = 1000
    
    query = db.query(models.Preference)
    
    if user_id:
        query = query.filter(models.Preference.user_id == user_id)
    if status:
        query = query.filter(models.Preference.status == status)
    
    preferences = query.offset(skip).limit(limit).all()
    
    # Convert preferences with properly formatted questions
    result = []
    for pref in preferences:
        questions_data = []
        for q in pref.questions:
            questions_data.append({
                "id": q.id,
                "question_type": q.question_type,
                "category": q.category,
                "question": q.question,
                "options": q.options_list,
                "answer": q.answer,
                "answer_score": q.answer_score,
                "importance": q.importance,
                "frustrated": q.frustrated
            })
        
        result.append(schemas.PreferenceResponse(
            id=pref.id,
            user_id=pref.user_id,
            status=pref.status,
            created_at=pref.created_at,
            updated_at=pref.updated_at,
            questions=[schemas.QuestionResponse(**q_data) for q_data in questions_data]
        ))
    
    return result


@app.get(
    "/preferences/{preference_id}",
    response_model=schemas.PreferenceResponse,
    tags=["Preferences"],
    summary="Get preference by ID",
    description="Retrieve a specific preference by its unique ID.",
    responses={
        200: {
            "description": "Preference found and returned successfully"
        },
        404: {
            "description": "Preference not found"
        }
    }
)
def get_preference(preference_id: int, db: Session = Depends(get_db)):
    """
    Get a specific preference by ID.
    
    - **preference_id**: The unique identifier of the preference
    """
    preference = db.query(models.Preference).filter(models.Preference.id == preference_id).first()
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found"
        )
    
    # Convert questions to proper format
    questions_data = []
    for q in preference.questions:
        questions_data.append({
            "id": q.id,
            "question_type": q.question_type,
            "category": q.category,
            "question": q.question,
            "options": q.options_list,
            "answer": q.answer,
            "answer_score": q.answer_score,
            "importance": q.importance,
            "frustrated": q.frustrated
        })
    
    return schemas.PreferenceResponse(
        id=preference.id,
        user_id=preference.user_id,
        status=preference.status,
        created_at=preference.created_at,
        updated_at=preference.updated_at,
        questions=[schemas.QuestionResponse(**q_data) for q_data in questions_data]
    )


@app.get(
    "/tasks/{task_id}/status",
    tags=["Tasks"],
    summary="Get task status",
    description="Get the status and result of a Celery task.",
    responses={
        200: {
            "description": "Task status retrieved successfully"
        },
        404: {
            "description": "Task not found"
        }
    }
)
def get_task_status(task_id: str):
    """
    Get the status of a Celery task.
    
    - **task_id**: The Celery task ID returned when creating a preference
    
    Returns task state: PENDING, STARTED, SUCCESS, FAILURE, RETRY
    """
    from celery_tasks import generate_questions_task
    
    task = generate_questions_task.AsyncResult(task_id)
    
    if task.state == "PENDING":
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task is waiting to be processed"
        }
    elif task.state == "FAILURE":
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task failed",
            "error": str(task.info) if task.info else "Unknown error"
        }
    elif task.state == "SUCCESS":
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": "Task completed successfully",
            "result": task.result
        }
    else:
        response = {
            "task_id": task_id,
            "state": task.state,
            "status": f"Task is {task.state.lower()}"
        }
    
    return response


# ==================== AGENTIC SELECTOR ENDPOINTS ====================

@app.post(
    "/agentic-selector",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Agentic Selector"],
    summary="Generate vehicle recommendation",
    description="Generate AI-powered vehicle recommendation based on user preferences and available deals. Runs asynchronously in the background.",
    responses={
        202: {
            "description": "Recommendation generation started"
        },
        404: {
            "description": "User not found"
        }
    }
)
def create_agentic_selector(
    selector_data: schemas.AgenticSelectorCreate,
    db: Session = Depends(get_db)
):
    """
    Generate vehicle recommendation using AI sellup agent.
    
    - **UserId**: ID of the user (required)
    - **deals**: List of available vehicle deals (required)
    
    The recommendation will be generated asynchronously and saved to the database.
    """
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == selector_data.UserId).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {selector_data.UserId} not found"
        )
    
    # Trigger Celery task
    task = generate_vehicle_recommendation_task.delay(selector_data.UserId, selector_data.deals)
    
    return {
        "message": "Vehicle recommendation generation started",
        "user_id": selector_data.UserId,
        "task_id": task.id,
        "status": "processing"
    }


@app.get(
    "/agentic-selector",
    response_model=List[schemas.AgenticSelectorResponse],
    tags=["Agentic Selector"],
    summary="Get all agentic selector records",
    description="Retrieve all agentic selector records with optional filtering.",
    responses={
        200: {
            "description": "List of agentic selector records retrieved successfully"
        }
    }
)
def get_agentic_selectors(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    vehicle_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all agentic selector records with optional filtering.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **user_id**: Filter by user ID (optional)
    - **vehicle_id**: Filter by vehicle ID (optional)
    """
    if limit > 1000:
        limit = 1000
    
    query = db.query(models.AgenticSelector)
    
    if user_id:
        query = query.filter(models.AgenticSelector.user_id == user_id)
    if vehicle_id:
        query = query.filter(models.AgenticSelector.vehicle_id == vehicle_id)
    
    selectors = query.order_by(models.AgenticSelector.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        schemas.AgenticSelectorResponse(
            id=selector.id,
            VEHICLE_ID=selector.vehicle_id,
            FEATURES_BASED_ON_PREFERENCES=selector.features_list,
            REASON=selector.reason,
            PERSUASIVE_MESSAGES_POINTS=selector.persuasive_messages_list,
            UserId=selector.user_id,
            created_at=selector.created_at,
            updated_at=selector.updated_at
        )
        for selector in selectors
    ]


@app.get(
    "/agentic-selector/{selector_id}",
    response_model=schemas.AgenticSelectorResponse,
    tags=["Agentic Selector"],
    summary="Get agentic selector by ID",
    description="Retrieve a specific agentic selector record by its ID.",
    responses={
        200: {
            "description": "Agentic selector record found and returned successfully"
        },
        404: {
            "description": "Agentic selector record not found"
        }
    }
)
def get_agentic_selector(selector_id: int, db: Session = Depends(get_db)):
    """
    Get a specific agentic selector record by ID.
    
    - **selector_id**: The unique identifier of the agentic selector record
    """
    selector = db.query(models.AgenticSelector).filter(models.AgenticSelector.id == selector_id).first()
    if not selector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agentic selector record not found"
        )
    
    return schemas.AgenticSelectorResponse(
        id=selector.id,
        VEHICLE_ID=selector.vehicle_id,
        FEATURES_BASED_ON_PREFERENCES=selector.features_list,
        REASON=selector.reason,
        PERSUASIVE_MESSAGES_POINTS=selector.persuasive_messages_list,
        UserId=selector.user_id,
        created_at=selector.created_at,
        updated_at=selector.updated_at
    )


@app.get(
    "/agentic-selector/user/{user_id}/latest",
    response_model=schemas.AgenticSelectorResponse,
    tags=["Agentic Selector"],
    summary="Get latest agentic selector for user",
    description="Retrieve the most recent agentic selector record for a specific user.",
    responses={
        200: {
            "description": "Latest agentic selector record found"
        },
        404: {
            "description": "No agentic selector record found for user"
        }
    }
)
def get_latest_agentic_selector(user_id: int, db: Session = Depends(get_db)):
    """
    Get the latest agentic selector record for a user.
    
    - **user_id**: The user ID
    """
    selector = db.query(models.AgenticSelector).filter(
        models.AgenticSelector.user_id == user_id
    ).order_by(models.AgenticSelector.created_at.desc()).first()
    
    if not selector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No agentic selector record found for user {user_id}"
        )
    
    return schemas.AgenticSelectorResponse(
        id=selector.id,
        VEHICLE_ID=selector.vehicle_id,
        FEATURES_BASED_ON_PREFERENCES=selector.features_list,
        REASON=selector.reason,
        PERSUASIVE_MESSAGES_POINTS=selector.persuasive_messages_list,
        UserId=selector.user_id,
        created_at=selector.created_at,
        updated_at=selector.updated_at
    )


# ==================== PROTECTION PLAN TRACKING ENDPOINTS ====================

@app.post(
    "/track-protection-plan",
    response_model=schemas.TrackProtectionPlanResponse,
    status_code=status.HTTP_200_OK,
    tags=["Protection Plan Tracking"],
    summary="Create or update protection plan tracking",
    description="Create a new tracking record or update existing one if protectionPackageId and UserId combination already exists.",
    responses={
        200: {
            "description": "Tracking record created or updated successfully"
        },
        404: {
            "description": "User not found"
        }
    }
)
def track_protection_plan(
    tracking_data: schemas.TrackProtectionPlanCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update protection plan tracking data.
    
    If a record with the same protectionPackageId and UserId exists, it will be updated.
    Otherwise, a new record will be created.
    
    - **protectionPackageId**: Protection package ID (required)
    - **clickedIncludes**: Number of times includes was clicked (default: 0)
    - **clickedUnIncludes**: Number of times un-includes was clicked (default: 0)
    - **clickedPriceDistribution**: Number of times price distribution was clicked (default: 0)
    - **clickedDescription**: Number of times description was clicked (default: 0)
    - **timeSpendSelected**: Time spent on selected option in milliseconds (default: 0)
    - **Unselected**: Number of times unselected (default: 0)
    - **Selected**: Number of times selected (default: 0)
    - **BookingId**: Booking ID (optional)
    - **UserId**: User ID (required)
    """
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == tracking_data.UserId).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {tracking_data.UserId} not found"
        )
    
    # Check if record already exists
    existing_tracking = db.query(models.TrackProtectionPlan).filter(
        models.TrackProtectionPlan.protection_package_id == tracking_data.protectionPackageId,
        models.TrackProtectionPlan.user_id == tracking_data.UserId
    ).first()
    
    if existing_tracking:
        # Update existing record
        existing_tracking.clicked_includes = tracking_data.clickedIncludes
        existing_tracking.clicked_un_includes = tracking_data.clickedUnIncludes
        existing_tracking.clicked_price_distribution = tracking_data.clickedPriceDistribution
        existing_tracking.clicked_description = tracking_data.clickedDescription
        existing_tracking.time_spend_selected = tracking_data.timeSpendSelected
        existing_tracking.unselected = tracking_data.Unselected
        existing_tracking.selected = tracking_data.Selected
        existing_tracking.booking_id = tracking_data.BookingId
        existing_tracking.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_tracking)
        
        return schemas.TrackProtectionPlanResponse(
            id=existing_tracking.id,
            protectionPackageId=existing_tracking.protection_package_id,
            clickedIncludes=existing_tracking.clicked_includes,
            clickedUnIncludes=existing_tracking.clicked_un_includes,
            clickedPriceDistribution=existing_tracking.clicked_price_distribution,
            clickedDescription=existing_tracking.clicked_description,
            timeSpendSelected=existing_tracking.time_spend_selected,
            Unselected=existing_tracking.unselected,
            Selected=existing_tracking.selected,
            UserId=existing_tracking.user_id,
            BookingId=existing_tracking.booking_id,
            created_at=existing_tracking.created_at,
            updated_at=existing_tracking.updated_at
        )
    else:
        # Create new record
        new_tracking = models.TrackProtectionPlan(
            protection_package_id=tracking_data.protectionPackageId,
            clicked_includes=tracking_data.clickedIncludes,
            clicked_un_includes=tracking_data.clickedUnIncludes,
            clicked_price_distribution=tracking_data.clickedPriceDistribution,
            clicked_description=tracking_data.clickedDescription,
            time_spend_selected=tracking_data.timeSpendSelected,
            unselected=tracking_data.Unselected,
            selected=tracking_data.Selected,
            user_id=tracking_data.UserId,
            booking_id=tracking_data.BookingId
        )
        
        db.add(new_tracking)
        db.commit()
        db.refresh(new_tracking)
        
        return schemas.TrackProtectionPlanResponse(
            id=new_tracking.id,
            protectionPackageId=new_tracking.protection_package_id,
            clickedIncludes=new_tracking.clicked_includes,
            clickedUnIncludes=new_tracking.clicked_un_includes,
            clickedPriceDistribution=new_tracking.clicked_price_distribution,
            clickedDescription=new_tracking.clicked_description,
            timeSpendSelected=new_tracking.time_spend_selected,
            Unselected=new_tracking.unselected,
            Selected=new_tracking.selected,
            UserId=new_tracking.user_id,
            BookingId=new_tracking.booking_id,
            created_at=new_tracking.created_at,
            updated_at=new_tracking.updated_at
        )


@app.get(
    "/track-protection-plan",
    response_model=List[schemas.TrackProtectionPlanResponse],
    tags=["Protection Plan Tracking"],
    summary="Get all protection plan tracking records",
    description="Retrieve all protection plan tracking records with optional filtering.",
    responses={
        200: {
            "description": "List of tracking records retrieved successfully"
        }
    }
)
def get_track_protection_plans(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    protection_package_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all protection plan tracking records with optional filtering.
    
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **user_id**: Filter by user ID (optional)
    - **protection_package_id**: Filter by protection package ID (optional)
    - **booking_id**: Filter by booking ID (optional)
    """
    if limit > 1000:
        limit = 1000
    
    query = db.query(models.TrackProtectionPlan)
    
    if user_id:
        query = query.filter(models.TrackProtectionPlan.user_id == user_id)
    if protection_package_id:
        query = query.filter(models.TrackProtectionPlan.protection_package_id == protection_package_id)
    if booking_id:
        query = query.filter(models.TrackProtectionPlan.booking_id == booking_id)
    
    tracking_records = query.offset(skip).limit(limit).all()
    
    return [
        schemas.TrackProtectionPlanResponse(
            id=record.id,
            protectionPackageId=record.protection_package_id,
            clickedIncludes=record.clicked_includes,
            clickedUnIncludes=record.clicked_un_includes,
            clickedPriceDistribution=record.clicked_price_distribution,
            clickedDescription=record.clicked_description,
            timeSpendSelected=record.time_spend_selected,
            Unselected=record.unselected,
            Selected=record.selected,
            UserId=record.user_id,
            BookingId=record.booking_id,
            created_at=record.created_at,
            updated_at=record.updated_at
        )
        for record in tracking_records
    ]


@app.get(
    "/track-protection-plan/{tracking_id}",
    response_model=schemas.TrackProtectionPlanResponse,
    tags=["Protection Plan Tracking"],
    summary="Get protection plan tracking by ID",
    description="Retrieve a specific protection plan tracking record by its ID.",
    responses={
        200: {
            "description": "Tracking record found and returned successfully"
        },
        404: {
            "description": "Tracking record not found"
        }
    }
)
def get_track_protection_plan(tracking_id: int, db: Session = Depends(get_db)):
    """
    Get a specific protection plan tracking record by ID.
    
    - **tracking_id**: The unique identifier of the tracking record
    """
    tracking = db.query(models.TrackProtectionPlan).filter(models.TrackProtectionPlan.id == tracking_id).first()
    if not tracking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking record not found"
        )
    
    return schemas.TrackProtectionPlanResponse(
        id=tracking.id,
        protectionPackageId=tracking.protection_package_id,
        clickedIncludes=tracking.clicked_includes,
        clickedUnIncludes=tracking.clicked_un_includes,
        clickedPriceDistribution=tracking.clicked_price_distribution,
        clickedDescription=tracking.clicked_description,
        timeSpendSelected=tracking.time_spend_selected,
        Unselected=tracking.unselected,
        Selected=tracking.selected,
        UserId=tracking.user_id,
        BookingId=tracking.booking_id,
        created_at=tracking.created_at,
        updated_at=tracking.updated_at
    )


def compute_best_package(packages):
    """
    Compute the best protection package based on engagement, conversion rate, and consistency.
    
    Args:
        packages: List of package dictionaries with tracking data
    
    Returns:
        List of tuples (protectionPackageId, final_score) sorted by score descending
    """
    results = []
    
    for pkg in packages:
        engagement = (
            pkg["clickedIncludes"] * 1.5 +
            pkg["clickedUnIncludes"] * 1.0 +
            pkg["clickedPriceDistribution"] * 2.0 +
            pkg["clickedDescription"] * 1.2 +
            pkg["timeSpendSelected"] / 10000
        )
        
        conversion_rate = pkg["Selected"] / (pkg["Selected"] + pkg["Unselected"] + 1)
        
        consistency = 1 - abs(pkg["Selected"] - pkg["Unselected"]) / \
                      (pkg["Selected"] + pkg["Unselected"] + 1)
        
        final_score = (0.5 * engagement) + \
                      (0.3 * conversion_rate) + \
                      (0.2 * consistency)
        
        results.append({
            "protectionPackageId": pkg["protectionPackageId"],
            "final_score": final_score,
            "engagement": engagement,
            "conversion_rate": conversion_rate,
            "consistency": consistency,
            "package_data": pkg
        })
    
    best = sorted(results, key=lambda x: x["final_score"], reverse=True)
    return best


@app.get(
    "/protection-package/best/{user_id}",
    response_model=schemas.BestProtectionPackageResponse,
    tags=["Protection Plan Tracking"],
    summary="Get best protection package for user",
    description="Compute and return the best protection package for a user based on engagement, conversion rate, and consistency metrics.",
    responses={
        200: {
            "description": "Best protection package found"
        },
        404: {
            "description": "No protection packages found for user"
        }
    }
)
def get_best_protection_package(user_id: int, db: Session = Depends(get_db)):
    """
    Get the best protection package for a user.
    
    The algorithm computes a score based on:
    - Engagement (50%): clicks on includes, un-includes, price distribution, description, and time spent
    - Conversion Rate (30%): ratio of selected vs unselected
    - Consistency (20%): how consistent the selection pattern is
    
    - **user_id**: The user ID to get the best package for
    """
    # Get all packages for the user
    packages = db.query(models.TrackProtectionPlan).filter(
        models.TrackProtectionPlan.user_id == user_id
    ).all()
    
    if not packages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No protection packages found for user {user_id}"
        )
    
    # Convert to dictionary format for algorithm
    packages_data = []
    for pkg in packages:
        packages_data.append({
            "protectionPackageId": pkg.protection_package_id,
            "clickedIncludes": pkg.clicked_includes,
            "clickedUnIncludes": pkg.clicked_un_includes,
            "clickedPriceDistribution": pkg.clicked_price_distribution,
            "clickedDescription": pkg.clicked_description,
            "timeSpendSelected": pkg.time_spend_selected,
            "Selected": pkg.selected,
            "Unselected": pkg.unselected
        })
    
    # Compute best package
    best_packages = compute_best_package(packages_data)
    
    if not best_packages:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No protection packages found for user {user_id}"
        )
    
    # Get the best one (first in sorted list)
    best = best_packages[0]
    
    return schemas.BestProtectionPackageResponse(
        protectionPackageId=best["protectionPackageId"],
        score=best["final_score"],
        engagement=best["engagement"],
        conversion_rate=best["conversion_rate"],
        consistency=best["consistency"],
        package_data=best["package_data"]
    )


# ==================== QUESTION ANSWER ENDPOINTS ====================

@app.put(
    "/questions/{question_id}/answer",
    response_model=schemas.QuestionResponse,
    tags=["Questions"],
    summary="Update answer to a question",
    description="Update the answer for a specific question.",
    responses={
        200: {
            "description": "Answer updated successfully"
        },
        404: {
            "description": "Question not found"
        }
    }
)
def update_question_answer(
    question_id: int,
    answer: Optional[str] = None,
    answer_score: Optional[int] = None,
    importance: Optional[int] = None,
    frustrated: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Update the answer for a question.
    
    - **question_id**: ID of the question
    - **answer**: The answer to the question (optional)
    - **answer_score**: Score for the answer (optional)
    - **importance**: Importance level 1-5 (optional)
    - **frustrated**: Boolean indicating frustration level (optional)
    """
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Update only provided fields
    if answer is not None:
        question.answer = answer
    if answer_score is not None:
        question.answer_score = answer_score
    if importance is not None:
        if importance < 1 or importance > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Importance must be between 1 and 5"
            )
        question.importance = importance
    if frustrated is not None:
        question.frustrated = frustrated
    
    db.commit()
    db.refresh(question)
    
    # Convert to response format
    return schemas.QuestionResponse(
        id=question.id,
        question_type=question.question_type,
        category=question.category,
        question=question.question,
        options=question.options_list,
        answer=question.answer,
        answer_score=question.answer_score,
        importance=question.importance,
        frustrated=question.frustrated
    )


@app.delete(
    "/preferences/{preference_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Preferences"],
    summary="Delete a preference",
    description="Delete a preference by its ID.",
    responses={
        204: {
            "description": "Preference deleted successfully"
        },
        404: {
            "description": "Preference not found"
        }
    }
)
def delete_preference(preference_id: int, db: Session = Depends(get_db)):
    """
    Delete a preference by ID.
    
    - **preference_id**: The unique identifier of the preference to delete
    """
    db_preference = db.query(models.Preference).filter(models.Preference.id == preference_id).first()
    if not db_preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preference not found"
        )
    
    db.delete(db_preference)
    db.commit()
    
    return None

