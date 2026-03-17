# 🎓 ScholarPath – AI-Based Scholarship Assistance Web Application

A Flask + SQLite + Bootstrap 5 web application that uses a **Rule-Based AI Engine** to match student profiles with eligible scholarships — including Telangana state schemes and TS ePASS.

---

## 📁 Project Structure

```
scholarship_app/
├── app.py            ← Flask routes + app entry point
├── models.py         ← SQLite schema, seed data & DB helpers
├── rule_engine.py    ← Rule-Based AI matching engine
├── scholarships.db   ← Auto-generated SQLite database (on first run)
├── README.md
├── static/
│   └── css/
│       └── style.css ← Custom premium CSS
└── templates/
    ├── base.html     ← Shared layout (navbar + footer)
    ├── index.html    ← Home page
    ├── form.html     ← Eligibility check form
    └── results.html  ← Matched scholarship results
```

---

## ⚙️ Setup & Run

### 1. Install Dependencies

```bash
pip install flask
```

### 2. Navigate to the project folder

```bash
cd /home/C2/.gemini/antigravity/scratch/scholarship_app
```

### 3. Run the Application

```bash
python app.py
```

> The database (`scholarships.db`) is **automatically initialized with seed data** on first run.  
> No separate `init_db` step is required.

### 4. Open in Browser

```
http://127.0.0.1:5000
```

---

## 🤖 How the AI Engine Works

The `RuleEngine` class in `rule_engine.py` applies **IF-THEN logic** for each scholarship:

| Rule | Condition |
|------|-----------|
| ✅ GPA | `student_gpa >= scholarship_min_gpa` |
| ✅ Income | `student_income <= scholarship_max_income` |
| ✅ Course | `student_course matches scholarship_required_course (or 'Any')` |
| ✅ State | `student_state matches scholarship_required_state (or 'Any')` |
| ✅ Category | `student_category matches scholarship_category (or 'All')` |
| ✅ Gender | `student_gender matches scholarship_gender_req (or 'Any')` |

Each matched scholarship includes a human-readable **Eligibility Reason** string explaining exactly why the student qualifies.

---

## 📚 Scholarships Seeded

| Scholarship | State | Category | Gender | Amount |
|---|---|---|---|---|
| Reliance Foundation Scholarship | All India | All | Any | ₹2,00,000/yr |
| NSP Central Sector Scholarship | All India | All | Any | ₹12,000/yr |
| AICTE Pragati (Diploma) | All India | All | Female | ₹50,000/yr |
| AICTE Pragati (B.Tech) | All India | All | Female | ₹50,000/yr |
| Sitaram Jindal Foundation | All India | All | Any | ₹24,000/yr |
| Post-Matric SC Scholarship | All India | SC | Any | ₹1,20,000/yr |
| Post-Matric ST Scholarship | All India | ST | Any | ₹1,20,000/yr |
| OBC Post-Matric Scholarship | All India | OBC | Any | ₹24,000/yr |
| Pragati Scholarship for Women | Telangana | All | Female | ₹30,000/yr |
| TS ePASS (SC) | Telangana | SC | Any | Full tuition |
| TS ePASS (ST) | Telangana | ST | Any | Full tuition |
| TS ePASS for OBC/EBC | Telangana | OBC | Any | Tuition fee |
| Telangana State Merit Scholarship | Telangana | All | Any | ₹15,000/yr |
| Dr. B.R. Ambedkar Overseas Scholarship | Telangana | SC | Any | ₹20,00,000 |

---

## 🔗 API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Home page |
| `/form` | GET | Eligibility form |
| `/results` | POST | AI matching results |
| `/api/scholarships` | GET | All scholarships as JSON |

---

## 🛠 Tech Stack

- **Backend**: Python 3 + Flask
- **Database**: SQLite (via `sqlite3` stdlib)
- **Frontend**: Bootstrap 5.3 + Bootstrap Icons + Google Fonts (Inter)
- **AI Logic**: Rule-Based Engine (IF-THEN pattern matching)
