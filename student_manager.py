# student_manager.py - Main business logic
# This class handles everything related to student management
# It processes grades, attendance, reports, and notifications
import datetime
import json
import os

from utils import format_name_for_report, get_letter_grade, validate_email, log_action


class StudentManager:
    """The main class that manages all student operations.
    Handles grading, attendance tracking, report generation,
    notifications, data persistence, and statistics."""

    def __init__(self):
        self.students = []
        self.processed_count = 0
        self.error_log = []
        self.notification_log = []
        self._cache = {}  # might be useful for performance later

    def add_student(self, student):
        self.students.append(student)

    def _send_notification(self, student, message, notification_type):
        if not validate_email(student.email):
            return
        self.notification_log.append({
            "to": student.email,
            "message": message,
            "sent_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": notification_type
        })
        log_action("NOTIFICATION", f"{notification_type.title()} notification sent to {student.email}")

    def _process_grade(self, student, send_notifications, notification_prefix):
        avg = sum(student.grades) / len(student.grades) if student.grades else 0
        letter = get_letter_grade(avg)
        student.final_grade = letter
        student.gpa = avg / 25
        student.scholarship_eligible = avg >= 85 and student.attendance_count >= 35

        if send_notifications:
            message = (
                f"{notification_prefix} {student.name}, your grade is {letter} "
                f"(GPA: {round(student.gpa, 2)})"
            )
            self._send_notification(student, message, "grade")

    def _process_attendance(self, student, send_notifications, notification_prefix, min_attendance_pct, include_warnings):
        total_classes = 40
        rate = student.attendance_count / total_classes * 100
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

    def process_students(self, mode, output_dir, send_notifications,
                         notification_prefix, min_attendance_pct,
                         include_warnings, export_format):
        results = []
        for s in self.students:
            if mode == "grade":
                self._process_grade(s, send_notifications, notification_prefix)
                results.append(s)
                self.processed_count += 1
            elif mode == "attendance":
                self._process_attendance(s, send_notifications, notification_prefix, min_attendance_pct, include_warnings)
                results.append(s)
                self.processed_count += 1
            elif mode == "status":
                self._process_status(s)
                results.append(s)
                self.processed_count += 1

        return results

    # Generate a report for the students
    def generate_report(self, students, report_type, include_header,
                        include_summary, sort_by, output_file):
        lines = []

        if report_type == "grades":
            if include_header:
                lines.append("=" * 60)
                lines.append("STUDENT GRADES REPORT")
                lines.append("Generated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                lines.append("=" * 60)
                lines.append("")

            # Sort students
            if sort_by == "name":
                sorted_students = sorted(students, key=lambda x: x.name)
            elif sort_by == "grade":
                sorted_students = sorted(students, key=lambda x: x.gpa if x.gpa else 0, reverse=True)
            elif sort_by == "id":
                sorted_students = sorted(students, key=lambda x: x.student_id)
            else:
                sorted_students = students

            for s in sorted_students:
                formatted = format_name_for_report(s.name)
                line = f"  {formatted:<30} | Grade: {s.final_grade or 'N/A':<3} | GPA: {s.gpa or 0:.2f}"
                if s.scholarship_eligible:
                    line += " | SCHOLARSHIP"
                lines.append(line)

            if include_summary:
                lines.append("")
                lines.append("-" * 60)
                # Calculate summary statistics
                total_gpa = 0
                count = 0
                grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
                for s in students:
                    if s.gpa is not None:
                        total_gpa += s.gpa
                        count += 1
                    if s.final_grade in grade_counts:
                        grade_counts[s.final_grade] += 1

                avg_gpa = total_gpa / count if count > 0 else 0
                lines.append(f"  Total Students: {len(students)}")
                lines.append(f"  Average GPA: {avg_gpa:.2f}")
                lines.append(f"  Grade Distribution: A={grade_counts['A']}, B={grade_counts['B']}, C={grade_counts['C']}, D={grade_counts['D']}, F={grade_counts['F']}")
                scholarship_count = sum(1 for s in students if s.scholarship_eligible)
                lines.append(f"  Scholarship Eligible: {scholarship_count}")

        elif report_type == "attendance":
            if include_header:
                lines.append("=" * 60)
                lines.append("STUDENT ATTENDANCE REPORT")
                lines.append("Generated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                lines.append("=" * 60)
                lines.append("")

            # Sort students
            if sort_by == "name":
                sorted_students = sorted(students, key=lambda x: x.name)
            elif sort_by == "attendance":
                sorted_students = sorted(students, key=lambda x: x.attendance_count, reverse=True)
            elif sort_by == "id":
                sorted_students = sorted(students, key=lambda x: x.student_id)
            else:
                sorted_students = students

            for s in sorted_students:
                formatted = format_name_for_report(s.name)
                rate = s.attendance_count / 40 * 100
                status_mark = "WARN" if s.warning else "OK"
                line = f"  {formatted:<30} | Attended: {s.attendance_count}/40 ({rate:.0f}%) {status_mark}"
                lines.append(line)

            if include_summary:
                lines.append("")
                lines.append("-" * 60)
                total_att = 0
                warning_count = 0
                for s in students:
                    total_att += s.attendance_count
                    if s.warning:
                        warning_count += 1
                avg_att = total_att / len(students) if students else 0
                lines.append(f"  Total Students: {len(students)}")
                lines.append(f"  Average Attendance: {avg_att:.1f}/40 ({avg_att/40*100:.0f}%)")
                lines.append(f"  Students with Warnings: {warning_count}")

        elif report_type == "full":
            if include_header:
                lines.append("=" * 60)
                lines.append("FULL STUDENT REPORT")
                lines.append("Generated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                lines.append("=" * 60)
                lines.append("")

            for s in students:
                formatted = format_name_for_report(s.name)
                rate = s.attendance_count / 40 * 100
                lines.append(f"  {formatted}")
                lines.append(f"    ID: {s.student_id} | Year: {s.year} | Major: {s.major}")
                lines.append(f"    Grade: {s.final_grade or 'N/A'} | GPA: {s.gpa or 0:.2f}")
                lines.append(f"    Attendance: {s.attendance_count}/40 ({rate:.0f}%)")
                lines.append(f"    Status: {s.status}")
                if s.notes:
                    lines.append(f"    Notes: {'; '.join(s.notes)}")
                lines.append("")

        report_text = "\n".join(lines)

        if output_file:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
            with open(output_file, "w") as f:
                f.write(report_text)
            log_action("REPORT", f"Report saved to {output_file}")

        return report_text

    def export_data(self, students, fmt, filepath):
        if fmt == "json":
            data = []
            for s in students:
                d = {}
                d["name"] = s.name
                d["student_id"] = s.student_id
                d["email"] = s.email
                d["final_grade"] = s.final_grade
                d["gpa"] = s.gpa
                d["attendance_count"] = s.attendance_count
                d["warning"] = s.warning
                d["status"] = s.status
                d["scholarship_eligible"] = s.scholarship_eligible
                data.append(d)
            result = json.dumps(data, indent=2)
        elif fmt == "csv":
            result = "name,student_id,email,final_grade,gpa,attendance,warning,status\n"
            for s in students:
                result += f"{s.name},{s.student_id},{s.email},{s.final_grade},{s.gpa},{s.attendance_count},{s.warning},{s.status}\n"
        else:
            result = ""
            for s in students:
                result += s.name + "|" + str(s.student_id) + "|" + str(s.final_grade) + "\n"

        if filepath:
            with open(filepath, "w") as f:
                f.write(result)
        return result

    # Get statistics about students
    def get_statistics(self, students):
        if not students:
            return {}

        # Calculate GPA statistics
        total_gpa = 0
        gpas = []
        for s in students:
            if s.gpa is not None:
                total_gpa += s.gpa
                gpas.append(s.gpa)

        avg_gpa = total_gpa / len(gpas) if gpas else 0

        # Find highest and lowest GPA
        highest_gpa = 0
        lowest_gpa = 999
        for g in gpas:
            if g > highest_gpa:
                highest_gpa = g
            if g < lowest_gpa:
                lowest_gpa = g

        # Count grades
        a_count = 0
        b_count = 0
        c_count = 0
        d_count = 0
        f_count = 0
        for s in students:
            if s.final_grade == "A":
                a_count += 1
            elif s.final_grade == "B":
                b_count += 1
            elif s.final_grade == "C":
                c_count += 1
            elif s.final_grade == "D":
                d_count += 1
            elif s.final_grade == "F":
                f_count += 1

        # Count attendance warnings
        warning_count = 0
        for s in students:
            if s.warning:
                warning_count += 1

        # Count scholarship eligible
        scholarship_count = 0
        for s in students:
            if s.scholarship_eligible:
                scholarship_count += 1

        return {
            "total": len(students),
            "avg_gpa": round(avg_gpa, 2),
            "highest_gpa": round(highest_gpa, 2),
            "lowest_gpa": round(lowest_gpa, 2),
            "grade_a": a_count,
            "grade_b": b_count,
            "grade_c": c_count,
            "grade_d": d_count,
            "grade_f": f_count,
            "warnings": warning_count,
            "scholarship_eligible": scholarship_count,
            "pass_rate": round((a_count + b_count + c_count + d_count) / len(students) * 100, 1)
        }

    # Search for students - might need this later
    def search_students(self, query, field):
        results = []
        for s in self.students:
            if field == "name":
                if query.lower() in s.name.lower():
                    results.append(s)
            elif field == "major":
                if query.lower() in s.major.lower():
                    results.append(s)
            elif field == "id":
                if str(query) == str(s.student_id):
                    results.append(s)
        return results
