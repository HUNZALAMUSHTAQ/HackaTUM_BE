from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    location = Column(String, nullable=False)
    driving_style = Column(String, nullable=True)  # e.g. sporty, relaxed, balanced
    fuel_preference = Column(String, nullable=True)  # petrol, hybrid, electric
    budget_sensitivity = Column(String, nullable=True)  # low, medium, high
    risk_tolerance = Column(String, nullable=True)  # low, medium, high
    
    # Relationship with preferences
    preferences = relationship("Preference", back_populates="user", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    preference_id = Column(Integer, ForeignKey("preferences.id"), nullable=True)  # Link to preference
    question_type = Column(String, nullable=False)  # e.g. boolean, text, scale, choice, multi_choice
    category = Column(String, nullable=False)  # e.g. driving_style, space, technology, fuel, risk, budget
    question = Column(Text, nullable=False)
    options = Column(Text, nullable=True)  # JSON string storing list of option strings
    answer = Column(Text, nullable=True)  # User's answer to the question
    answer_score = Column(Integer, nullable=True)  # Score for the answer (e.g. scale 1-5)
    importance = Column(Integer, default=1, nullable=False)  # Importance level (1-5)
    frustrated = Column(Boolean, default=False, nullable=False)  # User frustration indicator
    
    # Relationship with preference
    preference = relationship("Preference", back_populates="questions")
    
    def set_options(self, options_list):
        """Set options as a JSON string"""
        if options_list is not None:
            self.options = json.dumps(options_list)
        else:
            self.options = None
    
    @property
    def options_list(self):
        """Get options as a list (for Pydantic serialization)"""
        if self.options:
            try:
                return json.loads(self.options)
            except (json.JSONDecodeError, TypeError):
                return []
        return []


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, generating, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    questions = relationship("Question", back_populates="preference", cascade="all, delete-orphan")


class TrackProtectionPlan(Base):
    __tablename__ = "track_protection_plans"

    id = Column(Integer, primary_key=True, index=True)
    protection_package_id = Column(String, nullable=False, index=True)
    clicked_includes = Column(Integer, default=0, nullable=False)
    clicked_un_includes = Column(Integer, default=0, nullable=False)
    clicked_price_distribution = Column(Integer, default=0, nullable=False)
    clicked_description = Column(Integer, default=0, nullable=False)
    time_spend_selected = Column(Integer, default=0, nullable=False)
    unselected = Column(Integer, default=0, nullable=False)
    selected = Column(Integer, default=0, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with user
    user = relationship("User")


class AgenticSelector(Base):
    __tablename__ = "agentic_selectors"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String, nullable=False)
    features_based_on_preferences = Column(Text, nullable=False)  # JSON string storing list of strings
    reason = Column(Text, nullable=False)
    persuasive_messages_points = Column(Text, nullable=False)  # JSON string storing list of strings
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship with user
    user = relationship("User")
    
    def set_features(self, features_list):
        """Set features as a JSON string"""
        if features_list is not None:
            self.features_based_on_preferences = json.dumps(features_list)
        else:
            self.features_based_on_preferences = None
    
    def set_persuasive_messages(self, messages_list):
        """Set persuasive messages as a JSON string"""
        if messages_list is not None:
            self.persuasive_messages_points = json.dumps(messages_list)
        else:
            self.persuasive_messages_points = None
    
    @property
    def features_list(self):
        """Get features as a list"""
        if self.features_based_on_preferences:
            try:
                return json.loads(self.features_based_on_preferences)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @property
    def persuasive_messages_list(self):
        """Get persuasive messages as a list"""
        if self.persuasive_messages_points:
            try:
                return json.loads(self.persuasive_messages_points)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

