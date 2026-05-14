from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Student:
    name: str
    student_id: int
    email: str
    grades: list[int]
    attendance_count: int
    year: int
    major: str
    phone: str
    address: str
    emergency_contact: str
    enrollment_date: str
    is_international: bool
    final_grade: Optional[str] = None
    gpa: Optional[float] = None
    warning: bool = False
    status: str = "active"
    notes: list[str] = field(default_factory=list)
    scholarship_eligible: bool = False

    def __post_init__(self):
        # TODO: add support for multiple semesters
        # TODO: add GPA history tracking
        # TODO: integrate with university API
        pass

    # This method converts student to a string
    def to_string(self):
        return self.name + " (" + str(self.student_id) + ")"

    # This method converts student to a dictionary
    def to_dict(self):
        return asdict(self)

    # This method checks if two students are equal
    def is_equal(self, other):
        if other is None:
            return False
        return self.student_id == other.student_id

    # Legacy method - kept for backward compatibility
    def get_full_info(self):
        info = "Student: " + self.name + "\n"
        info += "ID: " + str(self.student_id) + "\n"
        info += "Email: " + self.email + "\n"
        info += "Year: " + str(self.year) + "\n"
        info += "Major: " + self.major + "\n"
        info += "Phone: " + self.phone + "\n"
        info += "Address: " + self.address + "\n"
        info += "Emergency: " + self.emergency_contact + "\n"
        return info

    # Never used but might be needed later
    def calculate_credits(self):
        if self.year == 1:
            return 30
        elif self.year == 2:
            return 60
        elif self.year == 3:
            return 90
        elif self.year == 4:
            return 120
        else:
            return 0

    # Experimental feature - not yet implemented
    def predict_graduation(self):
        pass
