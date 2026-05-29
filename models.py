from dataclasses import asdict, dataclass, field
from typing import Optional


CREDITS_BY_YEAR = {
    1: 30,
    2: 60,
    3: 90,
    4: 120,
}


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

    def to_string(self) -> str:
        return f"{self.name} ({self.student_id})"

    def to_dict(self) -> dict:
        return asdict(self)

    def is_equal(self, other: object) -> bool:
        return isinstance(other, Student) and self.student_id == other.student_id

    def get_full_info(self) -> str:
        return "\n".join([
            f"Student: {self.name}",
            f"ID: {self.student_id}",
            f"Email: {self.email}",
            f"Year: {self.year}",
            f"Major: {self.major}",
            f"Phone: {self.phone}",
            f"Address: {self.address}",
            f"Emergency: {self.emergency_contact}",
            "",
        ])

    def calculate_credits(self) -> int:
        return CREDITS_BY_YEAR.get(self.year, 0)
