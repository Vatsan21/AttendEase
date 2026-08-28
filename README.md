# AttendEase

A full-stack college attendance tracker.

## Stack
- Frontend: React + Vite
- Backend: FastAPI
- Database: PostgreSQL
- Auth: JWT email/password
- Containerization: Docker Compose

## Run

```bash
docker compose up --build
```

Open:
- App: http://localhost:5173
- API docs: http://localhost:8000/docs

## Main capabilities
- College attendance policy setup
- Per-subject threshold and class type
- Weekly schedule storage
- Present / absent / cancelled / holiday entries
- Real-time attendance %
- Safe classes to miss
- Classes needed to recover
- Recovery-impossible warning based on remaining scheduled classes
- Overall weighted attendance
- What-if simulator
- JWT authentication

## Calculation definitions

Held classes = Present + Absent.

Current attendance:
`attended / held * 100`

Safe consecutive misses:
largest `x` such that:
`attended / (held + x) >= threshold`

Recovery classes:
smallest `y` such that:
`(attended + y) / (held + y) >= threshold`

The backend caps both calculations by estimated remaining scheduled classes.

## Notes
This is a production-oriented MVP, not a final production deployment. Before public deployment add:
- email verification / password reset
- OAuth if desired
- migrations via Alembic
- rate limiting
- stronger secret management
- notification worker
- automated frontend tests
- institution moderation / deduplication
