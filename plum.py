import streamlit as st
import os
import requests
import pandas as pd
from io import BytesIO
import pdfplumber  # Using pdfplumber for PDF extraction
from docx import Document
import re
from word2number import w2n
import spacy

# Load the English language model for spaCy
nlp = spacy.load("en_core_web_sm")

# Helper function to extract text from PDF using pdfplumber
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Helper function to extract text from DOCX file
def extract_text_from_docx(file):
    doc = Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Function to extract details from the resume and job description
def extract_details(resume_text, job_description):
    # Process the resume text using spaCy NLP
    doc = nlp(resume_text)
    
    # Extract skills and other key information (for simplicity, only skills and experience)
    skills = []
    experience = []
    for token in doc:
        if token.pos_ == 'NOUN':  # Example to extract nouns (skills and experience terms)
            skills.append(token.text)
    
    # Here you can expand to extract other relevant details, such as experience, education, etc.
    # For now, let's just assume skills are the key info we match with the job description.

    # For job description matching, you would check the intersection of extracted skills and job requirements.
    job_doc = nlp(job_description)
    job_skills = [token.text.lower() for token in job_doc if token.pos_ == 'NOUN']

    matching_skills = set(skills) & set(job_skills)  # Find common skills

    # Calculating a simple score based on the number of matching skills
    score = len(matching_skills)

    return {
        'Skills': ", ".join(matching_skills),
        'Score': score
    }

# Function to process resumes and job description
def process_resumes(resume_input, job_description_input):
    resume_files = []

    # Check if resume_input is a URL
    if resume_input.lower().startswith("http"):
        try:
            response = requests.get(resume_input)
            response.raise_for_status()
            resume_files = [BytesIO(response.content)]
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching resume from URL: {e}")
            return None  # Return None to indicate failure to fetch resume
    else:
        # Check if resume_input is a directory and add PDFs and DOCXs
        if os.path.isdir(resume_input):
            resume_files = [os.path.join(resume_input, f) for f in os.listdir(resume_input) if f.lower().endswith(('.pdf', '.docx'))]
        else:
            st.error("The provided path is neither a folder nor a valid URL.")
            return None  # Return None to indicate invalid input

    if not resume_files:
        st.error("No valid resume files found.")
        return None  # Return None if no valid resume files are found

    results = []
    for resume_file in resume_files:
        if isinstance(resume_file, BytesIO):
            file_content = resume_file.read()
            if resume_input.lower().endswith(".pdf"):
                resume_text = extract_text_from_pdf(BytesIO(file_content))
            elif resume_input.lower().endswith(".docx"):
                resume_text = extract_text_from_docx(BytesIO(file_content))
        else:
            if resume_file.endswith(".pdf"):
                with open(resume_file, "rb") as file:
                    resume_text = extract_text_from_pdf(file)
            elif resume_file.endswith(".docx"):
                with open(resume_file, "rb") as file:
                    resume_text = extract_text_from_docx(file)
            else:
                st.warning("Unsupported file type!")
                continue

        resume_details = extract_details(resume_text, job_description_input)
        results.append(resume_details)

    # Sort results based on matching skills (Score)
    sorted_results = sorted(results, key=lambda x: x['Score'], reverse=True)
    for idx, result in enumerate(sorted_results, start=1):
        result['Ranking'] = idx  # Assign Rank

    return sorted_results

# Function to save results to a CSV file and display DataFrame
def save_results_to_csv_and_display(results, file_name="resume_analysis_results.csv"):
    # Convert results to a pandas DataFrame
    df = pd.DataFrame(results)

    # Save the DataFrame to a CSV file
    df.to_csv(file_name, index=False)
    st.success(f"Results saved to {file_name}")

    # Display the DataFrame
    return df

# Streamlit app UI
st.title("Resume and Job Description Matching Tool")

st.markdown("Upload your resume(s) and enter a job description to analyze the match.")

# File uploader for resumes
uploaded_files = st.file_uploader("Upload Resume(s)", type=["pdf", "docx"], accept_multiple_files=True)

# Job description input box
job_description_input = st.text_area("Enter Job Description")

# Button to process
if st.button("Process Resumes"):
    if uploaded_files and job_description_input:
        # Process the resumes
        resume_texts = [file.read() for file in uploaded_files]

        # Convert resume files to text
        resume_details = []
        for file_content in resume_texts:
            if file_content.endswith(b'.pdf'):
                resume_text = extract_text_from_pdf(BytesIO(file_content))
            elif file_content.endswith(b'.docx'):
                resume_text = extract_text_from_docx(BytesIO(file_content))

            resume_details.append(extract_details(resume_text, job_description_input))

        # Sort results based on score
        sorted_results = sorted(resume_details, key=lambda x: x['Score'], reverse=True)

        # Display results
        st.write("### Resume Matching Results")
        st.dataframe(pd.DataFrame(sorted_results))

        # Option to download results
        if st.button("Download Results as CSV"):
            df = pd.DataFrame(sorted_results)
            df.to_csv("resume_analysis_results.csv", index=False)
            st.success("CSV file downloaded successfully.")
    else:
        st.warning("Please upload resume(s) and enter a job description.")
