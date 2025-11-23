"""
Celery tasks for background processing
"""
from celery_app import celery_app
from question_generator_service import generate_questions_for_preference
from sellup_agent_service import generate_vehicle_recommendation, save_agentic_selector


@celery_app.task(bind=True, name="generate_preference_questions")
def generate_questions_task(self, preference_id: int, user_context: str = ""):
    """
    Celery task to generate questions for a preference.
    
    Args:
        preference_id: ID of the preference to generate questions for
        user_context: Optional context about the user
    
    Returns:
        List of created question IDs or None on error
    """
    try:
        result = generate_questions_for_preference(preference_id, user_context)
        return {
            "status": "success",
            "preference_id": preference_id,
            "questions_created": len(result) if result else 0,
            "question_ids": result
        }
    except Exception as exc:
        # Retry the task up to 3 times with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="generate_vehicle_recommendation")
def generate_vehicle_recommendation_task(self, user_id: int, deals: list):
    """
    Celery task to generate vehicle recommendation using AI sellup agent.
    
    Args:
        user_id: ID of the user
        deals: List of available vehicle deals
    
    Returns:
        Dictionary with recommendation data and saved record ID
    """
    try:
        # Generate recommendation
        recommendation = generate_vehicle_recommendation(user_id, deals)
        
        # Save to database
        agentic_selector = save_agentic_selector(
            user_id=user_id,
            vehicle_id=recommendation["VEHICLE_ID"],
            features=recommendation["FEATURES_BASED_ON_PREFERENCES"],
            reason=recommendation["REASON"],
            persuasive_messages=recommendation["PERSUASIVE_MESSAGES_POINTS"]
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "agentic_selector_id": agentic_selector.id,
            "vehicle_id": recommendation["VEHICLE_ID"],
            "features": recommendation["FEATURES_BASED_ON_PREFERENCES"],
            "reason": recommendation["REASON"],
            "persuasive_messages": recommendation["PERSUASIVE_MESSAGES_POINTS"]
        }
    except Exception as exc:
        # Retry the task up to 3 times with exponential backoff
        raise self.retry(exc=exc, countdown=60, max_retries=3)

