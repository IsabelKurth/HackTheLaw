import streamlit as st
import pandas as pd
import altair as alt
import json
from io import StringIO

# Import the logic functions from your provided scripts
from vertex_ai_logic import analyze_arbitration_strategy, get_similar_arguments_as_json

# --- CSS for the sticky left column ---
st.markdown(
    """
<style>
    /* This selector is robust to Streamlit's internal changes */
    .main .st-emotion-cache-1v0k24x > div:first-child {
        position: sticky;
        top: 5.5rem; 
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        height: calc(100vh - 7rem);
        overflow-y: auto;
    }
    @media (max-width: 768px) {
        .main .st-emotion-cache-1v0k24x > div:first-child {
            position: static;
            height: auto;
            background-color: transparent;
            padding: 0;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- Session State Initialization ---
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False
if "analyzed_arguments" not in st.session_state:
    st.session_state.analyzed_arguments = []


# --- Callback Function ---
def trigger_analysis():
    if not st.session_state.user_prompt.strip() and not st.session_state.get(
        "uploaded_files"
    ):
        st.warning("Please provide a strategy idea or upload documents to analyze.")
        return
    st.session_state.analyzed_arguments = []  # Clear old results before running
    st.session_state.run_analysis = True


# --- Main App ---
from PIL import Image

# Load an image from disk
img = Image.open("logo.png")

# Show it in your app
st.image(img, width=200)
st.set_page_config(page_title="Arbitration Strategy Dashboard", layout="wide")
st.title("Arbitration Strategy Dashboard")

left_col, right_col = st.columns([2, 3])

# --- LEFT COLUMN ---
with left_col:
    st.header("Provide Input")
    st.text_area("My strategy idea is:", height=200, key="user_prompt")
    st.file_uploader(
        "Upload factual documents (TXT)",
        type=["txt"],
        accept_multiple_files=True,
        key="uploaded_files",
    )
    st.button(
        "Analyze Strategy & Find Precedents", on_click=trigger_analysis, type="primary"
    )

# --- RIGHT COLUMN ---
with right_col:
    if st.session_state.run_analysis:
        with st.spinner("Analyzing strategy and finding precedents..."):
            factual_text = "\n\n---\n\n".join(
                [
                    StringIO(file.getvalue().decode("utf-8")).read()
                    for file in st.session_state.get("uploaded_files", [])
                ]
            )

            # --- ROBUST ANALYSIS AND DATA HANDLING BLOCK ---
            strategy_json_string = analyze_arbitration_strategy(
                st.session_state.user_prompt, factual_text
            )
            parsed_data = json.loads(strategy_json_string)

            # Check if the initial analysis was successful
            if isinstance(parsed_data, list) and parsed_data:
                # Success: We received a list of arguments.
                analyzed_args_list = parsed_data

                # Now, loop through them to get similar cases
                for i, arg_dict in enumerate(analyzed_args_list):
                    st.progress(
                        (i + 1) / len(analyzed_args_list),
                        f"Searching precedents for: '{arg_dict['title']}'",
                    )
                    similar_cases_json_string = get_similar_arguments_as_json(
                        arg_dict["argument"]
                    )

                    try:
                        search_results = json.loads(similar_cases_json_string)
                        # Fix for ValueError: Check if the search result is a list (success) or dict (error).
                        if isinstance(search_results, list):
                            arg_dict["similar_cases"] = pd.DataFrame(search_results)
                        else:
                            arg_dict["similar_cases"] = (
                                pd.DataFrame()
                            )  # Create empty DataFrame on search error
                    except (json.JSONDecodeError, TypeError):
                        arg_dict["similar_cases"] = (
                            pd.DataFrame()
                        )  # Handle invalid JSON

                st.session_state.analyzed_arguments = analyzed_args_list

            # Handle all failure cases from the initial analysis
            elif isinstance(parsed_data, dict) and "error" in parsed_data:
                # Failure: We received an error object. Display it.
                st.error(f"Failed to Analyze Strategy: {parsed_data.get('error')}")
                if "raw_response" in parsed_data:
                    st.code(parsed_data["raw_response"], language="text")
                st.session_state.analyzed_arguments = []
            else:
                # Handle any other unexpected format.
                st.error(
                    "Received an unexpected or empty response from the analysis service."
                )
                st.session_state.analyzed_arguments = []

        st.session_state.run_analysis = False  # Reset flag

    # --- Display Results ---
    if st.session_state.analyzed_arguments:
        st.header("In-Depth Argument Analysis")

        jurisdiction_args = [
            arg
            for arg in st.session_state.analyzed_arguments
            if arg.get("category") == "Jurisdiction"
        ]
        admissibility_args = [
            arg
            for arg in st.session_state.analyzed_arguments
            if arg.get("category") == "Admissibility"
        ]
        merits_args = [
            arg
            for arg in st.session_state.analyzed_arguments
            if arg.get("category") == "Merits"
        ]

        analysis_col1, analysis_col2, analysis_col3 = st.columns(3)

        def create_analysis_chart(df: pd.DataFrame):
            if df is None or df.empty or "judgment" not in df.columns:
                return None
            grouped = (
                df.groupby("judgment")
                .agg(
                    Count=("judgment", "size"),
                    CaseIDs=("case_identifier", lambda x: ", ".join(map(str, x))),
                    Titles=("case_title", lambda x: "; ".join(map(str, x))),
                    Summaries=("argument_summary", lambda x: "; ".join(map(str, x))),
                )
                .reindex(["Yes", "No", "N/A"], fill_value=0)
                .reset_index()
                .rename(columns={"judgment": "Outcome"})
            )

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
                        "Outcome:N",
                        scale=alt.Scale(
                            domain=["Yes", "No", "N/A"],
                            range=["#4caf50", "#f44336", "#bdbdbd"],
                        ),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("Outcome:N", title="Outcome"),
                        alt.Tooltip("Count:Q", title="Count"),
                        alt.Tooltip("CaseIDs:N", title="Case IDs"),
                        alt.Tooltip("Titles:N", title="Titles"),
                        alt.Tooltip("Summaries:N", title="Summaries"),
                    ],
                )
                .properties(width=240, height=30)
            )
            return bar_chart

        def display_argument_card(arg: dict, card_id: str):
            title = arg.get("title", "Untitled Argument")
            title_display = f"<div style='margin-bottom: -10px;'> <b>{title}</b>" + (
                " ✨ <span style='color: #28a745;'>New</span>"
                if arg.get("is_new_argument")
                else ""
            )
            st.markdown(title_display, unsafe_allow_html=True)
            check = arg.get("factual_check")
            if check is True:
                st.success("Factually Consistent", icon="✔️")
            elif isinstance(check, str) and check.lower() not in ["n/a", "true"]:
                st.warning(f"{check}", icon="⚠️")
            st.text_area(
                "",
                value=arg.get("argument", ""),
                height=100,
                key=f"arg_{card_id}",
                disabled=True,
            )
            if (
                not arg.get("is_new_argument")
                and arg.get("source_text", "N/A") != "N/A"
            ):
                st.caption(f'Source: "{arg.get("source_text")}"')
            chart = create_analysis_chart(arg.get("similar_cases"))
            if chart:
                st.altair_chart(chart, use_container_width=True)
            else:
                st.caption("No precedent data.")

        with analysis_col1:
            st.markdown("### ⚖️ Jurisdiction")
            for i, arg in enumerate(jurisdiction_args):
                display_argument_card(arg, f"jur_{i}")
        with analysis_col2:
            st.markdown("### 🧩 Admissibility")
            for i, arg in enumerate(admissibility_args):
                display_argument_card(arg, f"adm_{i}")
        with analysis_col3:
            st.markdown("### ⭐ Merits")
            for i, arg in enumerate(merits_args):
                display_argument_card(arg, f"mer_{i}")

    elif not st.session_state.run_analysis:
        st.info(
            "📈 Your results will appear here after you provide input and click the analyze button."
        )
