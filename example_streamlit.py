import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt

# --- Sample Data Loading ---
@st.cache_data
def load_data():
    # Replace with real case-law retrieval / embeddings store
    df = pd.DataFrame({
        'CaseID': ['C1', 'C2', 'C3', 'C4', 'C5'],
        'Title': [
            'River Contamination Tribunal v. Fenoscadia',
            'Environmental Claims Panel',
            'Mining Dispute ICSID',
            'UNCITRAL Water Pollution Case',
            'Cardio-Health Impacts Arbitration'
        ],
        'Year': [2017, 2019, 2021, 2022, 2024],
        'Similarity': [0.78, 0.65, 0.82, 0.55, 0.90],
        'Outcome': ['Opposed', 'Supported', 'Opposed', 'Supported', 'Opposed'],
        'Latitude': [10.0, 20.5, -5.2, 47.3, 35.7],
        'Longitude': [45.0, 30.2, 60.1, 10.0, -120.5],
        'Excerpt': [
            'Tribunal found contamination evidence inconclusive...',
            'Panel ruled in favor of state claim on water damage...',
            'ICSID rejected counterclaim for lack of causal nexus...',
            'Award granted partial relief on water purification costs...',
            'Majority held insufficient proof of health impacts...'
        ]
    })
    return df

# --- Main App ---
st.set_page_config(page_title="Arbitration Strategy Dashboard", layout="wide")
st.title("🌐 Arbitration Strategy Dashboard")
st.markdown("Welcome to the Arbitration Strategy Dashboard! This app helps you explore similar cases, improve your strategy and understand the chances of sucess in arbitration cases.")


idea_ready = st.selectbox("Do you have a draft for a first idea?", ["No", "Yes"])
if idea_ready == "Yes":
    # Inline text area instead of st.chat_input
    user_prompt = st.text_area("My first strategy idea is:")
    if st.button("Send Strategy Idea"):
        # show the user’s message in the chat
        st.chat_message("user").write(user_prompt)
        # placeholder LLM call
        response = f"[AI Response to: '{user_prompt}']"
        st.chat_message("assistant").write(response)
else:
    if st.button("Create Strategy"):
        st.success("Strategy generation initiated.")
   

df = load_data()

# Sidebar Filters
st.sidebar.header("Filter similar cases")
min_year, max_year = st.sidebar.slider(
    "Case Year Range", int(df.Year.min()), int(df.Year.max()), (2017, 2024)
)
outcome_filter = st.sidebar.multiselect(
    "Outcome", options=df.Outcome.unique(), default=list(df.Outcome.unique())
)
similarity_threshold = st.sidebar.slider(
    "Min. Similarity", 0.0, 1.0, 0.6, 0.01
)

# Apply Filters
filtered = df[
    (df.Year.between(min_year, max_year)) &
    (df.Outcome.isin(outcome_filter)) &
    (df.Similarity >= similarity_threshold)
]

# Case-Law Table
st.markdown("---")
st.subheader("📚 Retrieved Precedents")
st.dataframe(filtered[['CaseID','Title','Year','Similarity','Outcome','Excerpt']])

# Add three-column layout with analysis sections
st.markdown("---")
st.subheader("🔍 Case Analysis")

# Create three columns
col1, col2, col3 = st.columns(3)

# Jurification section
with col1:
    st.markdown("### ⚖️ Jurisdiction")
    jurification_text = """
    This section contains the legal foundations analysis of your case.
    
    The jurisdiction analysis evaluates the legal frameworks, precedents, and principles that could support your position. It identifies the strongest legal arguments and authorities that apply to your specific situation.
    
    Based on the retrieved precedents, several key legal principles emerge that could strengthen your position in this arbitration matter.
    """
    st.text_area("", jurification_text, height=200, key="jurification_box", disabled=True)

# Assembility section
with col2:
    st.markdown("### 🧩 Admissibility")
    assembility_text = """
    This section analyzes how to structure your legal arguments effectively.
    
    The admissiblity analysis provides a strategic framework for organizing your legal contentions, evidence, and procedural approaches. It suggests the optimal sequence and emphasis for presenting your case.
    
    Consider beginning with the strongest precedent-based arguments, then addressing causation elements before concluding with remedial proposals.
    """
    st.text_area("", assembility_text, height=200, key="assembility_box", disabled=True)

# Merits section
with col3:
    st.markdown("### ⭐ Merits")
    merits_text = """
    This section evaluates the substantive strengths of your case.
    
    The merits analysis objectively assesses the factual and legal strengths and weaknesses of your position. It provides a realistic evaluation of success likelihood and identifies areas requiring additional evidence or argument development.
    
    Based on similar precedents, your position shows moderate to strong potential, particularly regarding the causation elements which have been decisive in 65% of comparable cases.
    """
    st.text_area("", merits_text, height=200, key="merits_box", disabled=True)



st.markdown("---")
title_col, chart_col = st.columns([1, 2])
with title_col:
    st.subheader("📊 Probability of Success")
success_pct = 64

df_prob = pd.DataFrame({
    'category': ['Success', 'Remaining'],
    'value':    [success_pct, 100 - success_pct]
})

chart = (
    alt.Chart(df_prob)
       .mark_arc(innerRadius=70, stroke="#fff")
       .encode(
         theta=alt.Theta('value:Q'),
         color=alt.Color(
           'category:N',
           scale=alt.Scale(
             domain=['Success','Remaining'],
             range=['#4caf50', '#e0e0e0']
           ),
           legend=None
         )
       )
       .properties(width=200, height=200) 
)

# Create a single-row dataframe for the text
text_df = pd.DataFrame({'text': [f"{success_pct}%"]})

# Create the text layer
text_chart = (
    alt.Chart(text_df)
        .mark_text(
            size=20,
            font='Arial',
            fontWeight='bold'
        )
        .encode(
            text='text:N'
        )
        .properties(width=200, height=200)
)

# Combine the charts
chart_comb = alt.layer(chart, text_chart).resolve_scale(color='independent')

with chart_col:
    st.altair_chart(chart_comb, use_container_width=False)



st.markdown("---")
st.subheader("💡 Improve strategy")
st.markdown("In order to imporve your strategy and reasoning we will propse changes to you strategy based on the similar cases you selected with the filters on the left side. You can accept ot decline the changes.")