from dotenv import load_dotenv
import os 
from typing import TypedDict,Annotated,List
import pandas as pd

load_dotenv()
API_KEY=os.getenv("OPENAI_API_KEY")
HOTELS_CSV=os.environ.get("HOTELS_CSV","hotels.csv")


from langgraph.graph import StateGraph,START,END

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage,SystemMessage


class HotelState(TypedDict):
    hotel_row:dict
    draft:Annotated[str,"replace"]
    critique:Annotated[List[str],"replace"]

graph_builder=StateGraph(HotelState)

# initialize LLM
llm=ChatOpenAI(model="gpt-4o-mini",temperature=0.6)

# Node 1 : generalize Hotel row
def normalize_node(state:HotelState,config=None,runtime=None):
    row=dict(state.get("hotel_row")or {})
    normalized={}
    for k,v in row.items():
        if isinstance(v,str):
            v=v.strip()
            if v.lower() in ("nan",""):
                v=None
        if pd.isna(v) or v in ("","nan","NaN"):
            v=None
        normalized[k]=v
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
        "You are a concise summarizer. Produce a single paragraph(60-100 words)"
        "that mentions location cues, star rating, two to four salient review strengths"
        "from the row, and any distinctive feature present. "
        "Do not Hallucinate. Prefer data-grounded concrete statements. Avoid vague superlatives. "
    )

    hotel_attr=[]
    if hotel.get("star_rating"):
        hotel_attr.append(f"Star Rating:{hotel['star_rating']}")
    
    scores={
        "Cleanliness": hotel.get("cleanliness_base"),
        "Comfort": hotel.get("comfort_base"),
        "Facilities": hotel.get("facilities_base"),
        "Location": hotel.get("location_base"),
        "Staff": hotel.get("staff_base"),
        "Value/money": hotel.get("value_for_money_base")
    }

    valid_scores=[(k,v) for k,v in scores.items() if v not in(None,"","NaN")]

    try:
        top_scores=sorted(
        [(k,float(v)) for k,v in valid_scores.items()],
        key=lambda x: x[1],
        reverse=True)[:4]
    except Exception:
        top_scores=[]
    
    if top_scores:
        score_str=", ".join([f"{k} ({v})" for k,v in top_scores])
        hotel_attr.append("Notable Strengths: "+score_str)
    
    hotel_attr_text="\n".join(hotel_attr)
    name=hotel.get("hotel_name") or hotel.get("hotel_id") or "This Property"
    location=", ".join(filter(None,[hotel.get("city"),hotel.get("country")]))

    system_prompt=SystemMessage(content=style_guide)
    user_prompt=HumanMessage(content=(
        f"Hotel Name : {name}\n"
        f"Location L {location}\n"
        f"{hotel_attr_text}]\n\n"
        f"Notable strengths: {', '.join([f'{k}({v})' for k,v in top_scores]) if top_scores else 'None Listed'}\n\n"
        "Write a single paragraph(60-100 words)."
    ))
    res=llm([system_prompt,user_prompt])
    draft=(res.content or "").strip()
    if not draft:
        draft=f"{name} is located in {location}.Further details were not available."
    return {"draft":draft}

graph_builder.add_node("generate_draft",draft_node)
graph_builder.add_edge("normalize","generate_draft")

# Node 3 : Critique
def critique_node(state:HotelState,config=None,runtime=None):
    draft=state.get("draft","")
    hotel=state.get("hotel_row",{})
    missing=[]
    if hotel.get('city') or hotel.get('country'):
        if not (hotel.get('city') in draft) or not(hotel.get('country') and hotel['country'] in draft):
            missing.append("City or Country not mentioned")
    scores={
         "cleanliness": hotel.get('cleanliness_base'),
         "comfort":hotel.get('comfort_base'),
         "facilities":hotel.get('facilities_base'),
         "location":hotel.get("location_base"),
         "staff":hotel.get('staff_base'),
         "Value for money": hotel.get('value_for_money_base')
     }
    
    mentioned=sum(1 for k,v in scores.items() if v and k in draft.lower())
    if mentioned<2:
        missing.append("Fewer than two review strengths mentioned")
    critique=missing if missing else ["All required elements are present"]
    return {"critique": critique}

graph_builder.add_node("run_critique",critique_node)
graph_builder.add_edge("generate_draft","run_critique")
graph_builder.add_edge("run_critique",END)

compiled_graph=graph_builder.compile()

# Create Pipeline
def generate_draft_and_critique(hotel_row:dict):
    initial_state={"hotel_row":hotel_row,"draft":"","critique":[]}
    out=compiled_graph.invoke(initial_state)
    return {
        "draft":out.get("draft",""),
        "critique":out.get("critique",[]),
        "hotel_row":out.get("hotel_row",{})
    }

def persist_review(hotel_id:str,action:str,edited_summary:str):
    df=pd.read_csv(HOTELS_CSV)
    df.loc[df['hotel_id'].astype(str)==str(hotel_id),'review_status']=action
    df.loc[df['hotel_id'].astype(str)==str(hotel_id),'final_summary']=edited_summary
    df.to_csv(HOTELS_CSV,index=False)