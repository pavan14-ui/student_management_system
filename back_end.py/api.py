"""FastAPI backend for the Student Management System (SQL Server)."""
import math
import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SERVER = r"localhost\SQLEXPRESS"
DATABASE = "StudentManagementDB"
DRIVERS = ("ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server")
SUBJECTS = ["python", "java", "os", "dbms", "physics"]

app = FastAPI(title="Student Management System API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


def _connect_with_driver(driver, database):
    """Open SQL Server with the selected installed ODBC driver."""
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(connection_string, timeout=5)


def _ensure_database_exists(driver):
    """Create the project database if this is a fresh installation."""
    connection = _connect_with_driver(driver, "master")
    connection.autocommit = True

    try:
        cursor = connection.cursor()
        cursor.execute(
            "IF DB_ID(?) IS NULL EXEC('CREATE DATABASE StudentManagementDB')",
            DATABASE,
        )
        cursor.close()
    finally:
        connection.close()


def _ensure_tables(connection):
    """Create required tables without deleting any existing records."""
    cursor = connection.cursor()
    cursor.execute("""
        IF OBJECT_ID('dbo.students', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.students (
                student_id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL UNIQUE,
                age INT NOT NULL,
                course NVARCHAR(100) NOT NULL,
                email NVARCHAR(255) NULL
            )
        END
    """)
    cursor.execute("""
        IF OBJECT_ID('dbo.student_marks', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.student_marks (
                mark_id INT IDENTITY(1,1) PRIMARY KEY,
                student_id INT NOT NULL,
                subject NVARCHAR(100) NOT NULL,
                mark FLOAT NOT NULL CHECK (mark >= 0 AND mark <= 100),
                CONSTRAINT FK_student_marks_students
                    FOREIGN KEY (student_id)
                    REFERENCES dbo.students(student_id)
                    ON DELETE CASCADE,
                CONSTRAINT UQ_student_subject UNIQUE (student_id, subject)
            )
        END
    """)
    connection.commit()
    cursor.close()


def get_connection():
    """Connect to SQL Server and ensure the required schema is available."""
    errors = []

    for driver in DRIVERS:
        try:
            try:
                connection = _connect_with_driver(driver, DATABASE)
            except pyodbc.Error:
                _ensure_database_exists(driver)
                connection = _connect_with_driver(driver, DATABASE)

            _ensure_tables(connection)
            return connection
        except pyodbc.Error as error:
            errors.append(f"{driver}: {error}")

    raise HTTPException(
        status_code=503,
        detail=(
            "Could not connect to SQL Server. Check SQL Server Express, "
            "the ODBC driver, and Windows authentication. " + " | ".join(errors)
        ),
    )


class StudentPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=5, le=100)
    course: str = Field(min_length=1, max_length=100)
    email: str = ""
    marks: dict[str, float] = Field(default_factory=dict)

class StudentUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=5, le=100)
    course: str = Field(min_length=1, max_length=100)
    email: str = ""

class MarksPayload(BaseModel):
    marks: dict[str, float]


def validate_marks(marks, require_all=True):
    normalized = {str(k).strip().lower(): float(v) for k, v in marks.items()}
    if require_all and set(normalized) != set(SUBJECTS):
        raise HTTPException(status_code=400, detail=f"Provide marks for all five subjects: {', '.join(SUBJECTS)}")
    if any(not math.isfinite(v) or v < 0 or v > 100 for v in normalized.values()):
        raise HTTPException(status_code=400, detail="Marks must be numbers between 0 and 100.")
    unknown = set(normalized) - set(SUBJECTS)
    if unknown:
        raise HTTPException(status_code=400, detail="Unknown subjects: " + ", ".join(sorted(unknown)))
    return normalized


def fetch_marks(cursor, student_id):
    cursor.execute("SELECT subject, mark FROM dbo.student_marks WHERE student_id = ? ORDER BY subject", (student_id,))
    return {str(row[0]).lower(): float(row[1]) for row in cursor.fetchall()}

@app.get("/")
def home():
    return {"message": "Student Management System API is running", "subjects": SUBJECTS}

@app.get("/students")
def list_students():
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT student_id, name, age, course, email FROM dbo.students ORDER BY student_id")
        records = []
        for row in cur.fetchall():
            records.append({"student_id": row[0], "name": row[1], "age": row[2], "course": row[3],
                            "email": row[4] or "", "marks": fetch_marks(cur, row[0])})
        return {"students": records}
    finally:
        cur.close(); conn.close()

@app.get("/students/{student_id}")
def get_student(student_id: int):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT student_id, name, age, course, email FROM dbo.students WHERE student_id = ?", (student_id,))
        row = cur.fetchone()
        if not row: raise HTTPException(status_code=404, detail="Student not found")
        return {"student_id": row[0], "name": row[1], "age": row[2], "course": row[3], "email": row[4] or "", "marks": fetch_marks(cur, student_id)}
    finally:
        cur.close(); conn.close()

@app.get("/students/{student_id}/marks")
def get_student_marks(student_id: int):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT student_id FROM dbo.students WHERE student_id = ?", (student_id,))
        if not cur.fetchone(): raise HTTPException(status_code=404, detail="Student not found")
        return {"student_id": student_id, "marks": fetch_marks(cur, student_id)}
    finally:
        cur.close(); conn.close()

@app.post("/students", status_code=201)
def add_student(payload: StudentPayload):
    marks = validate_marks(payload.marks)
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO dbo.students (name, age, course, email) OUTPUT INSERTED.student_id VALUES (?, ?, ?, ?)",
                    (payload.name.strip(), payload.age, payload.course.strip(), payload.email.strip() or None))
        student_id = int(cur.fetchone()[0])
        for subject in SUBJECTS:
            cur.execute("INSERT INTO dbo.student_marks (student_id, subject, mark) VALUES (?, ?, ?)", (student_id, subject, marks[subject]))
        conn.commit()
        return {"message": "Student added successfully", "student_id": student_id}
    except pyodbc.IntegrityError:
        conn.rollback(); raise HTTPException(status_code=409, detail="A student with that name already exists")
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

@app.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdate):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("UPDATE dbo.students SET name=?, age=?, course=?, email=? WHERE student_id=?",
                    (payload.name.strip(), payload.age, payload.course.strip(), payload.email.strip() or None, student_id))
        if cur.rowcount == 0: conn.rollback(); raise HTTPException(status_code=404, detail="Student not found")
        conn.commit(); return {"message": "Student details updated", "student_id": student_id}
    except pyodbc.IntegrityError:
        conn.rollback(); raise HTTPException(status_code=409, detail="Another student already uses that name")
    except Exception:
        if conn: conn.rollback()
        raise
    finally:
        cur.close(); conn.close()

@app.put("/students/{student_id}/marks")
def update_marks(student_id: int, payload: MarksPayload):
    marks = validate_marks(payload.marks)
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT student_id FROM dbo.students WHERE student_id=?", (student_id,))
        if not cur.fetchone(): raise HTTPException(status_code=404, detail="Student not found")
        cur.execute("DELETE FROM dbo.student_marks WHERE student_id=?", (student_id,))
        for subject in SUBJECTS:
            cur.execute("INSERT INTO dbo.student_marks (student_id, subject, mark) VALUES (?, ?, ?)", (student_id, subject, marks[subject]))
        conn.commit(); return {"message": "Marks updated", "student_id": student_id, "marks": marks}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()

@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM dbo.students WHERE student_id=?", (student_id,))
        if cur.rowcount == 0: raise HTTPException(status_code=404, detail="Student not found")
        conn.commit(); return {"message": "Student deleted", "student_id": student_id}
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close(); conn.close()
