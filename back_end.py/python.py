"""
Student Management System - SQL Server edition.
All 16 menu options use the database layer in database.py.
"""

import pyodbc
from database import Database


SUBJECTS = ["python", "java", "os", "dbms", "physics"]


class Solution:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def get_name():
        while True:
            name = input("Enter student name: ").strip()
            if name and all(char.isalpha() or char.isspace() for char in name):
                return name
            print("Please enter a valid name (letters and spaces only).")

    @staticmethod
    def get_age():
        while True:
            try:
                age = int(input("Enter age (5-100): "))
                if 5 <= age <= 100:
                    return age
                print("Age must be between 5 and 100.")
            except ValueError:
                print("Please enter a whole number.")

    @staticmethod
    def get_course():
        while True:
            course = input("Enter course: ").strip()
            if course:
                return course
            print("Course cannot be empty.")

    @staticmethod
    def get_email(optional=True):
        while True:
            email = input("Enter email address (leave blank if none): ").strip()
            if not email and optional:
                return ""
            if "@" in email and "." in email.rsplit("@", 1)[-1]:
                return email
            print("Please enter a valid email address, or leave it blank.")

    @staticmethod
    def get_marks():
        marks = {}
        for subject in SUBJECTS:
            while True:
                try:
                    mark = float(input(f"Enter marks for {subject} (0-100): "))
                    if 0 <= mark <= 100:
                        marks[subject] = mark
                        break
                    print("Marks must be between 0 and 100.")
                except ValueError:
                    print("Please enter a valid number.")
        return marks

    @staticmethod
    def get_student_id():
        while True:
            try:
                student_id = int(input("Enter student ID: "))
                if student_id > 0:
                    return student_id
                print("ID must be a positive number.")
            except ValueError:
                print("Please enter a valid whole-number ID.")

    def find_student(self, name):
        return self.db.get_student_by_name(name)

    def add_student(self):
        try:
            count = int(input("Enter number of students to add: "))
            if count <= 0:
                print("Enter a positive number.")
                return
        except ValueError:
            print("Please enter a valid whole number.")
            return

        for index in range(count):
            print(f"\n===== Student {index + 1} of {count} =====")
            name = self.get_name()
            if self.find_student(name):
                print("A student with that name already exists. This entry was skipped.")
                continue
            age = self.get_age()
            course = self.get_course()
            email = self.get_email()
            marks = self.get_marks()
            try:
                student_id = self.db.add_student(name, age, course, email, marks)
                print(f"Student added successfully. Student ID: {student_id}")
            except pyodbc.IntegrityError:
                print("Could not add student: a student with that name may already exist.")
            except pyodbc.Error as exc:
                print(f"Database error while adding student: {exc}")

    def view_students(self):
        students = self.db.list_students()

        if not students:
            print("No students found.")
            return

        print("\n" + "=" * 150)
        print(
            f"{'ID':<5}{'Name':<18}{'Age':<6}"
            f"{'Course':<12}{'Email':<28}Marks"
        )
        print("-" * 150)

        for student in students:
            marks = self.db.get_marks(student.student_id)

            marks_text = ", ".join(
                f"{subject.upper()}: {mark:g}"
                for subject, mark in marks.items()) or "No marks"

            print(
                f"{student.student_id:<5}"
                f"{student.name[:16]:<18}"
                f"{student.age:<6}"
                f"{student.course[:10]:<12}"
                f"{(student.email or '')[:26]:<28}"
                f"{marks_text}"
            )

        print("=" * 150)

    def search_student(self):
        name = self.get_name()
        student = self.find_student(name)
        if not student:
            print("Student not found.")
            return
        self.print_student(student)

    def print_student(self, student):
        print(f"\nStudent ID: {student.student_id}")
        print(f"Name: {student.name}")
        print(f"Age: {student.age}")
        print(f"Course: {student.course}")
        print(f"Email: {student.email or 'Not provided'}")
        marks = self.db.get_marks(student.student_id)
        if marks:
            print("Marks:")
            for subject, mark in marks.items():
                print(f"  {subject}: {mark:g}")
        else:
            print("No marks available.")

    def update_student(self):
        student = self.db.get_student_by_id(self.get_student_id())
        if not student:
            print("Student not found.")
            return
        self.print_student(student)
        print("\nWhat do you want to update?")
        print("1. Name")
        print("2. Age")
        print("3. Course")
        print("4. Marks")
        print("5. Email")
        choice = input("Enter your choice (1-5): ").strip()
        try:
            if choice == "1":
                new_name = self.get_name()
                existing = self.find_student(new_name)
                if existing and existing.student_id != student.student_id:
                    print("Another student with this name already exists.")
                    return
                self.db.update_student_field(student.student_id, "name", new_name)
            elif choice == "2":
                self.db.update_student_field(student.student_id, "age", self.get_age())
            elif choice == "3":
                self.db.update_student_field(student.student_id, "course", self.get_course())
            elif choice == "4":
                self.db.replace_marks(student.student_id, self.get_marks())
            elif choice == "5":
                self.db.update_student_field(student.student_id, "email", self.get_email())
            else:
                print("Invalid choice.")
                return
            print("Student successfully updated.")
        except pyodbc.Error as exc:
            print(f"Database error while updating student: {exc}")

    def delete_student(self):
        student = self.db.get_student_by_id(self.get_student_id())
        if not student:
            print("Student not found.")
            return
        confirm = input(f"Are you sure you want to delete {student.name}? (yes/no): ").strip().lower()
        if confirm == "yes":
            if self.db.delete_student(student.student_id):
                print("Student deleted successfully.")
            else:
                print("Student was not found.")
        else:
            print("Delete cancelled.")

    def view_student_marks(self):
        student = self.db.get_student_by_id(self.get_student_id())
        if not student:
            print("Student not found.")
            return
        marks = self.db.get_marks(student.student_id)
        print(f"\nMarks for {student.name}:")
        if not marks:
            print("No marks available.")
            return
        for subject, mark in marks.items():
            print(f"{subject}: {mark:g}")
        print("Total marks:", sum(marks.values()))
        print("Average marks:", round(sum(marks.values()) / len(marks), 2))

    def update_subject_marks(self):
        student = self.db.get_student_by_id(self.get_student_id())
        if not student:
            print("Student not found.")
            return
        marks = self.db.get_marks(student.student_id)
        if not marks:
            print("No marks available. Use Add Marks first.")
            return
        print("Subjects:", ", ".join(marks.keys()))
        subject_input = input("Enter subject to update: ").strip().lower()
        actual_subject = next((s for s in marks if s.lower() == subject_input), None)
        if actual_subject is None:
            print("Subject not found.")
            return
        while True:
            try:
                mark = float(input("Enter new marks (0-100): "))
                if 0 <= mark <= 100:
                    marks[actual_subject] = mark
                    self.db.replace_marks(student.student_id, marks)
                    print("Marks updated successfully.")
                    return
                print("Marks must be between 0 and 100.")
            except ValueError:
                print("Please enter a valid number.")

    def add_marks(self):
        student = self.db.get_student_by_id(self.get_student_id())
        if not student:
            print("Student not found.")
            return
        marks = self.get_marks()
        self.db.replace_marks(student.student_id, marks)
        print("Marks saved successfully.")

    @staticmethod
    def calculate_grade(average):
        if average >= 90:
            return "A+"
        if average >= 80:
            return "A"
        if average >= 70:
            return "B"
        if average >= 60:
            return "C"
        if average >= 50:
            return "D"
        return "F"

    def _students_with_marks(self):
        result = []
        for student in self.db.list_students():
            marks = self.db.get_marks(student.student_id)
            if marks:
                average = sum(marks.values()) / len(marks)
                result.append({
                    "student": student,
                    "marks": marks,
                    "total": sum(marks.values()),
                    "average": average,
                    "grade": self.calculate_grade(average),
                })
        return result

    
    def student_statistics(self):
        students = self.db.list_students()

        if not students:
            print("No students found.")
            return

        total_students = len(students)
        all_marks = []

        for student in students:
            marks = self.db.get_marks(student.student_id)
            all_marks.extend(marks.values())

        print("\n===== STUDENT STATISTICS =====")
        print("Total number of students:", total_students)

        if not all_marks:
            print("No marks available.")
            return

        average = sum(all_marks) / len(all_marks)
        highest = max(all_marks)
        lowest = min(all_marks)

        print("Total marks entered:", len(all_marks))
        print("Average marks:", round(average, 2))
        print("Highest marks:", highest)
        print("Lowest marks:", lowest)


    def subject_wise_topper(self):
        students = self.db.list_students()
        subjects = sorted({subject for s in students for subject in self.db.get_marks(s.student_id)})
        if not subjects:
            print("No marks available.")
            return
        print("\n==== SUBJECT-WISE TOPPER ====")
        for subject in subjects:
            candidates = []
            for student in students:
                marks = self.db.get_marks(student.student_id)
                if subject in marks:
                    candidates.append((student, marks[subject]))
            topper, mark = max(candidates, key=lambda item: item[1])
            print(f"{subject}: {topper.name} - {mark:g}")

    def passed_or_fail(self):
        students = self.db.list_students()
        if not students:
            print("No students found.")
            return
        passed = failed = 0
        for student in students:
            marks = self.db.get_marks(student.student_id)
            if marks and all(mark >= 40 for mark in marks.values()):
                print(f"{student.name} --> PASS")
                passed += 1
            else:
                print(f"{student.name} --> FAIL (no marks or one/more marks below 40)")
                failed += 1
        print("Number of students passed:", passed)
        print("Number of students failed:", failed)

    def grade_calculate(self):
        records = self._students_with_marks()
        if not records:
            print("No student marks available.")
            return
        for record in records:
            print(f"\nStudent: {record['student'].name}")
            print("Total marks:", round(record["total"], 2))
            print("Average marks:", round(record["average"], 2))
            print("Grade:", record["grade"])

    def find_students_by_grade(self):
        grade = input("Enter grade (A+, A, B, C, D, F): ").strip().upper()
        if grade not in {"A+", "A", "B", "C", "D", "F"}:
            print("Invalid grade.")
            return
        found = False
        for record in self._students_with_marks():
            if record["grade"] == grade:
                print(f"{record['student'].name} — Average: {record['average']:.2f}, Grade: {grade}")
                found = True
        if not found:
            print("No students found with this grade.")

    def student_rank_wise(self):
        students = self.db.list_students()
        if not students:
            print("No students found.")
            return
        ranks = []
        for student in students:
            marks = self.db.get_marks(student.student_id)
            ranks.append((student.name, sum(marks.values()), bool(marks)))
        ranks.sort(key=lambda item: item[1], reverse=True)
        print("\n==== STUDENT RANK LIST (total marks) ====")
        for rank, (name, total, has_marks) in enumerate(ranks, start=1):
            suffix = "" if has_marks else " (no marks)"
            print(f"{rank}. {name} --> Total: {total:g}{suffix}")

    def subject_performance(self):
        students = self.db.list_students()
        subjects = sorted({subject for s in students for subject in self.db.get_marks(s.student_id)})
        if not subjects:
            print("No marks available.")
            return
        print("\n===== SUBJECT PERFORMANCE =====")
        for subject in subjects:
            marks = []
            for student in students:
                student_marks = self.db.get_marks(student.student_id)
                if subject in student_marks:
                    marks.append(student_marks[subject])
            if marks:
                print(f"{subject}: Average: {sum(marks) / len(marks):.2f} ({len(marks)} student(s))")

    @staticmethod
    def show_menu():
        print("\n" + "=" * 42)
        print("       STUDENT MANAGEMENT SYSTEM")
        print("=" * 42)
        print("1.  Add Student")
        print("2.  View Students")
        print("3.  Search Student")
        print("4.  Update Student")
        print("5.  Delete Student")
        print("6.  Check Student Statistics")
        print("7.  View Student Marks")
        print("8.  Update Subject Marks")
        print("9.  Subject-wise Topper")
        print("10. Passed or Failed")
        print("11. Grade Calculation")
        print("12. Student Rank-wise")
        print("13. Find Students by Grade")
        print("14. Subject Performance")
        print("15. Add Marks")
        print("16. Exit")
        print("=" * 42)


def main():
    db = None
    try:
        db = Database()
        app = Solution(db)
        actions = {
            "1": app.add_student,
            "2": app.view_students,
            "3": app.search_student,
            "4": app.update_student,
            "5": app.delete_student,
            "6": app.student_statistics,
            "7": app.view_student_marks,
            "8": app.update_subject_marks,
            "9": app.subject_wise_topper,
            "10": app.passed_or_fail,
            "11": app.grade_calculate,
            "12": app.student_rank_wise,
            "13": app.find_students_by_grade,
            "14": app.subject_performance,
            "15": app.add_marks,
        }

        while True:
            app.show_menu()
            choice = input("Enter your choice (1-16): ").strip()
            if choice == "16":
                print("Thank you for using Student Management System.")
                break
            action = actions.get(choice)
            if action is None:
                print("Invalid choice. Please enter a number from 1 to 16.")
                continue
            try:
                action()
            except pyodbc.Error as exc:
                print(f"Database operation failed: {exc}")
            except (ValueError, TypeError) as exc:
                print(f"Invalid input: {exc}")
    except (RuntimeError, pyodbc.Error) as exc:
        print("\nCould not start the Student Management System.")
        print(exc)
    except (EOFError, KeyboardInterrupt):
        print("\nProgram interrupted.")
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    main()
