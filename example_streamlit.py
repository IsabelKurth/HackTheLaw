import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import json

if "show_similar_cases" not in st.session_state:
    st.session_state.show_similar_cases = False
if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False


@st.cache_data
def load_related_cases():
    with open("arbitration_results_general.json", "r") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    return df


@st.cache_data
def load_argument_similar_cases():
    with open("search_results.json", "r") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    return df


# Function to create a sample claims dataframe
@st.cache_data
def load_claims_data():
    with open("input_arguments.json", "r") as f:
        data_args = json.load(f)
    claims_df = pd.DataFrame(data_args)
    return claims_df


# --- Main App ---
st.set_page_config(page_title="Arbitration Strategy Dashboard", layout="wide")
st.title("🌐 Arbitration Strategy Dashboard")

tooltip_html = """
<style>
.tooltip {
  position: relative;
  display: inline-block;
  cursor: help;
}
.tooltip .tooltiptext {
  visibility: hidden;
  width: 200px;
  background-color: rgba(0, 0, 0, 0.75);
  color: #fff;
  text-align: left;
  padding: 5px;
  border-radius: 4px;
  position: absolute;
  bottom: 125%;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  transition: opacity 0.3s;
}
.tooltip:hover .tooltiptext {
  visibility: visible;
  opacity: 1;
}
</style>

<span class="tooltip">
  Hover over this text
  <span class="tooltiptext">My custom box of extra info</span>
</span>
"""
st.markdown(tooltip_html, unsafe_allow_html=True)

st.markdown(
    "Welcome to the Arbitration Strategy Dashboard! This app helps you explore similar cases, improve your strategy and understand the chances of sucess in arbitration cases.",
    help="test helt text",
)


def show_similar_cases():
    st.session_state.show_similar_cases = True


def show_analysis_content():
    st.session_state.show_analysis = True


idea_ready = st.selectbox("Do you have a draft for a first idea?", ["No", "Yes"])
if idea_ready == "Yes":
    # Inline text area instead of st.chat_input
    user_prompt = st.text_area("My first strategy idea is:")
    st.file_uploader(
        "Upload relevant factual documents (PDF, DOCX, TXT, etc.)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )
    if st.button("Send Strategy Idea", on_click=show_similar_cases):
        st.success("Strategy idea received!")
else:
    uploaded_files = st.file_uploader(
        "Upload relevant documents (PDF, DOCX, TXT, etc.)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        st.success(f"{len(uploaded_files)} file(s) uploaded.")
        for file in uploaded_files:
            st.write(f"- {file.name}")
    else:
        st.info("No documents uploaded yet.")
    if st.button("Create Strategy", on_click=show_similar_cases):
        st.success("Strategy generation initiated.")


if st.session_state.show_similar_cases:
    df_arg_rel = load_argument_similar_cases()
    df_rel_cases = load_related_cases()

    st.sidebar.title("🚀 Your Strategy Idea")
    strategy = user_prompt.strip() if "user_prompt" in locals() else ""
    if strategy:
        st.sidebar.write(strategy)
    else:
        st.sidebar.info("No text prompt was provided.")

    # Case-Law Table
    st.markdown("---")
    st.subheader("📚 Retrieved Precedents")
    st.markdown("##### Filter similar cases")
    min_year, max_year = st.slider(
        "Case Year Range",
        int(df_rel_cases.source_year.min()),
        int(df_rel_cases.source_year.max()),
        (2017, 2024),
    )
    outcome_filter = st.multiselect(
        "Outcome",
        options=df_rel_cases.content_type.unique(),
        default=list(df_rel_cases.content_type.unique()),
    )
    similarity_threshold = st.slider("Min. Similarity", 0.0, 1.0, 0.6, 0.01)

    # Apply Filters
    filtered = df_rel_cases[
        (df_rel_cases.source_year.between(min_year, max_year))
        & (df_rel_cases.content_type.isin(outcome_filter))
        & (df_rel_cases.similarity_score >= similarity_threshold)
    ].head(5)
    st.dataframe(
        filtered.sort_values(by="similarity_score", ascending=False)[
            ["CaseNumber", "source_title", "llm_summary", "content_type"]
        ]
    )
    if st.button(
        "Use filtered cases to analyse my strategy", on_click=show_analysis_content
    ):
        st.success("Analysis initiated with selected cases.")

    if st.session_state.show_analysis:
        # Add three-column layout with analysis sections
        st.markdown("---")
        st.subheader("🔍 Case Analysis")
        claims_df = load_claims_data()

        # Create three columns
        col1, col2, col3 = st.columns(3)

        # Jurisdiction section
        with col1:
            st.markdown("### ⚖️ Jurisdiction")
            jurisdiction_claims = claims_df[claims_df["category"] == "Jurisdiction"]
            for idx, row in jurisdiction_claims.iterrows():
                st.markdown(
                    f"<div style='margin-bottom:-10px'><b>{row['title']}</b></div>",
                    unsafe_allow_html=True,
                )
                st.text_area(
                    label="",
                    value=row["argument"],
                    height=100,
                    key=f"claim_Jurisdiction_{idx}",
                    disabled=True,
                )
                # Only show the donut plot below the first text box
                if idx == jurisdiction_claims.index[0]:
                    # Assume the relevant column in df is 'jurisdiction' and values are 'N/A', 'No', 'Yes'
                    # Group by 'judgment' and aggregate case ids and titles
                    grouped = (
                        df_arg_rel.groupby("judgment")
                        .agg(
                            Count=("judgment", "size"),
                            CaseIDs=(
                                "case_identifier",
                                lambda x: ", ".join(map(str, x)),
                            ),
                            Titles=("case_title", lambda x: "; ".join(map(str, x))),
                        )
                        .reindex(["N/A", "No", "Yes"], fill_value=0)
                        .reset_index()
                        .rename(columns={"judgment": "Jurisdiction"})
                    )

                    # Create a single horizontal bar with segments for Yes, No, N/A
                    bar_data = grouped.copy()
                    bar_data["x0"] = bar_data["Count"].cumsum().shift(fill_value=0)
                    bar_data["x1"] = bar_data["Count"].cumsum()

                    bar_chart = (
                        alt.Chart(bar_data)
                        .mark_bar(height=30)
                        .encode(
                            x=alt.X("x0:Q", axis=None),
                            x2="x1:Q",
                            color=alt.Color(
                                "Jurisdiction:N",
                                scale=alt.Scale(
                                    domain=["Yes", "No", "N/A"],
                                    range=["#4caf50", "#f44336", "#bdbdbd"],
                                ),
                                legend=None,
                            ),
                            tooltip=[
                                alt.Tooltip("Jurisdiction:N", title="Jurisdiction"),
                                alt.Tooltip("Count:Q", title="Count"),
                                alt.Tooltip("CaseIDs:N", title="Case IDs"),
                                alt.Tooltip("Titles:N", title="Titles"),
                            ],
                        )
                        .properties(width=240, height=30)
                    )

                    st.altair_chart(bar_chart, use_container_width=False)

        # Admissibility section
        with col2:
            st.markdown("### 🧩 Admissibility")
            admissibility_claims = claims_df[claims_df["category"] == "Admissibility"]
            for idx, row in admissibility_claims.iterrows():
                st.markdown(
                    f"<div style='margin-bottom:-10px'><b>{row['title']}</b></div>",
                    unsafe_allow_html=True,
                )
                st.text_area(
                    label="",
                    value=row["argument"],
                    height=100,
                    key=f"claim_Admissibility_{idx}",
                    disabled=True,
                )

        # Merits section
        with col3:
            st.markdown("### ⭐ Merits")
            merits_claims = claims_df[claims_df["category"] == "Merits"]
            for idx, row in merits_claims.iterrows():
                st.markdown(
                    f"<div style='margin-bottom:-10px'><b>{row['title']}</b></div>",
                    unsafe_allow_html=True,
                )
                st.text_area(
                    label="",
                    value=row["argument"],
                    height=100,
                    key=f"claim_Merits_{idx}",
                    disabled=True,
                )

        st.markdown("---")
        st.subheader("💡 Improve strategy")
        st.markdown(
            "In order to imporve your strategy and reasoning we will propse changes to you strategy based on the similar cases you selected with the filters on the left side. You can accept ot decline the changes."
        )
