from sqlalchemy import create_engine, text

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker
)

from dotenv import load_dotenv

import os


# =====================================
# LOAD ENV VARIABLES
# =====================================
load_dotenv()


# =====================================
# SUPABASE DATABASE URL
# =====================================
DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


# =====================================
# CREATE ENGINE
# =====================================
engine = create_engine(

    DATABASE_URL,

    connect_args={
        "sslmode": "require"
    }
)


# =====================================
# SESSION
# =====================================
SessionLocal = sessionmaker(

    autocommit=False,

    autoflush=False,

    bind=engine
)


# =====================================
# BASE
# =====================================
Base = declarative_base()


# =====================================
# DATABASE DEPENDENCY
# =====================================
def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# =====================================
# TEST CONNECTION
# =====================================
def test_connection():

    try:

        with engine.connect() as conn:

            conn.execute(
                text("SELECT 1")
            )

        print(
            "Supabase database connected successfully!"
        )

    except Exception as e:

        print(
            f"Database connection failed: {e}"
        )