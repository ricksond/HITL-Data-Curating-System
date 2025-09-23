# HITL-Data-Curating-System
Requirements:
- Set your OpenAI API key: export OPENAI_API_KEY="sk-..."
- Install deps: pip install -r requirements.txt
- Put your hotel CSV as `hotels.csv` (or upload in the sidebar).
- Run: streamlit run app.py

Files:
- pipeline.py: LangGraph pipeline (normalize -> draft -> critique). Uses StateGraph.
- app.py: Streamlit UI to review and persist feedback to feedback.csv.
- feedback.csv will be created in project root (or path set by FEEDBACK_CSV env var).