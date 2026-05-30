from sqlalchemy import Column, Integer, String, Text, TIMESTAMP,Float,ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base

class JobDescription(Base):

    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    jd_text = Column(Text, nullable=False)

    jd_file_path = Column(String, nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )
    candidates = relationship(
        "CandidateResult",
        back_populates="job_description"
    )



class CandidateResult(Base):

    __tablename__ = "candidate_results"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # -----------------------------------
    # BASIC INFO
    # -----------------------------------
    candidate_name = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        nullable=True
    )

    phone = Column(
        String,
        nullable=True
    )

    # -----------------------------------
    # RESUME
    # -----------------------------------
    resume_file_path = Column(
        String,
        nullable=False
    )

    resume_text = Column(
        Text,
        nullable=False
    )

    # -----------------------------------
    # MATCHING DETAILS
    # -----------------------------------
    matching_skills = Column(
        Text,
        nullable=True
    )

    missing_skills = Column(
        Text,
        nullable=True
    )

    # -----------------------------------
    # AI SCORES
    # -----------------------------------
    semantic_similarity_score = Column(
        Float,
        default=0
    )

    skills_matching_score = Column(
        Float,
        default=0
    )

    experience_relevance_score = Column(
        Float,
        default=0
    )

    education_alignment_score = Column(
        Float,
        default=0
    )

    certification_score = Column(
        Float,
        default=0
    )

    publication_score = Column(
        Float,
        default=0
    )

    # -----------------------------------
    # FINAL SCORE
    # -----------------------------------
    final_score = Column(
        Float,
        default=0
    )

    rank = Column(
        Integer,
        nullable=True
    )

    # -----------------------------------
    # FOREIGN KEY
    # -----------------------------------
    jd_id = Column(
        Integer,
        ForeignKey("job_descriptions.id")
    )

    # Relationship
    job_description = relationship(
        "JobDescription",
        back_populates="candidates"
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )