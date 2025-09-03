import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os

# Function to extract text from a PDF
def get_pdf_text(pdf_file):
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
        return None
    return text

# --- State Management: The "memory" of our app ---
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
if 'qa_pairs' not in st.session_state:
    st.session_state.qa_pairs = []
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = []
if 'final_evaluation' not in st.session_state:
    st.session_state.final_evaluation = None

# --- Streamlit App Interface ---
st.set_page_config(page_title="Viva Voce AI Preparer", layout="wide")
st.title("🎓 AI Viva Voce Quiz Mode")
st.write("Upload your notes, and the AI will generate a quiz. Answer all questions, then get your score!")

# --- Get API Key from Replit Secrets ---
try:
    api_key = os.environ['GEMINI_API_KEY']
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
except KeyError:
    st.error("GEMINI_API_KEY not found! Please add it to your Replit Secrets.")
    st.stop()

# --- Main App Logic ---
uploaded_file = st.file_uploader("Upload your PDF document to start", type="pdf")

if uploaded_file and not st.session_state.quiz_started:
    if st.button("Start Quiz from this PDF"):
        with st.spinner('Reading your document and preparing the quiz...'):
            document_text = get_pdf_text(uploaded_file)
            if document_text:
                prompt = f"""
                You are an expert college professor creating a quiz. Based ONLY on the provided text, generate exactly 10 viva questions and their ideal, concise answers.
                Format the output strictly as follows, with no extra text:
                Q1: [Your Question Here]
                A1: [Your Answer Here]
                Q2: [Your Question Here]
                A2: [Your Answer Here]
                ...and so on for 10 questions.
                
                Here is the document text:
                {document_text}
                """
                try:
                    response = model.generate_content(prompt)
                    
                    full_text = response.text.strip().split('\n')
                    parsed_pairs = []
                    questions = [line for line in full_text if line.strip().startswith('Q')]
                    answers = [line for line in full_text if line.strip().startswith('A')]

                    if len(questions) == len(answers) and len(questions) > 0:
                        for q, a in zip(questions, answers):
                            question_text = q.split(":", 1)[1].strip()
                            answer_text = a.split(":", 1)[1].strip()
                            parsed_pairs.append((question_text, answer_text))
                        
                        st.session_state.qa_pairs = parsed_pairs
                        st.session_state.quiz_started = True
                        st.rerun()
                    else:
                        st.error("The AI returned an unexpected format. Please try generating the quiz again.")

                except Exception as e:
                    st.error(f"An error occurred with the Gemini API: {e}")

# --- Quiz Interface ---
if st.session_state.quiz_started and not st.session_state.final_evaluation:
    st.header("Answer all the questions below:")
    
    user_answers = []
    for i, (question, ideal_answer) in enumerate(st.session_state.qa_pairs):
        st.markdown(f"**Question {i+1}:** {question}")
        user_answers.append(st.text_area(f"Your Answer for Q{i+1}", key=f"ans_{i}", height=100))

    if st.button("Submit All Answers for Evaluation"):
        if all(answer.strip() for answer in user_answers):
            st.session_state.user_answers = user_answers
            with st.spinner("The AI examiner is grading your answers... This may take a moment."):
                evaluation_prompt = "You are an expert examiner. For each question, evaluate the student's answer against the ideal answer. Provide constructive feedback and a score out of 10 for each question. Be strict but fair. After evaluating all questions, provide a final total score and a summary of the student's performance. Here is the data:\n\n"
                for i, (question, ideal_answer) in enumerate(st.session_state.qa_pairs):
                    evaluation_prompt += f"--- Question {i+1} ---\n"
                    evaluation_prompt += f"Question: {question}\n"
                    evaluation_prompt += f"Ideal Answer: {ideal_answer}\n"
                    evaluation_prompt += f"Student's Answer: {st.session_state.user_answers[i]}\n\n"
                
                try:
                    eval_response = model.generate_content(evaluation_prompt)
                    st.session_state.final_evaluation = eval_response.text
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred during evaluation: {e}")
        else:
            st.warning("Please make sure you have typed an answer for every question before submitting.")

# --- Results Page ---
if st.session_state.final_evaluation:
    st.header("Quiz Results and Feedback")
    st.markdown(st.session_state.final_evaluation)
    
    if st.button("Start a New Quiz"):
        st.session_state.quiz_started = False
        st.session_state.qa_pairs = []
        st.session_state.user_answers = []
        st.session_state.final_evaluation = None
        st.rerun()

