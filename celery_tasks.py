"""
Celery tasks for background processing
"""
from celery_app import celery_app
from question_generator_service import generate_questions_for_preference


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

