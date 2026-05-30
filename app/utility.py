from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.models import JobDescription,CandidateResult
import os
from app.database import SessionLocal
from docx import Document
from PyPDF2 import PdfReader
import textract
import json
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_semantic_similarity(
    jd_text,
    resume_text
):

    documents = [

        resume_text,

        jd_text
    ]

    vectorizer = TfidfVectorizer(
        stop_words="english"
    )

    tfidf_matrix = vectorizer.fit_transform(
        documents
    )

    similarity = cosine_similarity(

        tfidf_matrix[0:1],

        tfidf_matrix[1:2]

    )[0][0]

    return round(
        similarity * 100,
        2
    )
import fitz
from groq import (
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    InternalServerError
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import test_connection
from app.database import engine
from app.models import Base
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.database import SessionLocal
from app.models import JobDescription
from uuid import uuid4
import os
import shutil
from typing import List
import re
from dotenv import load_dotenv
import os


load_dotenv()


groq_api_key = os.getenv(
    "GROQ_KEY"
)

llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="llama-3.3-70b-versatile"
)



def create_job_description(
    UPLOAD_FOLDER,

    jd_text: str = Form(default=""),
    jd_file: UploadFile = File(default=None),

):

    db = SessionLocal()

    try:

        extracted_text = ""
        saved_file_path = None

        # -------------------------
        # CASE 1 -> JD FILE UPLOADED
        # -------------------------
        if jd_file:

            

            # Generate unique filename
            unique_filename = (
                f"{uuid4()}_{jd_file.filename}"
            )

            saved_file_path = os.path.join(
                UPLOAD_FOLDER,
                unique_filename
            )

            # Save file
            with open(saved_file_path, "wb") as buffer:

                shutil.copyfileobj(
                    jd_file.file,
                    buffer
                )

            # TODO:
            # Extract text from PDF/DOCX here
            # For now dummy text
            extracted_text = extract_text_from_file(saved_file_path)
            if(extracted_text['success']==False):
                return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": extracted_text["error"],
                }
            )

            
            extracted_text=extracted_text['text']

        # -------------------------
        # CASE 2 -> JD TEXT PROVIDED
        # -------------------------
        elif jd_text:

            extracted_text = jd_text

        else:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Provide JD text or JD file"
                }
            )

        # -------------------------
        # GENERATE TITLE
        # -------------------------
        title_result = generate_jd_title(
            extracted_text
        )

        if not title_result["success"]:

            return JSONResponse(
                status_code=500,
                content=title_result
            )

        generated_title = title_result["title"]

        # -------------------------
        # STORE IN DATABASE
        # -------------------------
        new_jd = JobDescription(

            title=generated_title,

            jd_text=extracted_text,

            jd_file_path=saved_file_path

        )

        db.add(new_jd)

        db.commit()

        db.refresh(new_jd)

        return {

            "success": True,

            "message": "JD stored successfully",

            "data": {

                "id": new_jd.id,

                "title": new_jd.title,

                "jd_file_path": new_jd.jd_file_path,
                "jd_text":extracted_text

            }
        }

    except Exception as e:

        db.rollback()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

    finally:

        db.close()



def generate_jd_title(jd_text):

    try:

        # Validate input
        if not jd_text:
            return {
                "success": False,
                "error": "JD text is empty"
            }

        if not isinstance(jd_text, str):
            return {
                "success": False,
                "error": "JD text must be string"
            }

        if len(jd_text.strip()) == 0:
            return {
                "success": False,
                "error": "JD text contains only spaces"
            }

        # Optional size limit
        if len(jd_text) > 50000:
            return {
                "success": False,
                "error": "JD text too large"
            }

        # Prompt
        prompt = PromptTemplate(
            input_variables=["jd"],
            template="""
            Generate a short professional job title
            from this job description.

            Job Description:
            {jd}

            Rules:
            - Return ONLY title
            - Maximum 8 words
            - No explanation
            """
        )

        chain = prompt | llm

        response = chain.invoke({
            "jd": jd_text
        })

        # Validate response
        if not response:
            return {
                "success": False,
                "error": "No response from LLM"
            }

        title = response.content.strip()

        if not title:
            return {
                "success": False,
                "error": "Empty title generated"
            }

        return {
            "success": True,
            "title": title
        }

    except AuthenticationError:

        return {
            "success": False,
            "error": "Invalid Groq API key"
        }

    except RateLimitError:

        return {
            "success": False,
            "error": "Groq rate limit exceeded"
        }

    except APIConnectionError:

        return {
            "success": False,
            "error": "Internet/API connection error"
        }

    except BadRequestError as e:

        return {
            "success": False,
            "error": f"Bad request: {str(e)}"
        }

    except InternalServerError:

        return {
            "success": False,
            "error": "Groq internal server error"
        }

    except Exception as e:

        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }




def extract_text_from_file(file_path):

    try:

        if not os.path.exists(file_path):

            return {
                "success": False,
                "error": "File does not exist"
            }

        extension = file_path.split(".")[-1].lower()

        # -------------------------
        # PDF
        # -------------------------
        if extension == "pdf":

            return extract_text_from_pdf(file_path)

        # -------------------------
        # DOCX
        # -------------------------
        elif extension == "docx":

            return extract_text_from_docx(file_path)

        # -------------------------
        # DOC
        # -------------------------
        elif extension == "doc":

            return extract_text_from_doc(file_path)

        else:

            return {
                "success": False,
                "error": "Unsupported file format"
            }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }





def clean_extracted_text(text):

    
    text = re.sub(
        r"[^\x00-\x7F]+",
        " ",
        text
    )

   
    text = re.sub(
        r"/(?=[A-Za-z])",
        " ",
        text
    )

    
    text = re.sub(
        r"[•◆▪►■◉➢➤★☆✓✔]",
        " ",
        text
    )

   
    text = re.sub(
        r"[_\-]{2,}",
        " ",
        text
    )

    
    text = re.sub(
        r"\s*@\s*",
        "@",
        text
    )

    
    text = re.sub(
        r"\s*\.\s*",
        ".",
        text
    )

    
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()



def extract_text_from_pdf(file_path):

    try:

        text = ""

        pdf = fitz.open(file_path)

        for page in pdf:

            text += page.get_text()

        
        cleaned_text = clean_extracted_text(
            text
        )

        return {

            "success": True,

            "text": cleaned_text
        }

    except Exception as e:

        return {

            "success": False,

            "error": str(e)
        }


def extract_text_from_docx(file_path):

    try:

        doc = Document(file_path)

        extracted_text = "\n".join(
            para.text for para in doc.paragraphs
        )

        return {
            "success": True,
            "text": extracted_text.strip()
        }

    except Exception as e:

        return {
            "success": False,
            "error": f"DOCX extraction failed: {str(e)}"
        }



def extract_text_from_doc(file_path):

    try:

        text = textract.process(file_path)

        extracted_text = text.decode("utf-8")

        return {
            "success": True,
            "text": extracted_text.strip()
        }

    except Exception as e:

        return {
            "success": False,
            "error": f"DOC extraction failed: {str(e)}"
        }






def jd_data_extract(jd_text):

    """
    Extracts technical requirements from JD
    using LLM.
    """

    try:

        if not jd_text:

            return {
                "success": False,
                "error": "JD text is empty"
            }

        prompt = PromptTemplate(

            input_variables=["jd"],

            template="""
            You are an ATS Job Description parser.

            Analyze the following job description.

            Extract ONLY technology-related
            hiring requirements.

            Ignore:
            - soft skills
            - communication skills
            - teamwork
            - leadership
            - generic responsibilities

            Focus ONLY on:
            - programming languages
            - frameworks
            - databases
            - cloud platforms
            - DevOps tools
            - AI/ML technologies
            - libraries
            - APIs
            - software tools
            - years of experience

            Return ONLY valid JSON.

            Required JSON format:

            {{
                "mandatory_skills": [],

                "preferred_skills": [],

                "programming_languages": [],

                "frameworks": [],

                "databases": [],

                "cloud_platforms": [],

                "devops_tools": [],

                "ai_ml_tools": [],

                "apis_and_services": [],

                "experience_requirements": {{
                    "minimum_years": "",
                    "preferred_years": ""
                }},
                "education_requirements":[]
            }}

            Rules:
            - Return only JSON
            - No markdown
            - No explanations
            - Avoid duplicates
            - Include only technical requirements

            Job Description:
            {jd}
            """
        )

        chain = prompt | llm

        response = chain.invoke({

            "jd": jd_text

        })

        content = response.content.strip()

        content = content.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        parsed_data = json.loads(content)

        return {

            "success": True,

            "data": parsed_data
        }

    except json.JSONDecodeError:

        return {
            "success": False,
            "error": "Invalid JSON returned by LLM"
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
def process_resumes(

    resume_file_paths,
    jd_id,
    jd_text,
    jd_data,

):
    db = SessionLocal()

    processed_candidates = []

    try:

        for resume_path in resume_file_paths:

            
            if not os.path.exists(resume_path):

                processed_candidates.append({
                    "resume": resume_path,
                    "success": False,
                    "error": "File does not exist"
                })

                continue

           
            extraction_result = extract_text_from_file(
                resume_path
            )

            if not extraction_result["success"]:

                processed_candidates.append({
                    "resume": resume_path,
                    "success": False,
                    "error": extraction_result["error"]
                })

                continue

            resume_text = extraction_result["text"]

            
            extracted_resume_data = extract_resume_details(
    resume_text
)

            
            if not extracted_resume_data["success"]:

                processed_candidates.append({

                    "resume": resume_path,

                    "success": False,

                    "error": extracted_resume_data["error"]
                })
 
                continue
            resume_data = extracted_resume_data["data"]
            
            

           

            semantic_similarity_score = (
                calculate_semantic_similarity(
                    jd_text,
                    resume_text                )
            )

            score_result = calculate_candidate_scores(

            jd_data,

            extracted_resume_data

)  
            if not score_result["success"]:

                processed_candidates.append({

                    "resume": resume_path,

                    "success": False,

                    "error": score_result["error"]
                })

                continue
            scores = score_result["data"]

            

            skills_matching_score = scores[
                "skills_matching_score"
            ]

            experience_relevance_score = scores[
                "experience_relevance_score"
            ]

            education_alignment_score = scores[
                "education_alignment_score"
            ]

            publication_score = scores[
                "publication_score"
            ]

            

            matching_skills = scores[
                "matching_skills"
            ]

            missing_skills = scores[
                "missing_skills"
            ]
           
            final_score = round(

                (
                    semantic_similarity_score * 0.40 +

                    skills_matching_score * 0.35 +

                    experience_relevance_score * 0.10 +

                    education_alignment_score * 0.10 +


                    publication_score * 0.05

                ),

                2
            )
            semantic_similarity_score = float(
                semantic_similarity_score
            )

            final_score = float(final_score)
            matching_skills = json.dumps(
                    matching_skills
                )

            missing_skills = json.dumps(
                    missing_skills
                )

            
            candidate = CandidateResult(

                candidate_name=resume_data['candidate_name'],

                email=resume_data['email'],

                phone=resume_data['phone'],

                resume_file_path=resume_path,

                resume_text=resume_text,

                semantic_similarity_score=semantic_similarity_score,

                skills_matching_score=skills_matching_score,

                experience_relevance_score=experience_relevance_score,

                education_alignment_score=education_alignment_score,

                certification_score=0,

                publication_score=publication_score,

                final_score=final_score,

                jd_id=jd_id,
                missing_skills=missing_skills,
                matching_skills=matching_skills
            )

            db.add(candidate)

            db.commit()

            db.refresh(candidate)

            processed_candidates.append({

                "candidate_id": candidate.id,

                "candidate_name": resume_data['candidate_name'],

                "final_score": final_score,

                "success": True
            })

        
        rank_candidates(jd_id, db)

        return {
            "success": True,
            "processed_candidates": processed_candidates
        }

    except Exception as e:

        db.rollback()

        return {
            "success": False,
            "error": str(e)
        }

    finally:

        db.close()


def extract_resume_details(resume_text):

    try:

        prompt = PromptTemplate(

            input_variables=["resume"],

            template="""
            You are an ATS resume parser.

            Extract all possible candidate details
            from the resume.

            Return ONLY valid JSON.

            Required JSON format:

            {{
                "candidate_name": "",
                "email": "",
                "phone": "",

                "skills": [],

                "experience_summary": "",

                "education": [],

                "certifications": [],


                "research_papers": [],

                "projects": []
            }}

            Rules:
            - Return only JSON
            - No markdown
            - No explanations
            - If field missing return empty list/string

            Resume:
            {resume}
            """
        )

        chain = prompt | llm

        response = chain.invoke({

            "resume": resume_text

        })

        content = response.content.strip()

        content = content.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        parsed_data = json.loads(content)

        return {

            "success": True,

            "data": parsed_data
        }

    except json.JSONDecodeError:

        return {
            "success": False,
            "error": "Invalid JSON returned by LLM"
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }





def calculate_candidate_scores(

    extracted_jd_data,

    extracted_resume_data

):

    """
    Calculates ATS scores using:
    - LLM reasoning
    - Mathematical weighted scoring

    Returns:
    {
        semantic_similarity_score,
        skills_matching_score,
        experience_relevance_score,
        education_alignment_score,
        publication_score,
        final_score,
        matching_skills,
        missing_skills
    }
    """

    try:

       
        jd_data = extracted_jd_data["data"]

        resume_data = extracted_resume_data["data"]

        
        prompt = PromptTemplate(

            input_variables=[
                "jd",
                "resume"
            ],

            template="""
            You are an advanced ATS scoring engine.

            Compare the job description
            requirements with candidate profile.

            Analyze:
            - technical skill match
            - experience relevance
            - education alignment
            - project relevance
            - publication/research relevance

            Ignore:
            - communication skills
            - leadership
            - generic soft skills

            Return ONLY valid JSON.

            Required JSON format:

            {{
                "jd_required_skills": [],
        "jd_required_years_experience": 0,
        "jd_required_education": "",
        "jd_has_research": false,

        "resume_skills": [],
        "resume_years_experience": 0,
        "resume_education": "",
        "resume_has_research": false,

        "matching_skills": [],
        "missing_skills": [],
        "reasoning": ""
            }}

            Rules:
            
            - Return only JSON
            - No markdown
            - No explanations outside JSON

            JOB DESCRIPTION:
            {jd}

            CANDIDATE PROFILE:
            {resume}
            """
        )

        chain = prompt | llm

        response = chain.invoke({

            "jd": json.dumps(jd_data),

            "resume": json.dumps(resume_data)

        })

        content = response.content.strip()

        
        content = content.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

        llm_scores = json.loads(content)

       
        skills_matching_score = calc_skills_score(
        llm_scores.get("matching_skills", []),
        llm_scores.get("jd_required_skills", [])
    )

        experience_relevance_score = calc_experience_score(
            float(llm_scores.get("resume_years_experience", 0)),
            float(llm_scores.get("jd_required_years_experience", 0))
        )

        education_alignment_score = calc_education_score(
            llm_scores.get("resume_education", ""),
            llm_scores.get("jd_required_education", "")
        )

        publication_score = calc_publication_score(
            llm_scores.get("resume_has_research", False),
            llm_scores.get("jd_has_research", False)
        )

        

        
        return {

            "success": True,

            "data": {

                

                "skills_matching_score":
                    skills_matching_score,

                "experience_relevance_score":
                    experience_relevance_score,

                "education_alignment_score":
                    education_alignment_score,

                "publication_score":
                    publication_score,

                

                "matching_skills":
                    llm_scores.get(
                        "matching_skills",
                        []
                    ),

                "missing_skills":
                    llm_scores.get(
                        "missing_skills",
                        []
                    ),

                "reasoning":
                    llm_scores.get(
                        "reasoning",
                        ""
                    )
            }
        }

    except json.JSONDecodeError:

        return {
            "success": False,
            "error": "Invalid JSON returned by LLM"
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
    




def calc_skills_score(matching: list, required: list) -> float:
    """What % of required skills does candidate have."""
    if not required:
        return 0.0
    return round((len(matching) / len(required)) * 100, 2)


def calc_experience_score(resume_years: float, jd_years: float) -> float:
    """
    Fixed formula:
    - Meets or exceeds required → 100
    - Within 1 year less → 80
    - Within 2 years less → 60
    - Within 3 years less → 40
    - More than 3 years less → 20
    - No experience → 0
    """
    if jd_years == 0:
        return 100.0
    if resume_years <= 0:
        return 0.0

    gap = jd_years - resume_years

    if gap <= 0:
        return 100.0
    elif gap <= 1:
        return 80.0
    elif gap <= 2:
        return 60.0
    elif gap <= 3:
        return 40.0
    else:
        return 20.0


def calc_education_score(resume_edu: str, jd_edu: str) -> float:
    """
    Fixed formula based on degree level.
    PhD > Master > Bachelor > Other
    """
    level = {
        "phd": 4, "doctorate": 4,
        "master": 3, "msc": 3, "mtech": 3, "me": 3,
        "bachelor": 2, "bsc": 2, "btech": 2, "be": 2,
        "diploma": 1, "other": 1
    }

    def get_level(text: str) -> int:
        text = text.lower()
        for key, val in level.items():
            if key in text:
                return val
        return 1

    resume_level = get_level(resume_edu)
    jd_level     = get_level(jd_edu)

    if resume_level >= jd_level:
        return 100.0
    elif resume_level == jd_level - 1:
        return 70.0
    else:
        return 40.0


def calc_publication_score(resume_has: bool, jd_has: bool) -> float:
    """Simple binary — required and has it → 100, else 0 or 50."""
    if not jd_has:
        return 100.0   # not required, no penalty
    if resume_has:
        return 100.0
    return 0.0

def rank_candidates(jd_id, db):

    """
    Assigns rank based on final_score
    for all candidates under same JD
    """

    try:

        candidates = (

            db.query(CandidateResult)

            .filter(
                CandidateResult.jd_id == jd_id
            )

            .order_by(
                CandidateResult.final_score.desc()
            )

            .all()
        )

        
        for index, candidate in enumerate(candidates):

            candidate.rank = index + 1

        
        db.commit()

        return {
            "success": True
        }

    except Exception as e:

        db.rollback()

        return {
            "success": False,
            "error": str(e)
        }