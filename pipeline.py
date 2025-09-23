from dotenv import load_dotenv
import os 
from typing import TypedDict,Annotated,List
from datetime import datetime
import operator
import pandas as pd

load_dotenv()
API_KEY=os.getenv("OPENAI_API_KEY")
HOTELS_CSV=os.environ.get("HOTELS_CSV","hotels.csv")


from langgraph.graph import StateGraph,START,END

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage,SystemMessage


class HotelState(TypedDict):
    hotel_row:dict
    draft:str
    critique:List[str]

graph_builder=StateGraph(HotelState)

# initialize LLM
llm=ChatOpenAI(model="gpt-4o-mini",temperature=0.6)

# Node 1 : generalize Hotel row
def normalize_node(state:HotelState,config=None,runtime=None):
    row=dict(state.get("hotel_row")or {})
    normalized={}
    for k,v in row.items():
        normalized[k]=v.strip() if isinstance(v,str) else v
    keys=["hotel_id","hotel_name","city","country","star_rating","lat","lon",
          "cleanliness_base","comfort_base","facilities_base","location_base",
          "staff_base","value_for_money_base",
          "generated_summary","review_status","final_summary"]
    for k in keys:
        normalized.setdefault(k,None)
    return {"hotel_row":normalized}

graph_builder.add_node("normalize",normalize_node)
graph_builder.add_edge(START,"normalize")

# generating draft node 2
def draft_node(state:HotelState,config=None,runtime=None):
    hotel=state["hotel_row"]
    style_guide=(
        "You are a concice summarizer, produce a single paragraph(60-100 words)"
        "that mentioned location cues, star rating, two to four salient review strengths"
        "from the row, an any distinctive feature present"
        "Do not Hallucinate. Prefer data-grounded concrete statements,avoid vague superlatives"
    )

    hotel_attr=[]
    if hotel.get("star_rating"):
        hotel_attr.append(f"Star Rating:{hotel['star rating']}")
    
    scores={
        "Cleanliness": hotel.get("cleanliness_base"),
        "Comfort": hotel.get("comfort_base"),
        "Facilities": hotel.get("facilities_base"),
        "Location": hotel.get("location_base"),
        "Staff": hotel.get("staff_base"),
        "Value/money": hotel.get("value_for_money_base")
    }

    top_scores=sorted(
        [(k,v) for k,v in scores.items() if v],
        key=lambda x: float(x[1]),
        reverse=True)[:4]
    if top_scores:
        score_str=", ".join([f"{k} ({v})" for k,v in top_scores])
        hotel_attr.append("Notable Strengths: "+score_str)
    
    hotel_attr_text="\n".join(hotel_attr)
    name=hotel.get("hotel_name") or hotel.get("hotel_id") or "This Property"
    location=", ".join(filter(None,[hotel.get("city"),hotel.get("country")]))

    system_prompt=SystemMessage(content=style_guide)
    user_prompt=HumanMessage(content=(
        f"Hotel Name : {hotel}\n"
        f"Location L {location}\n"
        f"{hotel_attr_text}]\n\n"
        "Write a single paragraph(60-100 words)."
    ))
    res=llm([system_prompt,user_prompt])
    draft=res.content.strip()
    return {"draft":draft}

graph_builder.add_node("draft",draft_node)
graph_builder.add_edge("normalize","draft")

# Node 3 : Critique
def critique_node(state:HotelState,config=None,runtime=None):
    pass