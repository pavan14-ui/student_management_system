"""
Database layer for Student Management System.
Requires SQL Server Express (default instance: localhost\\SQLEXPRESS)
and Microsoft ODBC Driver 17 or 18 for SQL Server.
"""

import pyodbc
from collections import namedtuple

Student = namedtuple("Student", "student_id name age course email")


SERVER = r"localhost\SQLEXPRESS"
DATABASE = "StudentManagementDB"


def _connection_string(database="master", driver="ODBC Driver 17 for SQL Server"):
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={SERVER};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


def connect_to_server():
    """Connect using an installed SQL Server ODBC driver."""
    errors = []
    for driver in (
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 18 for SQL Server",
    ):
        try:
            return pyodbc.connect(_connection_string("master", driver), timeout=5)
        except pyodbc.Error as exc:
            errors.append(f"{driver}: {exc}")
    raise RuntimeError(
        "Could not connect to SQL Server. Check that SQL Server Express is running "
        "and that the ODBC Driver 17 or 18 is installed.\n" + "\n".join(errors)
    )


class Database:
    def __init__(self):
        self.connection = None
        self.driver = None
        self.connect()

    def connect(self):
        errors = []
        for driver in (
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 18 for SQL Server",
        ):
            try:
                # First connect to master so the database can be created if needed.
                master_conn = pyodbc.connect(
                    _connection_string("master", driver), timeout=5
                )
                master_conn.autocommit = True
                master_cursor = master_conn.cursor()
                master_cursor.execute(
                    "IF DB_ID(?) IS NULL EXEC('CREATE DATABASE StudentManagementDB')",
                    DATABASE,
                )
                master_cursor.close()
                master_conn.close()

                self.connection = pyodbc.connect(
                    _connection_string(DATABASE, driver), timeout=5
                )
                self.driver = driver
                self._create_tables()
                print(f"Connected to SQL Server database: {DATABASE}")
                return
            except pyodbc.Error as exc:
                errors.append(f"{driver}: {exc}")
                try:
                    master_conn.close()
                except Exception:
                    pass
        raise RuntimeError(
            "Unable to connect to SQL Server or create the database.\n"
            "Check SERVER in database.py, SQL Server Express service, Windows "
            "authentication permissions, and ODBC Driver installation.\n"
            + "\n".join(errors)
        )

    def _create_tables(self):
        cursor = self.connection.cursor()
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
                        FOREIGN KEY (student_id) REFERENCES dbo.students(student_id)
                        ON DELETE CASCADE,
                    CONSTRAINT UQ_student_subject UNIQUE (student_id, subject)
                )
            END
        """)
        self.connection.commit()
        cursor.close()

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query, params=()):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def list_students(self):
        cursor = self.execute("""
            SELECT student_id, name, age, course, email
            FROM dbo.students ORDER BY student_id
        """)
        rows = [Student(*row) for row in cursor.fetchall()]
        cursor.close()
        return rows

    def get_student_by_name(self, name):
        cursor = self.execute("""
            SELECT student_id, name, age, course, email
            FROM dbo.students WHERE LOWER(name) = LOWER(?)
        """, (name,))
        row = cursor.fetchone()
        cursor.close()
        return Student(*row) if row else None

    def get_student_by_id(self, student_id):
        cursor = self.execute("""
            SELECT student_id, name, age, course, email
            FROM dbo.students WHERE student_id = ?
        """, (student_id,))
        row = cursor.fetchone()
        cursor.close()
        return Student(*row) if row else None

    def add_student(self, name, age, course, email, marks):
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO dbo.students (name, age, course, email)
                OUTPUT INSERTED.student_id
                VALUES (?, ?, ?, ?)
            """, (name, age, course, email or None))
            student_id = cursor.fetchone()[0]
            for subject, mark in marks.items():
                cursor.execute("""
                    INSERT INTO dbo.student_marks (student_id, subject, mark)
                    VALUES (?, ?, ?)
                """, (student_id, subject, mark))
            self.connection.commit()
            return student_id
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def get_marks(self, student_id):
        cursor = self.execute("""
            SELECT subject, mark FROM dbo.student_marks
            WHERE student_id = ? ORDER BY subject
        """, (student_id,))
        rows = cursor.fetchall()
        cursor.close()
        return {row[0]: float(row[1]) for row in rows}

    def replace_marks(self, student_id, marks):
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "DELETE FROM dbo.student_marks WHERE student_id = ?",
                (student_id,),
            )
            for subject, mark in marks.items():
                cursor.execute("""
                    INSERT INTO dbo.student_marks (student_id, subject, mark)
                    VALUES (?, ?, ?)
                """, (student_id, subject, mark))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def update_student_field(self, student_id, field, value):
        allowed = {"name", "age", "course", "email"}
        if field not in allowed:
            raise ValueError("Invalid student field.")
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f"UPDATE dbo.students SET {field} = ? WHERE student_id = ?",
                (value, student_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def delete_student(self, student_id):
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "DELETE FROM dbo.students WHERE student_id = ?", (student_id,)
            )
            deleted = cursor.rowcount > 0
            self.connection.commit()
            return deleted
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()
