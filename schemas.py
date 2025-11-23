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


class AgenticSelectorCreate(BaseModel):
    UserId: int = Field(..., description="User ID", example=1)
    deals: List[dict] = Field(..., description="List of available vehicle deals")

    class Config:
        json_schema_extra = {
            "example": {
                "UserId": 1,
                "deals": [
                    {
                        "vehicle": {
                            "id": "bb728740-95ac-7a86-2025-087de2dd7a66",
                            "brand": "FORD",
                            "model": "MUSTANG",
                            "modelAnnex": "2.3 ECOBOOST PREMIUM CONVERTIBLE RWD",
                            "acrissCode": "FTAR",
                            "images": ["https://vehicle-pictures-prod.orange.sixt.com/5144354/ffffff/18_1.png"],
                            "bagsCount": 0,
                            "passengersCount": 4,
                            "groupType": "CONVERTIBLE",
                            "tyreType": "ALL-YEAR_TYRES",
                            "transmissionType": "Automatic",
                            "fuelType": "",
                            "isNewCar": False,
                            "isRecommended": True,
                            "isMoreLuxury": False,
                            "isExcitingDiscount": False
                        },
                        "pricing": {
                            "displayPrice": {
                                "currency": "USD",
                                "amount": 46.75,
                                "prefix": "+",
                                "suffix": "/day"
                            },
                            "totalPrice": {
                                "currency": "USD",
                                "amount": 93.5,
                                "prefix": "",
                                "suffix": "in total"
                            }
                        }
                    }
                ]
            }
        }


class AgenticSelectorResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the agentic selector")
    VEHICLE_ID: str = Field(..., description="Recommended vehicle ID", alias="vehicle_id")
    FEATURES_BASED_ON_PREFERENCES: List[str] = Field(..., description="Features based on user preferences")
    REASON: str = Field(..., description="Reason for recommendation")
    PERSUASIVE_MESSAGES_POINTS: List[str] = Field(..., description="Persuasive message points")
    UserId: int = Field(..., description="User ID", alias="user_id")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        populate_by_name = True


class TrackProtectionPlanCreate(BaseModel):
    protectionPackageId: str = Field(..., description="Protection package ID", example="1")
    clickedIncludes: int = Field(0, description="Number of times includes was clicked", example=0, ge=0)
    clickedUnIncludes: int = Field(0, description="Number of times un-includes was clicked", example=0, ge=0)
    clickedPriceDistribution: int = Field(0, description="Number of times price distribution was clicked", example=0, ge=0)
    clickedDescription: int = Field(0, description="Number of times description was clicked", example=0, ge=0)
    timeSpendSelected: int = Field(0, description="Time spent on selected option in milliseconds", example=571007, ge=0)
    Unselected: int = Field(0, description="Number of times unselected", example=2, ge=0)
    Selected: int = Field(0, description="Number of times selected", example=2, ge=0)
    BookingId: Optional[str] = Field(None, description="Booking ID", example="booking123")
    UserId: int = Field(..., description="User ID", example=1)

    class Config:
        json_schema_extra = {
            "example": {
                "protectionPackageId": "1",
                "clickedIncludes": 0,
                "clickedUnIncludes": 0,
                "clickedPriceDistribution": 0,
                "clickedDescription": 0,
                "timeSpendSelected": 571007,
                "Unselected": 2,
                "Selected": 2,
                "BookingId": "booking123",
                "UserId": 1
            }
        }


class BestProtectionPackageResponse(BaseModel):
    protectionPackageId: str = Field(..., description="Best protection package ID")
    score: float = Field(..., description="Final computed score")
    engagement: float = Field(..., description="Engagement score")
    conversion_rate: float = Field(..., description="Conversion rate")
    consistency: float = Field(..., description="Consistency score")
    package_data: dict = Field(..., description="Full package data")

    class Config:
        json_schema_extra = {
            "example": {
                "protectionPackageId": "1",
                "score": 0.85,
                "engagement": 0.75,
                "conversion_rate": 0.6,
                "consistency": 0.8,
                "package_data": {
                    "clickedIncludes": 5,
                    "clickedUnIncludes": 2,
                    "clickedPriceDistribution": 3,
                    "clickedDescription": 4,
                    "timeSpendSelected": 571007,
                    "Selected": 10,
                    "Unselected": 5
                }
            }
        }


class TrackProtectionPlanResponse(BaseModel):
    id: int = Field(..., description="Unique identifier for the tracking record")
    protectionPackageId: str = Field(..., description="Protection package ID")
    clickedIncludes: int = Field(..., description="Number of times includes was clicked")
    clickedUnIncludes: int = Field(..., description="Number of times un-includes was clicked")
    clickedPriceDistribution: int = Field(..., description="Number of times price distribution was clicked")
    clickedDescription: int = Field(..., description="Number of times description was clicked")
    timeSpendSelected: int = Field(..., description="Time spent on selected option in milliseconds")
    Unselected: int = Field(..., description="Number of times unselected")
    Selected: int = Field(..., description="Number of times selected")
    UserId: int = Field(..., description="User ID")
    BookingId: Optional[str] = Field(None, description="Booking ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


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

