// Student Management System - website logic
// The API connects this page to SQL Server.

const API_URL = "http://127.0.0.1:8000";
const SUBJECTS = ["python", "java", "os", "dbms", "physics"];

let students = [];
let selectedStudentId = null;

function getElement(id) {
    return document.getElementById(id);
}

function showMessage(message, isError = false) {
    const messageBox = getElement("message");
    messageBox.textContent = message;
    messageBox.className = isError ? "message error" : "message success";
}

function toNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
}

function getMarks(student) {
    const marks = {};

    SUBJECTS.forEach(function (subject) {
        marks[subject] = toNumber(student.marks?.[subject]);
    });

    return marks;
}

function getTotal(student) {
    return Object.values(getMarks(student)).reduce(function (total, mark) {
        return total + mark;
    }, 0);
}

function getAverage(student) {
    return getTotal(student) / SUBJECTS.length;
}

function getGrade(average) {
    if (average >= 90) return "A+";
    if (average >= 80) return "A";
    if (average >= 70) return "B";
    if (average >= 60) return "C";
    if (average >= 50) return "D";
    return "F";
}

function hasPassed(student) {
    const marks = getMarks(student);
    return SUBJECTS.every(function (subject) {
        return marks[subject] >= 40;
    });
}

async function apiRequest(path, options = {}) {
    let response;

    try {
        response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });
    } catch (error) {
        throw new Error(
            "Cannot connect to the API. Start it with: " +
            "python -m uvicorn api:app --reload"
        );
    }

    let result = {};

    try {
        result = await response.json();
    } catch (error) {
        // The server may return an empty response when something goes wrong.
    }

    if (!response.ok) {
        throw new Error(result.detail || `Request failed (${response.status}).`);
    }

    return result;
}

async function loadStudents() {
    try {
        const result = await apiRequest("/students");
        students = Array.isArray(result.students) ? result.students : [];
        renderAll();
        showMessage(`Loaded ${students.length} student(s) from SQL Server.`);
    } catch (error) {
        showMessage(
            `${error.message} Check that SQL Server and the API are running.`,
            true
        );
    }
}

function renderAll() {
    renderStudents();
    renderDashboard();
    renderToppers();
    renderRankings();
    renderPassFailResults();
    renderGrades();
    renderSubjectPerformance();
    renderStatistics();
}

function addCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value ?? "";
    row.appendChild(cell);
    return cell;
}

function renderStudents() {
    const tableBody = getElement("studentTable");
    const searchText = getElement("search").value.trim().toLowerCase();
    tableBody.innerHTML = "";

    const filteredStudents = students.filter(function (student) {
        const values = [student.student_id, student.name, student.course, student.email];
        return values.some(function (value) {
            return String(value || "").toLowerCase().includes(searchText);
        });
    });

    if (filteredStudents.length === 0) {
        const row = tableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 15;
        cell.textContent = "No students found.";
        return;
    }

    filteredStudents.forEach(function (student) {
        const row = tableBody.insertRow();
        const marks = getMarks(student);
        const total = getTotal(student);
        const average = getAverage(student);

        addCell(row, student.student_id);
        addCell(row, student.name);
        addCell(row, student.age);
        addCell(row, student.course);
        addCell(row, student.email || "");

        SUBJECTS.forEach(function (subject) {
            addCell(row, marks[subject]);
        });

        addCell(row, total.toFixed(2));
        addCell(row, average.toFixed(2));
        addCell(row, getGrade(average));

        const resultCell = addCell(row, hasPassed(student) ? "PASS" : "FAIL");
        resultCell.className = hasPassed(student) ? "pass" : "fail";

        const actionsCell = row.insertCell();
        const editButton = document.createElement("button");
        editButton.textContent = "Edit";
        editButton.className = "small";
        editButton.addEventListener("click", function () {
            fillForm(student);
        });

        const deleteButton = document.createElement("button");
        deleteButton.textContent = "Delete";
        deleteButton.className = "small danger";
        deleteButton.addEventListener("click", function () {
            deleteStudent(student.student_id);
        });

        actionsCell.append(editButton, deleteButton);
    });
}

function renderDashboard() {
    getElement("totalStudents").textContent = students.length;

    const courses = students
        .map(function (student) {
            return (student.course || "").trim().toLowerCase();
        })
        .filter(Boolean);

    getElement("totalCourses").textContent = new Set(courses).size;

    const average = students.length
        ? students.reduce(function (sum, student) {
            return sum + getAverage(student);
        }, 0) / students.length
        : 0;

    getElement("classAverage").textContent = average.toFixed(2);
    getElement("passedCount").textContent = students.filter(hasPassed).length;
    getElement("failedCount").textContent = students.filter(function (student) {
        return !hasPassed(student);
    }).length;
}

function renderToppers() {
    const tableBody = getElement("topperTable");
    tableBody.innerHTML = "";

    if (students.length === 0) {
        const row = tableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 3;
        cell.textContent = "No topper data available.";
        return;
    }

    SUBJECTS.forEach(function (subject) {
        const highestMark = Math.max(...students.map(function (student) {
            return getMarks(student)[subject];
        }));

        students.forEach(function (student) {
            if (getMarks(student)[subject] !== highestMark) return;

            const row = tableBody.insertRow();
            addCell(row, subject.toUpperCase());
            addCell(row, student.name);
            addCell(row, highestMark);
        });
    });
}

function renderRankings() {
    const tableBody = getElement("rankTable");
    tableBody.innerHTML = "";

    [...students]
        .sort(function (first, second) {
            return getTotal(second) - getTotal(first);
        })
        .forEach(function (student, index) {
            const row = tableBody.insertRow();
            addCell(row, index + 1);
            addCell(row, student.name);
            addCell(row, getTotal(student).toFixed(2));
            addCell(row, getAverage(student).toFixed(2));
            addCell(row, getGrade(getAverage(student)));
        });
}

function renderPassFailResults() {
    const tableBody = getElement("passFailTable");
    tableBody.innerHTML = "";

    students.forEach(function (student) {
        const row = tableBody.insertRow();
        const passed = hasPassed(student);

        addCell(row, student.name);
        addCell(row, getTotal(student).toFixed(2));
        addCell(row, getAverage(student).toFixed(2));

        const resultCell = addCell(row, passed ? "PASS" : "FAIL");
        resultCell.className = passed ? "pass" : "fail";
    });
}

function renderGrades() {
    const tableBody = getElement("gradeTable");
    const selectedGrade = getElement("gradeFilter").value;
    tableBody.innerHTML = "";

    const filteredStudents = students.filter(function (student) {
        return !selectedGrade || getGrade(getAverage(student)) === selectedGrade;
    });

    filteredStudents.forEach(function (student) {
        const row = tableBody.insertRow();
        addCell(row, student.name);
        addCell(row, getAverage(student).toFixed(2));
        addCell(row, getGrade(getAverage(student)));
    });

    if (filteredStudents.length === 0) {
        const row = tableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 3;
        cell.textContent = "No students match this grade.";
    }
}

function renderSubjectPerformance() {
    const tableBody = getElement("subjectTable");
    tableBody.innerHTML = "";

    SUBJECTS.forEach(function (subject) {
        const marks = students.map(function (student) {
            return getMarks(student)[subject];
        });

        if (marks.length === 0) return;

        const total = marks.reduce(function (sum, mark) {
            return sum + mark;
        }, 0);
        const row = tableBody.insertRow();

        addCell(row, subject.toUpperCase());
        addCell(row, (total / marks.length).toFixed(2));
        addCell(row, Math.max(...marks));
        addCell(row, Math.min(...marks));
        addCell(row, marks.length);
    });
}

function renderStatistics() {
    const allMarks = students.flatMap(function (student) {
        return SUBJECTS.map(function (subject) {
            return getMarks(student)[subject];
        });
    });

    getElement("marksEntered").textContent = allMarks.length;

    const average = allMarks.length
        ? allMarks.reduce(function (sum, mark) {
            return sum + mark;
        }, 0) / allMarks.length
        : 0;

    getElement("overallAverage").textContent = average.toFixed(2);
    getElement("highestMark").textContent = allMarks.length ? Math.max(...allMarks) : "—";
    getElement("lowestMark").textContent = allMarks.length ? Math.min(...allMarks) : "—";
}

function fillForm(student) {
    selectedStudentId = student.student_id;

    getElement("studentId").value = student.student_id;
    getElement("name").value = student.name;
    getElement("age").value = student.age;
    getElement("course").value = student.course;
    getElement("email").value = student.email || "";

    const marks = getMarks(student);
    SUBJECTS.forEach(function (subject) {
        getElement(subject).value = marks[subject];
    });

    getElement("formTitle").textContent = `Edit Student #${student.student_id}`;
    getElement("saveButton").textContent = "Update Student";
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetForm() {
    selectedStudentId = null;
    getElement("studentForm").reset();
    getElement("studentId").value = "";
    getElement("formTitle").textContent = "Add Student";
    getElement("saveButton").textContent = "Add Student";
}

function readStudentForm() {
    const marks = {};
    SUBJECTS.forEach(function (subject) {
        marks[subject] = Number(getElement(subject).value);
    });

    return {
        name: getElement("name").value.trim(),
        age: Number(getElement("age").value),
        course: getElement("course").value.trim(),
        email: getElement("email").value.trim(),
        marks: marks
    };
}

function validateStudent(student) {
    if (!student.name || !student.course) {
        showMessage("Student name and course are required.", true);
        return false;
    }

    if (!Number.isInteger(student.age) || student.age < 5 || student.age > 100) {
        showMessage("Enter an age between 5 and 100.", true);
        return false;
    }

    const hasInvalidMark = SUBJECTS.some(function (subject) {
        const mark = student.marks[subject];
        return !Number.isFinite(mark) || mark < 0 || mark > 100;
    });

    if (hasInvalidMark) {
        showMessage("Enter marks from 0 to 100 for all five subjects.", true);
        return false;
    }

    return true;
}

async function saveStudent(event) {
    event.preventDefault();
    const student = readStudentForm();

    if (!validateStudent(student)) return;

    try {
        if (selectedStudentId !== null) {
            await apiRequest(`/students/${selectedStudentId}`, {
                method: "PUT",
                body: JSON.stringify({
                    name: student.name,
                    age: student.age,
                    course: student.course,
                    email: student.email
                })
            });

            await apiRequest(`/students/${selectedStudentId}/marks`, {
                method: "PUT",
                body: JSON.stringify({ marks: student.marks })
            });

            showMessage("Student details and marks updated successfully.");
        } else {
            await apiRequest("/students", {
                method: "POST",
                body: JSON.stringify(student)
            });

            showMessage("Student added successfully.");
        }

        resetForm();
        await loadStudents();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function deleteStudent(studentId) {
    const student = students.find(function (item) {
        return Number(item.student_id) === Number(studentId);
    });

    if (!student) return;

    const confirmed = window.confirm(
        `Delete ${student.name}? This action cannot be undone.`
    );
    if (!confirmed) return;

    try {
        await apiRequest(`/students/${studentId}`, { method: "DELETE" });

        if (Number(selectedStudentId) === Number(studentId)) {
            resetForm();
        }

        await loadStudents();
        showMessage(`${student.name} was deleted successfully.`);
    } catch (error) {
        showMessage(error.message, true);
    }
}

// Connect the form, search box, and buttons to their actions.
getElement("studentForm").addEventListener("submit", saveStudent);
getElement("resetButton").addEventListener("click", resetForm);
getElement("refreshButton").addEventListener("click", loadStudents);
getElement("search").addEventListener("input", renderStudents);
getElement("gradeFilter").addEventListener("change", renderGrades);
getElement("searchByGradeButton").addEventListener("click", renderGrades);

// Load existing records when the page opens.
loadStudents();
