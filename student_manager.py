import csv
import datetime
import io
import json
import os
from collections import Counter

from utils import format_name_for_report, get_letter_grade, log_action, validate_email


TOTAL_CLASSES = 40
GRADE_ORDER = ("A", "B", "C", "D", "F")


class StudentManager:
    def __init__(self):
        self.students = []
        self.processed_count = 0
        self.notification_log = []

    def add_student(self, student):
        self.students.append(student)

    def process_students(
        self,
        mode,
        output_dir=None,
        send_notifications=False,
        notification_prefix="",
        min_attendance_pct=75,
        include_warnings=True,
        export_format=None,
    ):
        processors = {
            "grade": lambda student: self._process_grade(
                student, send_notifications, notification_prefix
            ),
            "attendance": lambda student: self._process_attendance(
                student,
                send_notifications,
                notification_prefix,
                min_attendance_pct,
                include_warnings,
            ),
            "status": self._process_status,
        }

        processor = processors.get(mode)
        if processor is None:
            return []

        for student in self.students:
            processor(student)

        self.processed_count += len(self.students)
        return list(self.students)

    def generate_report(
        self,
        students,
        report_type,
        include_header=True,
        include_summary=True,
        sort_by=None,
        output_file=None,
    ):
        builders = {
            "grades": self._build_grades_report,
            "attendance": self._build_attendance_report,
            "full": self._build_full_report,
        }

        builder = builders.get(report_type)
        if builder is None:
            return ""

        lines = self._header_lines(report_type) if include_header else []
        lines.extend(builder(students, sort_by, include_summary))
        report_text = "\n".join(lines)
        self._write_file(output_file, report_text, "REPORT", f"Report saved to {output_file}")
        return report_text

    def export_data(self, students, fmt, filepath=None):
        exporters = {
            "json": self._export_json,
            "csv": self._export_csv,
        }
        result = exporters.get(fmt, self._export_pipe)(students)
        self._write_file(filepath, result)
        return result

    def get_statistics(self, students):
        if not students:
            return {}

        gpas = [student.gpa for student in students if student.gpa is not None]
        grade_counts = self._grade_counts(students)
        passing_count = sum(grade_counts[grade] for grade in ("A", "B", "C", "D"))

        return {
            "total": len(students),
            "avg_gpa": round(sum(gpas) / len(gpas), 2) if gpas else 0,
            "highest_gpa": round(max(gpas), 2) if gpas else 0,
            "lowest_gpa": round(min(gpas), 2) if gpas else 0,
            "grade_a": grade_counts["A"],
            "grade_b": grade_counts["B"],
            "grade_c": grade_counts["C"],
            "grade_d": grade_counts["D"],
            "grade_f": grade_counts["F"],
            "warnings": sum(1 for student in students if student.warning),
            "scholarship_eligible": sum(
                1 for student in students if student.scholarship_eligible
            ),
            "pass_rate": round(passing_count / len(students) * 100, 1),
        }

    def search_students(self, query, field):
        searchers = {
            "name": lambda student: str(query).lower() in student.name.lower(),
            "major": lambda student: str(query).lower() in student.major.lower(),
            "id": lambda student: str(query) == str(student.student_id),
        }
        matches = searchers.get(field)
        if matches is None:
            return []
        return [student for student in self.students if matches(student)]

    def _send_notification(self, student, message, notification_type):
        if not validate_email(student.email):
            return

        self.notification_log.append({
            "to": student.email,
            "message": message,
            "sent_at": self._timestamp(),
            "type": notification_type,
        })
        log_action(
            "NOTIFICATION",
            f"{notification_type.title()} notification sent to {student.email}",
        )

    def _process_grade(self, student, send_notifications, notification_prefix):
        average = sum(student.grades) / len(student.grades) if student.grades else 0
        student.final_grade = get_letter_grade(average)
        student.gpa = average / 25
        student.scholarship_eligible = average >= 85 and student.attendance_count >= 35

        if send_notifications:
            message = (
                f"{notification_prefix} {student.name}, your grade is {student.final_grade} "
                f"(GPA: {round(student.gpa, 2)})"
            )
            self._send_notification(student, message, "grade")

    def _process_attendance(
        self,
        student,
        send_notifications,
        notification_prefix,
        min_attendance_pct,
        include_warnings,
    ):
        rate = self._attendance_rate(student)
        student.warning = rate < min_attendance_pct

        if student.warning and include_warnings:
            warning_note = f"Low attendance warning: {round(rate, 1)}%"
            if warning_note not in student.notes:
                student.notes.append(warning_note)

        if student.warning and send_notifications:
            message = f"{notification_prefix} {student.name}, attendance warning: {round(rate, 1)}%"
            self._send_notification(student, message, "attendance")

    def _process_status(self, student):
        if student.final_grade == "F":
            student.status = "probation"
        elif student.warning:
            student.status = "warning"
        else:
            student.status = "good_standing"

    def _build_grades_report(self, students, sort_by, include_summary):
        lines = []
        for student in self._sort_students(students, sort_by):
            line = (
                f"  {format_name_for_report(student.name):<30} | "
                f"Grade: {student.final_grade or 'N/A':<3} | "
                f"GPA: {student.gpa or 0:.2f}"
            )
            if student.scholarship_eligible:
                line += " | SCHOLARSHIP"
            lines.append(line)

        if include_summary:
            lines.extend(self._grades_summary_lines(students))
        return lines

    def _build_attendance_report(self, students, sort_by, include_summary):
        lines = []
        for student in self._sort_students(students, sort_by):
            rate = self._attendance_rate(student)
            status_mark = "WARN" if student.warning else "OK"
            lines.append(
                f"  {format_name_for_report(student.name):<30} | "
                f"Attended: {student.attendance_count}/{TOTAL_CLASSES} ({rate:.0f}%) {status_mark}"
            )

        if include_summary:
            lines.extend(self._attendance_summary_lines(students))
        return lines

    def _build_full_report(self, students, sort_by, include_summary):
        lines = []
        for student in self._sort_students(students, sort_by):
            rate = self._attendance_rate(student)
            lines.extend([
                f"  {format_name_for_report(student.name)}",
                f"    ID: {student.student_id} | Year: {student.year} | Major: {student.major}",
                f"    Grade: {student.final_grade or 'N/A'} | GPA: {student.gpa or 0:.2f}",
                f"    Attendance: {student.attendance_count}/{TOTAL_CLASSES} ({rate:.0f}%)",
                f"    Status: {student.status}",
            ])
            if student.notes:
                lines.append(f"    Notes: {'; '.join(student.notes)}")
            lines.append("")
        return lines

    def _grades_summary_lines(self, students):
        grade_counts = self._grade_counts(students)
        gpas = [student.gpa for student in students if student.gpa is not None]
        average_gpa = sum(gpas) / len(gpas) if gpas else 0
        scholarship_count = sum(1 for student in students if student.scholarship_eligible)

        return [
            "",
            "-" * 60,
            f"  Total Students: {len(students)}",
            f"  Average GPA: {average_gpa:.2f}",
            "  Grade Distribution: "
            + ", ".join(f"{grade}={grade_counts[grade]}" for grade in GRADE_ORDER),
            f"  Scholarship Eligible: {scholarship_count}",
        ]

    def _attendance_summary_lines(self, students):
        average_attendance = (
            sum(student.attendance_count for student in students) / len(students)
            if students
            else 0
        )
        warning_count = sum(1 for student in students if student.warning)

        return [
            "",
            "-" * 60,
            f"  Total Students: {len(students)}",
            f"  Average Attendance: {average_attendance:.1f}/{TOTAL_CLASSES} "
            f"({average_attendance / TOTAL_CLASSES * 100:.0f}%)",
            f"  Students with Warnings: {warning_count}",
        ]

    def _sort_students(self, students, sort_by):
        sorters = {
            "name": lambda student: student.name,
            "grade": lambda student: student.gpa if student.gpa else 0,
            "attendance": lambda student: student.attendance_count,
            "id": lambda student: student.student_id,
        }
        key = sorters.get(sort_by)
        if key is None:
            return list(students)
        return sorted(students, key=key, reverse=sort_by in {"grade", "attendance"})

    def _header_lines(self, report_type):
        titles = {
            "grades": "STUDENT GRADES REPORT",
            "attendance": "STUDENT ATTENDANCE REPORT",
            "full": "FULL STUDENT REPORT",
        }
        return [
            "=" * 60,
            titles[report_type],
            f"Generated: {self._timestamp()}",
            "=" * 60,
            "",
        ]

    def _grade_counts(self, students):
        counts = Counter(student.final_grade for student in students)
        return {grade: counts.get(grade, 0) for grade in GRADE_ORDER}

    def _attendance_rate(self, student):
        return student.attendance_count / TOTAL_CLASSES * 100

    def _export_json(self, students):
        data = [
            {
                "name": student.name,
                "student_id": student.student_id,
                "email": student.email,
                "final_grade": student.final_grade,
                "gpa": student.gpa,
                "attendance_count": student.attendance_count,
                "warning": student.warning,
                "status": student.status,
                "scholarship_eligible": student.scholarship_eligible,
            }
            for student in students
        ]
        return json.dumps(data, indent=2)

    def _export_csv(self, students):
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow([
            "name",
            "student_id",
            "email",
            "final_grade",
            "gpa",
            "attendance",
            "warning",
            "status",
        ])
        for student in students:
            writer.writerow([
                student.name,
                student.student_id,
                student.email,
                student.final_grade,
                student.gpa,
                student.attendance_count,
                student.warning,
                student.status,
            ])
        return output.getvalue()

    def _export_pipe(self, students):
        return "".join(
            f"{student.name}|{student.student_id}|{student.final_grade}\n"
            for student in students
        )

    def _write_file(self, filepath, content, action=None, details=None):
        if not filepath:
            return
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
        if action and details:
            log_action(action, details)

    def _timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
