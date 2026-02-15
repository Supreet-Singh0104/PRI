
from typing import Dict, Any, Optional
from src.db import get_connection

def create_profile_table_if_not_exists():
    """
    Creates the patient_profiles table if it does not exist.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS patient_profiles (
                patient_id VARCHAR(255) PRIMARY KEY,
                medications TEXT,
                medical_history TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            """)
        conn.commit()
    finally:
        conn.close()

def get_profile(patient_id: str) -> Dict[str, str]:
    """
    Retrieves the profile (medications, history) for a given patient_id.
    Returns a dict with empty strings if not found.
    """
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(
                "SELECT medications, medical_history FROM patient_profiles WHERE patient_id = %s",
                (patient_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "medications": row["medications"] or "",
                    "medical_history": row["medical_history"] or ""
                }
    finally:
        conn.close()
    
    return {"medications": "", "medical_history": ""}

def save_profile(patient_id: str, medications: str, medical_history: str):
    """
    Upserts the patient profile.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO patient_profiles (patient_id, medications, medical_history)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    medications = VALUES(medications),
                    medical_history = VALUES(medical_history)
                """,
                (patient_id, medications, medical_history)
            )
        conn.commit()
    finally:
        conn.close()
