"""
Service for generating vehicle recommendations using AI sellup agent
"""
import json
import sys
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
import models
from database import SessionLocal


SELLUP_AGENT_PROMPT = """You are an intelligent car rental recommendation and ultra-upsell agent for a premium car rental platform.

Your job is to:
1. Understand the user's preferences
2. Analyze available vehicle deals
3. Recommend the BEST matching car
4. Persuasively upsell premium or higher value options
5. Make the user feel they are missing out without sounding pushy

You must balance logic + emotional persuasion.

================ USER PREFERENCES ================
Below are the answers selected by the user:

{{USER_PREFERENCES}}
Example format:
Question 1: ...
User Answer: ...

Question 2: ...
User Answer: ...

Question 3: ...
User Answer: ...

==================================================

================ AVAILABLE CARS DATA ================
{{CAR_LIST_JSON}}
=====================================================

### Recommendation Rules:
- First, match the user's preferences with car attributes:
  - passenger count
  - groupType (SUV, sedan, convertible, etc.)
  - fuelType
  - transmission
  - bagsCount
  - new car status
- Give more weight to:
  ✅ isRecommended = true  
  ✅ isExcitingDiscount = true  
  ✅ Higher passenger and luggage comfort  
  ✅ Electric / Hybrid / New vehicle (if user prefers eco or tech)  
- Consider pricing, discounts and value for money.

### Response Requirements:
Return response in this structured style:

1. **Top Recommendation**
   - Car name + short one-line value summary
   - Why it perfectly matches the user preference
   - 3 Bullet benefits related to their answers

2. **Ultra Upsell Section**
   Make the user feel like they would lose value if they don't upgrade:
   - Highlight missed experiences (comfort, tech, savings, power, safety, status)
   - Use concepts like:  
     "Most of our customers regret not upgrading…"  
     "For just X more per day, you unlock…"  
     "This is what you'll miss out on…"

3. **Comparison Tease**
   Briefly compare with 1 cheaper option and show what the user sacrifices.

4. **Emotional Closing CTA**
   Example:
   "Don't settle for average when your trip deserves premium comfort. 
    Upgrade now and thank yourself later."

### Tone Instructions:
- Friendly, premium, slightly persuasive, not aggressive
- Language should feel natural like a car concierge
- Not robotic, not overly salesy
- Make user feel smart for choosing better

### Output Style:
Keep it short, persuasive, structured, and skimmable.
Avoid long paragraphs. Use bullets.
Highlight prices, features, and experience emotionally.


Return the 
VEHICLE_ID 
FEATURES_BASED_ON_PREFERENCES
REASON
PERSUASIVE_MESSAGES_POINTS To the USER"""


def generate_vehicle_recommendation(user_id: int, deals: list):
    """
    Generate vehicle recommendation using AI sellup agent.
    
    Args:
        user_id: ID of the user
        deals: List of available vehicle deals
    
    Returns:
        Dictionary with VEHICLE_ID, FEATURES_BASED_ON_PREFERENCES, REASON, PERSUASIVE_MESSAGES_POINTS
    """
    db = SessionLocal()
    try:
        # Get user and their preferences
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        # Get user's latest preference with questions
        preference = db.query(models.Preference).filter(
            models.Preference.user_id == user_id
        ).order_by(models.Preference.created_at.desc()).first()
        
        # Format user preferences as text
        user_preferences_text = ""
        if preference and preference.questions:
            for idx, question in enumerate(preference.questions, 1):
                user_preferences_text += f"Question {idx}: {question.question}\n"
                if question.answer:
                    user_preferences_text += f"User Answer: {question.answer}\n"
                else:
                    user_preferences_text += "User Answer: Not answered\n"
                user_preferences_text += "\n"
        else:
            user_preferences_text = "No preferences available yet."
        
        # Format deals as JSON
        deals_json = json.dumps(deals, indent=2)
        
        # Build the prompt
        user_input = f"""USER PREFERENCES:
{user_preferences_text}

AVAILABLE CARS DATA:
{deals_json}

Please analyze the user preferences and available cars, then recommend the best vehicle match."""
        
        # Initialize Gemini client
        client = genai.Client(
            api_key="API_KEY"
        )
        
        model = "gemini-2.0-flash"
        
        # Replace placeholders in system instruction
        system_instruction_text = SELLUP_AGENT_PROMPT.replace(
            "{{USER_PREFERENCES}}", user_preferences_text
        ).replace(
            "{{CAR_LIST_JSON}}", deals_json
        )
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_input),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["VEHICLE_ID", "FEATURES_BASED_ON_PREFERENCES", "REASON", "PERSUASIVE_MESSAGES_POINTS"],
                properties={
                    "VEHICLE_ID": genai.types.Schema(
                        type=genai.types.Type.STRING,
                    ),
                    "FEATURES_BASED_ON_PREFERENCES": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                    ),
                    "REASON": genai.types.Schema(
                        type=genai.types.Type.STRING,
                    ),
                    "PERSUASIVE_MESSAGES_POINTS": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(
                            type=genai.types.Type.STRING,
                        ),
                    ),
                },
            ),
            system_instruction=[
                types.Part.from_text(text=system_instruction_text),
            ],
        )
        
        # Generate recommendation
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text
        
        # Parse JSON response
        response_data = json.loads(response_text)
        
        return {
            "VEHICLE_ID": response_data.get("VEHICLE_ID", ""),
            "FEATURES_BASED_ON_PREFERENCES": response_data.get("FEATURES_BASED_ON_PREFERENCES", []),
            "REASON": response_data.get("REASON", ""),
            "PERSUASIVE_MESSAGES_POINTS": response_data.get("PERSUASIVE_MESSAGES_POINTS", [])
        }
        
    except Exception as e:
        print(f"Error generating vehicle recommendation for user {user_id}: {str(e)}", file=sys.stderr)
        raise
    finally:
        db.close()


def save_agentic_selector(user_id: int, vehicle_id: str, features: list, reason: str, persuasive_messages: list):
    """
    Save agentic selector result to database.
    
    Args:
        user_id: ID of the user
        vehicle_id: Recommended vehicle ID
        features: List of features based on preferences
        reason: Reason for recommendation
        persuasive_messages: List of persuasive message points
    
    Returns:
        AgenticSelector model instance
    """
    db = SessionLocal()
    try:
        agentic_selector = models.AgenticSelector(
            user_id=user_id,
            vehicle_id=vehicle_id,
            reason=reason
        )
        
        agentic_selector.set_features(features)
        agentic_selector.set_persuasive_messages(persuasive_messages)
        
        db.add(agentic_selector)
        db.commit()
        db.refresh(agentic_selector)
        
        return agentic_selector
    except Exception as e:
        db.rollback()
        print(f"Error saving agentic selector: {str(e)}", file=sys.stderr)
        raise
    finally:
        db.close()

