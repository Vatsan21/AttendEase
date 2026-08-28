from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False, unique=True, index=True)
    min_attendance_percent = Column(Float, nullable=False, default=75)
    lab_min_percent = Column(Float, nullable=True)
    theory_min_percent = Column(Float, nullable=True)
    condonation_min_percent = Column(Float, nullable=True)
    semester_start = Column(Date, nullable=False)
    semester_end = Column(Date, nullable=False)

    users = relationship("User", back_populates="college")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)

    college = relationship("College", back_populates="users")
    subjects = relationship("Subject", back_populates="user", cascade="all, delete-orphan")

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    code = Column(String(80), nullable=True)
    instructor = Column(String(160), nullable=True)
    class_type = Column(String(30), nullable=False, default="lecture")
    weekly_schedule = Column(JSON, nullable=False, default=list)
    custom_threshold = Column(Float, nullable=True)

    user = relationship("User", back_populates="subjects")
    attendance_records = relationship(
        "AttendanceRecord",
        back_populates="subject",
        cascade="all, delete-orphan",
    )

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("subject_id", "date", name="uq_subject_date"),
    )

    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False)

    subject = relationship("Subject", back_populates="attendance_records")
