import os
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import College, User, Subject, AttendanceRecord
from .schemas import (
    CollegeCreate, CollegeOut, SignupRequest, LoginRequest, TokenOut,
    SubjectCreate, SubjectOut, AttendanceCreate, AttendanceOut,
    SimulationRequest, UserOut
)
from .auth import (
    hash_password, verify_password, create_token, get_current_user
)
from .calculations import (
    compute_subject_stats, threshold_for_subject, current_percent,
    safe_misses, classes_to_recover, status_band
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AttendEase API", version="1.0.0")

origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/colleges", response_model=list[CollegeOut])
def list_colleges(db: Session = Depends(get_db)):
    return db.scalars(select(College).order_by(College.name)).all()

@app.post("/colleges", response_model=CollegeOut)
def create_college(payload: CollegeCreate, db: Session = Depends(get_db)):
    if payload.semester_end < payload.semester_start:
        raise HTTPException(400, "Semester end must be after start")
    existing = db.scalar(select(College).where(College.name == payload.name))
    if existing:
        return existing
    c = College(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@app.post("/auth/signup", response_model=TokenOut)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(400, "Email already registered")
    if not db.get(College, payload.college_id):
        raise HTTPException(404, "College not found")
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        college_id=payload.college_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer"}

@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user.id), "token_type": "bearer"}

@app.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@app.get("/subjects", response_model=list[SubjectOut])
def list_subjects(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(select(Subject).where(Subject.user_id == user.id).order_by(Subject.name)).all()

@app.post("/subjects", response_model=SubjectOut)
def create_subject(
    payload: SubjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for wd in payload.weekly_schedule:
        if wd < 0 or wd > 6:
            raise HTTPException(400, "weekly_schedule values must be 0..6")
    s = Subject(user_id=user.id, **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@app.put("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    payload: SubjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(Subject, subject_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Subject not found")
    for k, v in payload.model_dump().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s

@app.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(Subject, subject_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Subject not found")
    db.delete(s)
    db.commit()
    return {"deleted": True}

@app.get("/attendance", response_model=list[AttendanceOut])
def list_attendance(
    subject_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        select(AttendanceRecord)
        .join(Subject)
        .where(Subject.user_id == user.id)
        .order_by(AttendanceRecord.date.desc())
    )
    if subject_id:
        q = q.where(AttendanceRecord.subject_id == subject_id)
    return db.scalars(q).all()

@app.post("/attendance", response_model=AttendanceOut)
def upsert_attendance(
    payload: AttendanceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(Subject, payload.subject_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Subject not found")
    if payload.date > date.today():
        raise HTTPException(400, "Cannot mark attendance for a future date")

    rec = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.subject_id == payload.subject_id,
            AttendanceRecord.date == payload.date,
        )
    )
    if rec:
        rec.status = payload.status
    else:
        rec = AttendanceRecord(**payload.model_dump())
        db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

@app.delete("/attendance/{record_id}")
def delete_attendance(
    record_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rec = db.get(AttendanceRecord, record_id)
    if not rec or rec.subject.user_id != user.id:
        raise HTTPException(404, "Attendance record not found")
    db.delete(rec)
    db.commit()
    return {"deleted": True}

@app.get("/stats")
def stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subjects = db.scalars(
        select(Subject)
        .options(joinedload(Subject.attendance_records))
        .where(Subject.user_id == user.id)
    ).unique().all()

    per_subject = [compute_subject_stats(s, user.college, date.today()) for s in subjects]

    total_attended = sum(x["attended"] for x in per_subject)
    total_held = sum(x["held"] for x in per_subject)
    total_remaining = sum(x["remaining_estimated"] for x in per_subject)
    overall_threshold = user.college.min_attendance_percent
    overall_pct = current_percent(total_attended, total_held)
    overall_recover = classes_to_recover(
        total_attended, total_held, overall_threshold, total_remaining
    )

    return {
        "subjects": per_subject,
        "overall": {
            "threshold": overall_threshold,
            "attended": total_attended,
            "held": total_held,
            "remaining_estimated": total_remaining,
            "attendance_percent": overall_pct,
            "safe_misses": safe_misses(
                total_attended, total_held, overall_threshold, total_remaining
            ),
            "classes_to_recover": overall_recover["needed"],
            "recovery_possible": overall_recover["possible"],
            "status": status_band(overall_pct, overall_threshold),
        },
    }

@app.post("/simulate")
def simulate(
    payload: SimulationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.scalar(
        select(Subject)
        .options(joinedload(Subject.attendance_records))
        .where(Subject.id == payload.subject_id, Subject.user_id == user.id)
    )
    if not s:
        raise HTTPException(404, "Subject not found")
    held_records = [r for r in s.attendance_records if r.status in ("present", "absent")]
    attended = sum(1 for r in held_records if r.status == "present")
    held = len(held_records)

    for result in payload.future_results:
        held += 1
        if result == "present":
            attended += 1

    threshold = threshold_for_subject(s, user.college)
    pct = current_percent(attended, held)
    return {
        "attendance_percent": pct,
        "attended": attended,
        "held": held,
        "threshold": threshold,
        "status": status_band(pct, threshold),
    }
