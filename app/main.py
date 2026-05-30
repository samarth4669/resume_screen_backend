#######################################IMPORTS##########################################################################
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import test_connection
from app.database import engine
from app.models import Base
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.database import SessionLocal,get_db
from app.models import JobDescription,CandidateResult
from uuid import uuid4
from app.utility import extract_text_from_file,extract_resume_details,calculate_semantic_similarity,jd_data_extract,process_resumes,create_job_description
import os
import shutil
from typing import List

from sqlalchemy.orm import Session
from fastapi import Depends











##################################################################################IMPORTS##########################################################





#####################################################################################INITIAL CONFIGURATION#####################################################
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://resume-screen-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)
UPLOAD_FOLDER = "uploads/jd"
RESUME_UPLOAD_FOLDER = "uploads/resumes"
os.makedirs(RESUME_UPLOAD_FOLDER,exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)





##############################################################################INITIAL CONFIGURATION #################################################################










######################################################################################APIS#############################################################################
@app.on_event("startup")
def startup():
    test_connection()


@app.get("/")
def home():
    return {
        "message": "Resume Screening Backend Running"
    }


@app.post("/analyze")
async def analyze(

    jd_text: str = Form(None),

    jd_file: UploadFile = File(None),

    resume_files: list[UploadFile] = File(None),

):
    print(jd_text,jd_file,resume_files)
    output=create_job_description(UPLOAD_FOLDER,jd_text,jd_file)
    if isinstance(output, JSONResponse):
       return output

    
    print(output['data'])
    
    jd_data=jd_data_extract(output['data']['jd_text'])
    print(jd_data)
    saved_resume_paths = []

    for resume_file in resume_files:

        unique_filename = (
            f"{uuid4()}_{resume_file.filename}"
        )

        resume_path = os.path.join(

            RESUME_UPLOAD_FOLDER,

            unique_filename
        )

        with open(
            resume_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                resume_file.file,
                buffer
            )

        saved_resume_paths.append(
            resume_path
        )
    return process_resumes(saved_resume_paths,output['data']['id'],output['data']['jd_text'],jd_data)    

 
@app.get("/job-descriptions")
def get_job_descriptions(

    db: Session = Depends(get_db)

):

    jds = db.query(

        JobDescription

    ).all()

    result = []

    for jd in jds:

        result.append({

            "id": jd.id,

            "title": jd.title,

            "jd_text": jd.jd_text,

            "jd_file_path": jd.jd_file_path,

            "created_at": jd.created_at,

            "candidate_count": len(
                jd.candidates
            )
        })

    return {

        "success": True,

        "job_descriptions": result
    }








@app.get("/analyze/{jd_id}")
def analyze_candidates(
    jd_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------
    # FETCH CANDIDATES
    # -----------------------------------
    candidates = (
        db.query(CandidateResult)
        .filter(CandidateResult.jd_id == jd_id)
        .order_by(CandidateResult.final_score.desc())
        .all()
    )

    

    # -----------------------------------
    # RESPONSE
    # -----------------------------------
    results = []

    for candidate in candidates:

        results.append({

            "id": candidate.id,

            "name": candidate.candidate_name,

            "email": candidate.email,

            "phone": candidate.phone,

            "resumeText": candidate.resume_text,

            "resumeFile": candidate.resume_file_path,

            "matchScore": round(candidate.final_score, 2),

            "rank": candidate.rank,

            "matchingSkills": (
                candidate.matching_skills.split(",")
                if candidate.matching_skills
                else []
            ),

            "missingSkills": (
                candidate.missing_skills.split(",")
                if candidate.missing_skills
                else []
            ),

            "semanticSimilarityScore":
                candidate.semantic_similarity_score,

            "skillsMatchingScore":
                candidate.skills_matching_score,

            "experienceRelevanceScore":
                candidate.experience_relevance_score,

            "educationAlignmentScore":
                candidate.education_alignment_score,

            "certificationScore":
                candidate.certification_score,

            "publicationScore":
                candidate.publication_score,
        })

    return {
        "success": True,
        "total_candidates": len(results),
        "candidates": results
    }













# test_jd = """
#     We are seeking a highly skilled and experienced Senior Machine Learning Engineer 
# to join our AI Infrastructure team. The ideal candidate will have 7+ years of 
# hands-on experience in designing, building, and deploying large-scale ML systems 
# in production environments.

# Responsibilities:
# - Architect and implement end-to-end ML pipelines using distributed computing frameworks
# - Lead the development of real-time model serving infrastructure handling 10M+ requests/day
# - Collaborate with cross-functional teams including Data Science, DevOps, and Product
# - Optimize model performance through quantization, pruning, and distillation techniques
# - Drive MLOps best practices including CI/CD for ML, model versioning, and drift monitoring

# Requirements:
# - PhD or Master's degree in Computer Science, Machine Learning, or related field
# - Strong proficiency in Python, C++, and CUDA programming
# - Deep expertise in frameworks: PyTorch, TensorFlow, JAX, Triton
# - Experience with Kubernetes, Docker, and cloud platforms (AWS SageMaker, GCP Vertex AI)
# - Hands-on experience with LLMs, transformer architectures, and fine-tuning techniques (LoRA, QLoRA)
# - Proficiency in distributed training frameworks: DeepSpeed, FSDP, Megatron-LM
# - Experience with vector databases (Pinecone, Weaviate, Qdrant) and RAG pipelines
# - Strong understanding of data structures, algorithms, and system design
# - Excellent communication skills with ability to present to C-suite stakeholders

# Nice to have:
# - Published research in top-tier ML conferences (NeurIPS, ICML, ICLR)
# - Experience with RLHF and alignment techniques
# - Contributions to open-source ML projects
#     """
    
# result = generate_jd_title(test_jd)
# print("Generated Title:", result)