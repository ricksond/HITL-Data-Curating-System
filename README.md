# HITL-Data-Curating-System
Requirements:
- Set your OpenAI API key: export OPENAI_API_KEY
- Install deps: pip install -r requirements.txt
- Put your hotel CSV as `hotels.csv` (or upload in the sidebar).
- Run: streamlit run app.py

Files:
- pipeline.py: LangGraph pipeline (normalize -> draft -> critique). Uses StateGraph.
- app.py: Streamlit UI to review and persist feedback to the same hotels.csv files
by creating three more seperate columns in code
