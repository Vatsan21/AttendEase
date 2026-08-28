from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict

AttendanceStatus = Literal["present", "absent", "cancelled", "holiday"]
ClassType = Literal["lecture", "lab", "tutorial"]

class CollegeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    min_attendance_percent: float = Field(ge=0, le=100)
    lab_min_percent: Optional[float] = Field(default=None, ge=0, le=100)
    theory_min_percent: Optional[float] = Field(default=None, ge=0, le=100)
    condonation_min_percent: Optional[float] = Field(default=None, ge=0, le=100)
    semester_start: date
    semester_end: date

class CollegeOut(CollegeCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    college_id: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SubjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    instructor: Optional[str] = None
    class_type: ClassType = "lecture"
    weekly_schedule: List[int] = Field(
        default_factory=list,
        description="Python weekday integers: Monday=0 ... Sunday=6. Duplicate weekdays are allowed to represent multiple classes."
    )
    custom_threshold: Optional[float] = Field(default=None, ge=0, le=100)

class SubjectOut(SubjectCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AttendanceCreate(BaseModel):
    subject_id: int
    date: date
    status: AttendanceStatus

class AttendanceOut(AttendanceCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class SimulationRequest(BaseModel):
    subject_id: int
    future_results: List[Literal["present", "absent"]]

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    college: CollegeOut
    model_config = ConfigDict(from_attributes=True)
