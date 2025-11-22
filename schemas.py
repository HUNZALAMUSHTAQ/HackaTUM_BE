from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any
from datetime import datetime
import json


class QuestionCreate(BaseModel):
    question_type: str = Field(
        ..., 
        description="Type of question - e.g. boolean, text, scale, choice, multi_choice",
        example="choice"
    )
    category: str = Field(
        ..., 
        description="Category of the question - e.g. driving_style, space, technology, fuel, risk, budget",
        example="driving_style"
    )
    question: str = Field(
        ..., 
        description="The question text",
        example="What is your preferred driving style?"
    )
    options: Optional[List[str]] = Field(
        None,
        description="List of available options for choice/multi_choice question types",
        example=["sporty", "relaxed", "balanced"]
    )
    answer: Optional[str] = Field(
        None,
        description="Default or expected answer for the question",
        example="sporty"
    )
    answer_score: Optional[int] = Field(
        None,
        description="Default or expected score for the answer",
        example=4
    )
    importance: int = Field(
        1,
        description="Default importance level: 1 = low, 5 = critical",
        example=3,
        ge=1,
        le=5
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question_type": "choice",
                "category": "driving_style",
                "question": "What is your preferred driving style?",
                "options": ["sporty", "relaxed", "balanced"],
                "answer": "sporty",
                "answer_score": 4,
                "importance": 3
            }
        }


class QuestionResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the question")
    question_type: str = Field(..., description="Type of question")
    category: str = Field(..., description="Category of the question")
    question: str = Field(..., description="The question text")
    options: Optional[List[str]] = Field(None, description="List of available options")
    answer: Optional[str] = Field(None, description="User's answer to the question")
    answer_score: Optional[int] = Field(None, description="Score for the answer")
    importance: int = Field(..., description="Importance level (1-5)")
    frustrated: bool = Field(False, description="Whether the user is frustrated")

    @model_validator(mode='before')
    @classmethod
    def convert_options(cls, data: Any) -> Any:
        """Convert options from JSON string to list if needed"""
        if isinstance(data, dict):
            # If options is a string (JSON), parse it
            if 'options' in data and isinstance(data['options'], str):
                try:
                    data['options'] = json.loads(data['options'])
                except (json.JSONDecodeError, TypeError):
                    data['options'] = []
            # If options_list property exists (from model), use it
            elif 'options_list' in data:
                data['options'] = data.pop('options_list')
        return data

    class Config:
        from_attributes = True


class PreferenceCreate(BaseModel):
    user_id: int = Field(
        ..., 
        description="ID of the user",
        example=1
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1
            }
        }


class PreferenceResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the preference")
    user_id: int = Field(..., description="ID of the user who owns this preference")
    status: str = Field(..., description="Status of the preference: pending, generating, completed, failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    questions: List[QuestionResponse] = Field(
        default=[], 
        description="List of questions for this preference"
    )

    class Config:
        from_attributes = True


class PreferenceCreateResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the preference")
    user_id: int = Field(..., description="ID of the user who owns this preference")
    status: str = Field(..., description="Status of the preference")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    task_id: str = Field(..., description="Celery task ID for question generation")
    message: str = Field(..., description="Status message")


class UserCreate(BaseModel):
    name: str = Field(..., description="Full name of the user", example="John Doe")
    age: int = Field(..., description="Age of the user", example=30, ge=0)
    gender: str = Field(..., description="Gender of the user", example="Male")
    location: str = Field(..., description="Location of the user", example="Munich")
    driving_style: Optional[str] = Field(
        None, 
        description="Driving style preference - e.g. sporty, relaxed, balanced",
        example="sporty"
    )
    fuel_preference: Optional[str] = Field(
        None, 
        description="Fuel preference - petrol, hybrid, electric",
        example="electric"
    )
    budget_sensitivity: Optional[str] = Field(
        None, 
        description="Budget sensitivity level - low, medium, high",
        example="medium"
    )
    risk_tolerance: Optional[str] = Field(
        None, 
        description="Risk tolerance level - low, medium, high",
        example="high"
    )

    class Config:
        json_schema_extra = {
            "example": {
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
                        "question_id": 1,
                        "answer": "sporty",
                        "answer_score": 4,
                        "importance": 3,
                        "frustrated": False
                    }
                ]
            }
        }


class UserResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the user")
    name: str = Field(..., description="Full name of the user")
    age: int = Field(..., description="Age of the user")
    gender: str = Field(..., description="Gender of the user")
    location: str = Field(..., description="Location of the user")
    driving_style: Optional[str] = Field(None, description="Driving style preference")
    fuel_preference: Optional[str] = Field(None, description="Fuel preference")
    budget_sensitivity: Optional[str] = Field(None, description="Budget sensitivity level")
    risk_tolerance: Optional[str] = Field(None, description="Risk tolerance level")
    preferences: List[PreferenceResponse] = Field(
        default=[], 
        description="List of user preferences"
    )

    class Config:
        from_attributes = True

