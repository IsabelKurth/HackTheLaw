import streamlit as st
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
)
from vertexai.language_models import TextEmbeddingModel
import json
import pandas as pd
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# --- Suppress a known, harmless warning from the Google Cloud client ---
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="google.cloud.aiplatform.compat.services.prediction_service_client",
)

# --- DIRECT CONFIGURATION & INITIALIZATION ---
PROJECT_ID = "hack-thelaw25cam-586"
LOCATION = "us-central1"

if "gcp_initialized" not in st.session_state:
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        st.session_state.gcp_initialized = True
        print(f"✅ Vertex AI Initialized directly with Project ID: {PROJECT_ID}")
    except Exception as e:
        st.session_state.gcp_initialized = False
        st.error(f"""
        🔴 **Failed to initialize Google Cloud AI.**
        This usually means you are not authenticated.
        
        **Please run the following command in your terminal and then restart the app:**
        ```
        gcloud auth application-default login
        ```
        *Original Error: {e}*
        """)

# ==============================================================================
# SCRIPT 1: ADVANCED STRATEGY ANALYSIS
# ==============================================================================

if st.session_state.get("gcp_initialized", False):
    generation_config = GenerationConfig(
        temperature=0.4,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
    )
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    # Using the exact model name you specified.
    MODEL_NAME_GEN = "gemini-2.0-flash-lite-001"
    try:
        reasoning_model = GenerativeModel(
            MODEL_NAME_GEN,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
    except Exception as e:
        st.error(
            f"Could not initialize Generative Model '{MODEL_NAME_GEN}'. It may not be available in your project. Error: {e}"
        )
        st.session_state.gcp_initialized = False


@st.cache_data
def analyze_arbitration_strategy(strategy_text: str, factual_text: str) -> str:
    if not st.session_state.get("gcp_initialized", False):
        return json.dumps(
            {"error": "GCP not initialized. Cannot perform analysis."}, indent=4
        )
    if not strategy_text and not factual_text:
        return json.dumps(
            {"error": "Both strategy and factual text are empty."}, indent=4
        )

    factual_text = """Fenoscadia Limited (“Fenoscadia”) is a privately owned mining company incorporated in the Republic of Ticadia. In 2008, the Republic of Kronos, a neighboring state, granted Fenoscadia an exclusive 80-year license to extract lindoro, a rare earth metal, from its territory. The concession agreement permitted Fenoscadia to mine lindoro in Kronos’s inland regions, and the company began commercial operations shortly thereafter. Lindoro is a valuable resource used in electronics and renewable energy technologies, and Fenoscadia became the sole extractor of lindoro in Kronos.

Over the years, Fenoscadia invested significantly in infrastructure, technology, and labor to support its operations, and the project became a key part of Kronos’s export economy. However, tensions emerged in 2016 when the government of Kronos issued Presidential Decree No. 242, revoking Fenoscadia’s mining license and unilaterally terminating the concession. The decree cited environmental and public health concerns, referencing a government-funded scientific study that allegedly linked lindoro mining to contamination of the Rhea River and increased rates of cardiovascular disease and microcephaly among local populations.

The study, however, did not conclusively establish a direct causal link between Fenoscadia’s operations and the alleged health or environmental harms. Despite this, Kronos proceeded with the revocation, ordered the immediate cessation of lindoro extraction, and confiscated all extracted lindoro stored on site. Fenoscadia contends that it was not afforded due process and that the revocation amounted to an unlawful expropriation of its investment in violation of the Ticadia–Kronos Bilateral Investment Treaty (“the BIT”).

Arbitration proceedings were subsequently initiated by Fenoscadia against Kronos. In response, Kronos filed a counterclaim, seeking at least USD 150 million in damages for alleged environmental degradation, public health costs, and the expense of purifying contaminated water sources. Fenoscadia disputes both the jurisdiction of the tribunal over the counterclaim and its substantive validity, arguing that its operations were conducted in compliance with Kronos’s environmental regulations and that the study lacks sufficient scientific basis to support the claimed damages."""

    # --- FULL PROMPT AS PROVIDED ---
    prompt = [
        "You are an expert legal counsel in international investment arbitration. You will be given two pieces of text: a 'CASE STRATEGY' and a 'FACTUAL BACKGROUND'.",
        "Your task is to perform a comprehensive analysis and produce a single JSON array containing all identified arguments. You must perform three steps:",
        "1. Deconstruct the user's 'CASE STRATEGY' into its core arguments.",
        "2. For each of those arguments, cross-reference it with the 'FACTUAL BACKGROUND' and your knowledge of international arbitration to check for accuracy. Be aware that arguments from the users strategy might be factually incorect",
        "3. Identify any NEW potential arguments (for or against the user's position) that are suggested by the 'FACTUAL BACKGROUND' but were NOT mentioned in the 'CASE STRATEGY'.",
        "For EACH argument in the final JSON output, you must provide:",
        " - `title`: A very short, 3-4 word title for the argument.",
        " - `argument`: A concise, standalone statement of the argument.",
        " - `category`: Classify as 'Jurisdiction', 'Admissibility', or 'Merits'.",
        " - `factual_check`: true if it is consistent with the factual background or provide a short correction (e.g., 'Correction: The contract specifies a 90-day notice period, not 60.'). Be aware that the user may need to be corrected",
        " - `source_text`: For arguments from the user's strategy, quote the verbatim source sentence(s). For newly discovered arguments, this should be 'N/A'.",
        " - `is_new_argument`: A boolean value. `false` for arguments from the user's strategy, `true` for newly discovered arguments.",
        "Provide your output as a single, valid JSON array of objects only. Do not add explanations outside the JSON.",
        "Example output format:",
        """
[
    {
    "title": "Legitimate Regulatory Action",
    "argument": "The government's actions were legitimate regulatory measures for public health and not expropriation.",
    "category": "Merits",
    "factual_check": "true",
    "source_text": "we will demonstrate that the government's actions were legitimate, non-discriminatory regulatory measures designed to protect public health and did not amount to an expropriation of the claimant's investment.",
    "is_new_argument": false
    },
    {
    "title": "New Fork-in-the-Road Argument",
    "argument": "The claimant may be barred from arbitration because they first initiated proceedings regarding the same dispute in the host state's local courts.",
    "category": "Admissibility",
    "factual_check": "true",
    "source_text": "N/A",
    "is_new_argument": true
    }
]
        """,
        "--- CASE STRATEGY ---",
        strategy_text,
        "--- FACTUAL BACKGROUND ---",
        factual_text,
    ]

    try:
        response = reasoning_model.generate_content(prompt)
        text_response = response.text
        start, end = text_response.find("["), text_response.rfind("]")
        if start != -1 and end != -1:
            json_str = text_response[start : end + 1]
            parsed_json = json.loads(json_str)
            return json.dumps(parsed_json, indent=4)
        return json.dumps(
            {
                "error": "No valid JSON array found in model's response.",
                "raw_response": text_response,
            },
            indent=4,
        )
    except Exception as e:
        return json.dumps(
            {
                "error": f"An unexpected error occurred during strategy analysis: {str(e)}"
            },
            indent=4,
        )


# ==============================================================================
# SCRIPT 2: SIMILAR ARGUMENT SEARCH
# ==============================================================================

if st.session_state.get("gcp_initialized", False):
    DATABASE_FILE, EMBEDDINGS_FILE = (
        "legal_arguments_database_merged.csv",
        "arguments_embeddings.npy",
    )
    MODEL_NAME_EMBED = "gemini-embedding-001"
    try:
        embedding_model = TextEmbeddingModel.from_pretrained(MODEL_NAME_EMBED)
        db_df = pd.read_csv(DATABASE_FILE)
        corpus_embeddings = np.load(EMBEDDINGS_FILE)
    except Exception as e:
        st.warning(
            f"Could not load search database or embedding model '{MODEL_NAME_EMBED}'. Search will be disabled. Error: {e}"
        )
        st.session_state.gcp_initialized = False


@st.cache_data
def get_similar_arguments_as_json(query_text: str, top_n: int = 5) -> str:
    if not st.session_state.get("gcp_initialized", False) or not query_text.strip():
        return json.dumps(
            [
                {
                    "error": "GCP not initialized or query is empty. Cannot perform search."
                }
            ],
            indent=4,
        )
    try:
        query_embedding = np.array(
            embedding_model.get_embeddings([query_text])[0].values
        ).reshape(1, -1)
        similarities = cosine_similarity(query_embedding, corpus_embeddings)[0]
        top_n_indices = np.argsort(similarities)[::-1][:top_n]
        results_df = db_df.iloc[top_n_indices].copy()
        results_df["similarity_score"] = similarities[top_n_indices]
        results_df = results_df.fillna("N/A")
        output_list = [
            {
                "similarity_score": row["similarity_score"],
                "case_identifier": row["case_identifier"],
                "case_title": row["case_title"],
                "argument_summary": row["argument_summary"],
                "judgment": row["court_followed"],
                "judgment_summary": row["tribunal_reasoning"],
            }
            for _, row in results_df.iterrows()
        ]
        return json.dumps(output_list, indent=4)
    except Exception as e:
        return json.dumps(
            {"error": f"An unexpected error occurred during search: {str(e)}"}, indent=4
        )
