from math import floor, ceil
from datetime import date, timedelta

def current_percent(attended: int, held: int) -> float:
    return round((attended / held) * 100, 2) if held > 0 else 0.0

def safe_misses(attended: int, held: int, threshold: float, remaining: int) -> int:
    if held <= 0:
        return 0
    p = threshold / 100.0
    if p <= 0:
        return remaining
    if attended / held < p:
        return 0
    max_by_math = floor((attended / p) - held + 1e-9)
    return max(0, min(remaining, max_by_math))

def classes_to_recover(attended: int, held: int, threshold: float, remaining: int):
    p = threshold / 100.0
    if p <= 0:
        return {"needed": 0, "possible": True}
    if p >= 1:
        needed = 0 if attended == held else None
        return {"needed": needed, "possible": needed == 0}
    if held == 0 or attended / held >= p:
        return {"needed": 0, "possible": True}

    # (a+y)/(h+y) >= p => y >= (p*h-a)/(1-p)
    needed = max(0, ceil(((p * held) - attended) / (1 - p) - 1e-12))
    return {"needed": needed, "possible": needed <= remaining}

def threshold_for_subject(subject, college):
    if subject.custom_threshold is not None:
        return subject.custom_threshold
    if subject.class_type == "lab" and college.lab_min_percent is not None:
        return college.lab_min_percent
    if subject.class_type == "lecture" and college.theory_min_percent is not None:
        return college.theory_min_percent
    return college.min_attendance_percent

def count_remaining_occurrences(weekly_schedule, start: date, end: date) -> int:
    if start > end:
        return 0
    counts = {}
    for wd in weekly_schedule or []:
        counts[wd] = counts.get(wd, 0) + 1
    total = 0
    d = start
    while d <= end:
        total += counts.get(d.weekday(), 0)
        d += timedelta(days=1)
    return total

def status_band(percent: float, threshold: float) -> str:
    if percent >= threshold + 5:
        return "safe"
    if percent >= threshold:
        return "borderline"
    return "risk"

def compute_subject_stats(subject, college, today: date):
    held_records = [r for r in subject.attendance_records if r.status in ("present", "absent")]
    attended = sum(1 for r in held_records if r.status == "present")
    held = len(held_records)
    threshold = threshold_for_subject(subject, college)
    remaining = count_remaining_occurrences(
        subject.weekly_schedule,
        max(today + timedelta(days=1), college.semester_start),
        college.semester_end,
    )
    pct = current_percent(attended, held)
    recover = classes_to_recover(attended, held, threshold, remaining)

    return {
        "subject_id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "class_type": subject.class_type,
        "threshold": threshold,
        "attended": attended,
        "held": held,
        "remaining_estimated": remaining,
        "attendance_percent": pct,
        "safe_misses": safe_misses(attended, held, threshold, remaining),
        "classes_to_recover": recover["needed"],
        "recovery_possible": recover["possible"],
        "status": status_band(pct, threshold),
    }
