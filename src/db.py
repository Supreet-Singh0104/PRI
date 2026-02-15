# src/db.py

import mysql.connector
from mysql.connector import errorcode
from typing import Optional, List, Dict
from src.config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DB,
)

def get_raw_connection(database: Optional[str] = None):
    """
    Connect to MySQL. If `database` is None, connect without selecting DB
    (used for creating the DB).
    """
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=database if database else None,
    )
    return conn

def ensure_database():
    """
    Create the project database if it does not exist.
    """
    conn = get_raw_connection()
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` DEFAULT CHARACTER SET 'utf8mb4';")
    cur.close()
    conn.close()

def get_connection():
    """
    Get a connection to the project database (assumes it exists).
    """
    ensure_database()
    conn = get_raw_connection(database=MYSQL_DB)
    return conn

def init_db():
    """
    Create tables if they don't exist.
    """
    ensure_database()
    conn = get_connection()
    cur = conn.cursor()

    # Patients table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INT AUTO_INCREMENT PRIMARY KEY,
        external_id VARCHAR(64) UNIQUE,
        name VARCHAR(255),
        sex ENUM('M','F','O'),
        dob DATE
    ) ENGINE=InnoDB;
    """)

    # Lab tests master
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lab_tests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(32) UNIQUE,
        name VARCHAR(255),
        unit_default VARCHAR(32),
        description TEXT
    ) ENGINE=InnoDB;
    """)

    # Lab results (time-series)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lab_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        patient_id INT NOT NULL,
        test_id INT NOT NULL,
        value DOUBLE NOT NULL,
        unit VARCHAR(32),
        flag ENUM('High','Low','Normal') NULL,
        result_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_lab_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
        CONSTRAINT fk_lab_test FOREIGN KEY (test_id) REFERENCES lab_tests(id)
    ) ENGINE=InnoDB;
    """)

    # Audit Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        patient_id VARCHAR(64),
        report_date DATE,
        abnormal_tests_count INT,
        trends_json JSON,
        escalation_json JSON,
        knowledge_sources_json JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """)

    conn.commit()
    cur.close()
    conn.close()

def insert_patient(external_id: str, name: str, sex: str, dob: str) -> int:
    """
    Insert a patient if not exists; return its ID.
    dob: 'YYYY-MM-DD'
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # Try to fetch existing
    cur.execute("SELECT id FROM patients WHERE external_id = %s;", (external_id,))
    row = cur.fetchone()
    if row:
        patient_id = row["id"]
    else:
        cur.execute(
            """
            INSERT INTO patients (external_id, name, sex, dob)
            VALUES (%s, %s, %s, %s);
            """,
            (external_id, name, sex, dob),
        )
        conn.commit()
        patient_id = cur.lastrowid

    cur.close()
    conn.close()
    return patient_id

def insert_lab_test(code: str, name: str, unit_default: str, description: str = "") -> int:
    """
    Insert a lab test if not exists; return its ID.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id FROM lab_tests WHERE code = %s;", (code,))
    row = cur.fetchone()
    if row:
        test_id = row["id"]
    else:
        cur.execute(
            """
            INSERT INTO lab_tests (code, name, unit_default, description)
            VALUES (%s, %s, %s, %s);
            """,
            (code, name, unit_default, description),
        )
        conn.commit()
        test_id = cur.lastrowid

    cur.close()
    conn.close()
    return test_id

def insert_lab_result(
    patient_id: int,
    test_id: int,
    value: float,
    unit: str,
    flag: str,
    result_date: str,
) -> int:
    """
    Insert a lab result row.
    result_date: 'YYYY-MM-DD'
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO lab_results (patient_id, test_id, value, unit, flag, result_date)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (patient_id, test_id, value, unit, flag, result_date),
    )
    conn.commit()
    row_id = cur.lastrowid

    cur.close()
    conn.close()
    return row_id


def get_patient_id_by_external_id(external_id: str) -> Optional[int]:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM patients WHERE external_id = %s;", (external_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row["id"] if row else None

def fetch_lab_history_for_patient(patient_id: int) -> List[Dict]:
    """
    Returns time-series lab data for a patient, ordered by test code and date.
    Each row: {code, name, value, unit, flag, result_date}
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT
            lt.code,
            lt.name,
            lr.value,
            lr.unit,
            lr.flag,
            lr.result_date
        FROM lab_results lr
        JOIN lab_tests lt ON lr.test_id = lt.id
        WHERE lr.patient_id = %s
        ORDER BY lt.code, lr.result_date;
        """,
        (patient_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def insert_feedback(report_id: str, rating: str):
    """
    Inserts feedback (thumbs up/down) into report_feedback table.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS report_feedback (
        id INT AUTO_INCREMENT PRIMARY KEY,
        report_id VARCHAR(255),
        rating VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """)
    
    cur.execute(
        "INSERT INTO report_feedback (report_id, rating) VALUES (%s, %s);",
        (report_id, rating)
    )
    conn.commit()
    cur.close()
    conn.close()
