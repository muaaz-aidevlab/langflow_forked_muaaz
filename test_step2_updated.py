import streamlit as st
import json
from docx import Document
from langflow.processing.load import load_flow_from_json
import os

from dotenv import load_dotenv
load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')

# Load initial JSON configuration
with open('carlat_step1_updated.json', "r", encoding="utf-8") as f:
    flow_graph = json.load(f)


def update_api_key(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) or isinstance(value, list):
                update_api_key(value)  # Recurse into sub-dicts or lists
            elif key == 'name' and value == 'openai_api_key':
                if 'value' in data:
                    old_value = data['value']  # Capture old value for logging or other purposes
                    data['value'] = openai_api_key  # Update with new API key
                    print(f"API key updated from {old_value} to {openai_api_key}")
    elif isinstance(data, list):
        for item in data:
            update_api_key(item)  # Recurse into elements if it's a list

# Update the API key in the JSON
update_api_key(flow_graph)

def update_json_with_file_path(uploaded_file):
    # Save the uploaded file and update the JSON configuration
    if uploaded_file is not None:
        base_path = os.getcwd()  # Or any directory you want to save files in
        file_path = os.path.join(base_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        # Update the JSON node for the PDF loader with the new file path
        for node in flow_graph["data"]["nodes"]:
            if node["data"]["type"] == "PyPDFLoader":
                node["data"]["node"]["template"]["file_path"]["file_path"] = file_path
        return file_path
    return None

def load_flow():
    return load_flow_from_json(flow_graph)

def extract_keywords(flow1):
    result = flow1('Return up to 10 most interesting and important key topics found in this raw Q&A transcript. Display them as a bulleted list. Only return the topics and do not return the descriptions')
    content_output = result['chat_history'][1].content
    return content_output

def get_quotes(flow1, topics):
    result = flow1(f'For each of the extracted topics, find the relevant quotes from the script: {topics}. Return the quotes as they have appeared in the script, no changes should be made.')
    quotes_output = result['chat_history'][1].content
    return quotes_output

def get_qa_pairs(flow1, quotes):
    result = flow1(f'For each of the extracted quotes, generate well-worded question and answer pair: {quotes}. Do not mention the name of the interviewers or interviewee in the question answer pairs.')
    qa_pairs_output = result['chat_history'][1].content
    return qa_pairs_output

def create_docx(content, filename):
    doc = Document()
    doc.add_paragraph(content)
    doc.save(filename)

# Streamlit UI components
st.title("Dr. Carlat's App")

uploaded_file = st.file_uploader("Upload a document", type=["pdf"])
if uploaded_file:
    file_path = update_json_with_file_path(uploaded_file)
    st.success(f"File uploaded at {file_path}")

    flow1 = load_flow()

    if st.button("Extract Keywords"):
        keywords = extract_keywords(flow1)
        st.session_state.keywords = keywords  # Save keywords to session state

    if "keywords" in st.session_state:
        # Display keywords in an editable text box
        st.session_state.edited_keywords = st.text_area("Edit Keywords", value=st.session_state.keywords, height=300)

    if st.button("Get Quotes"):
        if "keywords" in st.session_state:
            quotes = get_quotes(flow1, st.session_state.edited_keywords)
            st.session_state.quotes = quotes  # Save quotes to session state
        # elif st.session_state.edited_keywords:
        #     quotes = get_quotes(flow1, st.session_state.edited_keywords)
        #     st.session_state.quotes = quotes
        else:
            st.error("Extract keywords first before getting quotes.")

    if "quotes" in st.session_state:
        # Display quotes in a new text box
        st.text_area("Extracted Quotes", value=st.session_state.quotes, height=300, key="quotes_box")

    if st.button("Get QA pairs"):
        if "quotes" in st.session_state:
            qa_pairs = get_qa_pairs(flow1, st.session_state.quotes)
            st.session_state.qa_pairs = qa_pairs  # Save QA pairs to session state
        else:
            st.error("Generate quotes first before getting QA pairs.")

    if "qa_pairs" in st.session_state:
        # Display QA pairs in a new text box
        st.text_area("Generated QA Pairs", value=st.session_state.qa_pairs, height=300, key="qa_pairs_box")

        if st.button("Download QA Pairs"):
            create_docx(st.session_state.qa_pairs, "qa_pairs.docx")
            with open("qa_pairs.docx", "rb") as file:
                st.download_button(
                    label="Download QA Pairs as DOCX",
                    data=file,
                    file_name="qa_pairs.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    if st.button("Download Keywords"):
        create_docx(st.session_state.edited_keywords if 'keywords' in st.session_state else '', 'output.docx')
        with open("output.docx", "rb") as file:
            st.download_button(
                label="Download Keywords as DOCX",
                data=file,
                file_name="output.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
