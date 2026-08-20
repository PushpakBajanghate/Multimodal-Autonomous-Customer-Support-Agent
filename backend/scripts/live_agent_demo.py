"""
Live Real-Time Agent Demo & Verification Script for Multimodal Autonomous Customer Support Agent (Aura).
Demonstrates real-time interaction with Google Gemini 3.6 Flash NLU and StateGraph tool execution.
"""

import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.agent.intent import analyze_utterance
from app.agent.graph import agent_graph
from app.agent.responder import generate_agent_response

def run_demo():
    print("=" * 70)
    print("  AURA: MULTIMODAL AUTONOMOUS CUSTOMER SUPPORT AGENT - LIVE DEMO")
    print("=" * 70)
    print(f"Provider: {settings.LLM_PROVIDER}")
    print(f"Gemini Model: {settings.GEMINI_MODEL}")
    print(f"API Key Present: {'Yes (Active)' if settings.GEMINI_API_KEY else 'No (Heuristic Fallback)'}")
    print("-" * 70)

    # 1. Initialize DB
    print("[1] Initializing and verifying persistent database...")
    init_db()
    db = SessionLocal()

    # 2. Test scenarios
    test_queries = [
        "Hello Aura, can you tell me what you can do for me?",
        "Where is my parcel? Can you check tracking for order #1?",
        "Mera order #2 ka status batao please",
        "I want to request a refund for order #2 because the item was broken.",
        "Please cancel my order #1 right now.",
        "Change my shipping address for order #1 to 742 Evergreen Terrace, Springfield.",
        "I forgot my password, please send a reset link to alice.smith@example.com",
        "I have a dispute that needs a manager, please connect me with a human agent."
    ]

    print(f"\n[2] Executing {len(test_queries)} live real-time conversations:")
    print("=" * 70)

    for idx, query in enumerate(test_queries, 1):
        print(f"\n>> USER [{idx}]: \"{query}\"")
        
        # Real-time intent analysis with Gemini
        analysis = analyze_utterance(query)
        print(f"   [NLU Brain]: Intent={analysis.intent.value} | Conf={analysis.confidence:.2f} | Entities={analysis.entities.model_dump(exclude_none=True)}")
        
        # Real-time domain response generation
        reply = generate_agent_response(
            db=db,
            message=query,
            conversation_id=1,
            customer_id=1
        )
        print(f"   [Aura Agent Reply]:")
        for line in reply.strip().split("\n"):
            print(f"     {line}")

    db.close()
    print("\n" + "=" * 70)
    print("  ALL REAL-TIME DEMO SCENARIOS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_demo()