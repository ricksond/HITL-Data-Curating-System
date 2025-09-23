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

def draft_node(state:HotelState,config=None,runtime=None):
    pass