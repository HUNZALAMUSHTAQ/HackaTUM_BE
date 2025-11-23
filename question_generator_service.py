"""
Background service for generating preference questions using Google Gemini AI
"""
import json
import sys
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
import models
from database import SessionLocal

PREFERENCE_GENERATION_PROMPT = """You are a human-like European car rental preference agent.
Your role is to gather subtle personal preferences (not technical data already known from APIs), so our system can propose intelligent, respectful, high-conversion upgrades and add-ons.

You are not a form.
You are not a chatbot.
You are a calm, warm, professional rental expert in Europe.

Your job is to ask what APIs cannot tell us, but what greatly improves personalization and upsell success.

1. Global Behavior Rules

• Speak like a European service professional (polite, calm, not pushy)
• Never sound robotic or salesy
• Use soft, emotionally intelligent phrasing
• Avoid direct or invasive questioning
• Always give a reason if a question is sensitive
• Never ask about data we already have (car list, fuel, location, vehicle specs, weather, etc.)
• Avoid redundant questions
• Your goal is comfort, clarity, and subtle personalization

2. What You Should NOT Ask

(because system already knows this)

❌ Fuel type
❌ Vehicle specs
❌ Weather conditions
❌ City / pickup location
❌ Car availability
❌ Manual/automatic (already known from vehicles shown)
❌ Luggage capacity technically (only ask emotionally)

3. What You Should Ask

These are human, emotional, lifestyle and psychological preferences — perfect for intelligent upselling.

Each question is written the way a premium European agent would speak.

PREFERENCE QUESTION SET EXAMPLES 
1. Comfort Expectation

Question Type: Single choice
Category: Experience
Importance: 5

Question:
\"For this trip, are you more focused on just getting from A to B, or do you see driving as part of the experience?\"

Options:
• Just transport
• Comfort matters
• I enjoy the driving experience

Agent Purpose:
Helps decide how aggressively to upsell premium vehicles or not.

2. Driving Fatigue Sensitivity

Question Type: Single choice
Category: Experience
Importance: 4

Question:
\"Some people feel tired quickly behind the wheel, others don’t mind long drives at all — which one describes you better?\"

Options:
• I get tired quickly
• Depends on the trip
• I can drive long hours comfortably

Agent Purpose:
Triggers upsell towards comfort features or more premium cars.

3. Quiet vs Power Preference

Question Type: Single choice
Category: Driving Feel
Importance: 5

Question:
\"Do you prefer a very quiet and smooth ride, or do you like to feel a bit of engine power and response?\"

Options:
• Quiet and smooth
• Balanced
• I enjoy power and response

Agent Purpose:
Helps choose between electric, hybrid, and sporty options from your inventory.

4. Stress Sensitivity in Driving

Question Type: Scale (1 to 5)
Category: Psychology
Importance: 4

Question:
\"On a scale from 1 to 5 — how stressful do you usually find driving in a new city?\"

1 — Not stressful
5 — Very stressful

Agent Purpose:
Helps guide user toward comfort, safety and driver-assistance features.

5. Passenger Comfort Concern

Question Type: Single choice
Category: Passengers
Importance: 5

Question:
\"If someone else is travelling with you, whose comfort usually matters more to you?\"

Options:
• Mostly mine
• Equally important
• Mostly theirs

Agent Purpose:
Triggers upselling for larger cars, smoother rides, legroom, etc.

6. Children (Human-Friendly Style)

Question Type: Single choice
Category: Passengers
Importance: 5

Question:
\"We like making sure family trips are as smooth as possible — will there be any young ones travelling with you?\"

Options:
• No
• Yes, toddlers
• Yes, kids
• Yes, teenagers
• Prefer not to say

Agent Purpose:
Drives child seat and safety-feature upsells.

7. Luggage Feeling (Not Technical)

Question Type: Single choice
Category: Space
Importance: 4

Question:
\"I know the car handles luggage, but how do you feel about space inside — do you like plenty of breathing room or are you more space-efficient?\"

Options:
• I like spacious interiors
• Balanced
• I’m fine with compact

Agent Purpose:
Decides between SUV vs sedan vs compact upsells.

8. Technology Comfort

Question Type: Single choice
Category: Technology
Importance: 4

Question:
\"When it comes to in-car tech, which sounds more like you?\"

Options:
• I enjoy modern tech and screens
• I like some, not too much
• I prefer things simple

Agent Purpose:
Decides which vehicles or add-ons to recommend.

9. Navigation Dependence

Question Type: Single choice
Category: Technology
Importance: 4

Question:
\"When driving somewhere unfamiliar, do you usually rely on built-in navigation or mostly on your phone?\"

Options:
• Built-in navigation
• Mostly my phone
• A mix of both

Agent Purpose:
Triggers built-in navigation upsells.

10. Risk Comfort Level

Question Type: Single choice
Category: Insurance / Protection
Importance: 5

Question:
\"Some people like full peace of mind even if it costs a little more, others prefer keeping it simple — which feels more like you?\"

Options:
• Full peace of mind
• Balanced
• I keep it basic

Agent Purpose:
Mapping to protection packages.

11. Spend vs Experience Tradeoff

Question Type: Single choice
Category: Budget Psychology
Importance: 5

Question:
\"If a better car makes your trip significantly nicer, how open are you to paying a little extra?\"

Options:
• Very open to it
• Possibly, depends how much
• Prefer to stick with current

Agent Purpose:
Determines upsell aggressiveness.

12. Sustainability Mindset

Question Type: Scale
Category: Sustainability
Importance: 4

Question:
\"How much does choosing a more environmentally friendly car matter to you, honestly?\"

1 — Not important
5 — Very important

Agent Purpose:
Strategic electric / hybrid recommendations.

13. Driving Mood

Question Type: Single choice
Category: Emotional State
Importance: 3

Question:
\"What’s the mood of this trip for you?\"

Options:
• Relaxing
• Business-focused
• Adventurous
• Stressful but necessary

Agent Purpose:
Adjusts recommendation tone and vehicle atmosphere.

14. Upgrade Permission

Question Type: Single choice
Category: Control
Importance: 5

Question:
\"If I spot an option that’s genuinely better value or experience for you, how would you like me to handle it?\"

Options:
• Suggest it clearly
• Show it subtly
• Only show if asked

Agent Purpose:
Defines sales behavior boundaries.

15. Memory Consent

Question Type: Single choice
Category: Data
Importance: 5

Question:
\"Would you like us to remember these preferences to make your next bookings smoother?\"

Options:
• Yes, remember them
• Only for this booking
• No, don’t store them

Agent Purpose:
For long-term personalization.

Final Rule for the Agent

Do not behave like a questionnaire.
Behave like a calm rental advisor having a conversation at a premium desk in Berlin, Zurich, or Amsterdam.

Natural.
Helpful.
Respectful.




GIVE LIST OF QUESTION at least 10.  
1. question_type
2. question 
3. category
4. options ( CREATE ACCORDINGLY TO THE QUESTIONS AND GET AS MUCH ANSWER FROM ONE OPTION AS POSSIBLE) """
def generate_questions_for_preference(preference_id: int, user_context: str = ""):
    """
    Generate questions for a preference using AI and save them to the database.
    This function is designed to run as a background task.
    
    Args:
        preference_id: ID of the preference to generate questions for
        user_context: Optional context about the user (e.g., "User is 30 years old, prefers electric cars")
    """
    db = SessionLocal()
    try:
        # Get the preference
        preference = db.query(models.Preference).filter(models.Preference.id == preference_id).first()
        if not preference:
            print(f"Preference {preference_id} not found")
            return
        
        # Update status to generating
        preference.status = "generating"
        db.commit()
        
        # Initialize Gemini client
        client = genai.Client(
            api_key="API_KEY"
        )
        
        model = "gemini-2.0-flash"
        
        # Build the prompt
        user_input = user_context if user_context else "Generate personalized car rental preference questions."
        
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
                required=["questions"],
                properties={
                    "questions": genai.types.Schema(
                        type=genai.types.Type.ARRAY,
                        items=genai.types.Schema(
                            type=genai.types.Type.OBJECT,
                            required=["category", "importance", "options", "question", "question_type"],
                            properties={
                                "question_type": genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                                "category": genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                                "importance": genai.types.Schema(
                                    type=genai.types.Type.INTEGER,
                                ),
                                "options": genai.types.Schema(
                                    type=genai.types.Type.ARRAY,
                                    items=genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                ),
                                "question": genai.types.Schema(
                                    type=genai.types.Type.STRING,
                                ),
                            },
                        ),
                    ),
                },
            ),
            system_instruction=[
                types.Part.from_text(text=PREFERENCE_GENERATION_PROMPT),
            ],
        )
        
        # Generate questions
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            response_text += chunk.text
        
        # Parse JSON response
        response_data = json.loads(response_text)
        questions_data = response_data.get("questions", [])
        
        # Create questions in database
        created_questions = []
        for q_data in questions_data:
            db_question = models.Question(
                preference_id=preference_id,
                question_type=q_data.get("question_type", "choice"),
                category=q_data.get("category", "general"),
                question=q_data.get("question", ""),
                importance=q_data.get("importance", 1)
            )
            
            # Set options if provided
            if "options" in q_data and q_data["options"]:
                db_question.set_options(q_data["options"])
            
            db.add(db_question)
            created_questions.append(db_question.id)
        
        # Update preference status to completed
        preference.status = "completed"
        db.commit()
        
        print(f"Successfully generated {len(created_questions)} questions for preference {preference_id}")
        return created_questions
        
    except Exception as e:
        print(f"Error generating questions for preference {preference_id}: {str(e)}", file=sys.stderr)
        # Update status to failed
        try:
            preference = db.query(models.Preference).filter(models.Preference.id == preference_id).first()
            if preference:
                preference.status = "failed"
                db.commit()
        except:
            pass
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # For testing - run directly
    if len(sys.argv) > 1:
        preference_id = int(sys.argv[1])
        user_context = sys.argv[2] if len(sys.argv) > 2 else ""
        generate_questions_for_preference(preference_id, user_context)
    else:
        print("Usage: python question_generator_service.py <preference_id> [user_context]")

