import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from pipeline import generate_draft_and_critique,persist_review


load_dotenv()

HOTELS_CSV=os.environ.get("HOTELS_CSV","hotels.csv")

st.set_page_config(page_title="HITL Curator",layout="wide")
st.title("Hotel Summary Validation")

# Load the Dataset
@st.cache_resource
def load_hotels():
    df=pd.read_csv(HOTELS_CSV)
    for col in ["generated_summary","review_status","final_summary"]:
        if col not in df.columns:
            df[col]=""
    return df

hotels_df=load_hotels()
# Navigation
st.sidebar.header("Navigation")
hotel_ids=hotels_df["hotel_id"].tolist()
selected_hotel_id=st.sidebar.selectbox("Choose a Hotel ID:",hotel_ids)

# Show Select Hotel
hotel_row=hotels_df[hotels_df['hotel_id']==selected_hotel_id].iloc[0].to_dict()

if not hotel_row['generated_summary']:
    result=generate_draft_and_critique(hotel_row)
    draft=result['draft']
    hotels_df.loc[hotels_df["hotel_id"]==selected_hotel_id,"generated_summary"]=draft
    hotels_df.to_csv(HOTELS_CSV,index=False)
else:
    draft=hotel_row["generated_summary"]


# More UI
col1,col2=st.columns([1,2])

with col1:
    st.subheader("Hotel Attributes")
    st.write(f"**Hotel Name:** {hotel_row.get('hotel_name')}")
    st.write(f"**Location:** {hotel_row.get('city')},{hotel_row.get('country')}")
    st.write(f"**Star Rating:** {hotel_row.get('star_rating')}")
    st.markdown('"Review Sub Scores"')
    st.write(f"**Cleanliness:** {hotel_row.get('cleanliness_base')}")
    st.write(f"**Comfort:** {hotel_row.get('comfort_base')}")
    st.write(f"**Facilities:** {hotel_row.get('facilities_base')}")
    st.write(f"**Location:** {hotel_row.get('location_base')}")
    st.write(f"**Staff:** {hotel_row.get('staff_base')}")
    st.write(f"**Value For Money:** {hotel_row.get('value_for_money_base')}")

with col2:
    st.subheader("Summary (Automated)")
    st.info(draft)
    edited=st.text_area("Edit the summary if needed: ",value=draft,height=150)

    colA,colB=st.columns(2)
    with colA:
        if st.button("Accept"):
            persist_review(hotel_row['hotel_id'],"accept",edited)
            st.success("Summary Accepted and Saved.")
    with colB:
        if st.button("Reject"):
            persist_review(hotel_row["hotel_id"],"reject",edited)
            st.error("Summary Rejected and saved.")