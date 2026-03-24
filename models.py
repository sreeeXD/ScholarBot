import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'scholarships.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scholarships (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL UNIQUE,
            min_gpa          REAL DEFAULT 0.0,
            max_income       REAL DEFAULT 9999999,
            required_course  TEXT DEFAULT 'Any',
            required_state   TEXT DEFAULT 'Any',
            category         TEXT DEFAULT 'All',
            gender_req       TEXT DEFAULT 'Any',
            amount           TEXT,
            deadline         TEXT,
            apply_link       TEXT,
            description      TEXT,
            documents_required TEXT DEFAULT ''
        )
    ''')

    # Add column if upgrading an existing DB
    try:
        cursor.execute("ALTER TABLE scholarships ADD COLUMN documents_required TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass  # Column already exists

    scholarships = [
        # ── National Scholarships ──────────────────────────────────────────────
        (
            'Reliance Foundation Scholarship',
            7.5, 600000, 'Any', 'Any', 'All', 'Any',
            '₹2,00,000/year', '2026-10-31',
            'https://scholarships.reliancefoundation.org',
            'Merit-cum-means scholarship for undergraduate students across India.',
            'Aadhaar Card|Class 10 & 12 Marksheets|College Admission Letter|Family Income Certificate|Bank Account Details|Passport-size Photograph|Caste Certificate (if applicable)'
        ),
        (
            'NSP Central Sector Scholarship',
            8.0, 800000, 'Any', 'Any', 'All', 'Any',
            '₹12,000/year', '2026-10-15',
            'https://scholarships.gov.in',
            'For students who scored in top 20 percentile in Class XII.',
            'Aadhaar Card|Class 12 Marksheet (top 20 percentile proof)|Income Certificate|College Enrollment Proof|Bank Passbook Copy|Passport-size Photograph'
        ),
        (
            'AICTE Pragati Scholarship (Diploma)',
            6.0, 800000, 'Diploma', 'Any', 'All', 'Female',
            '₹50,000/year', '2026-09-30',
            'https://www.aicte-india.org/bureaus/bos/pragati',
            'AICTE scholarship for girl students studying Diploma courses.',
            'Aadhaar Card|AICTE Approved Institution Proof|Diploma Admission Letter|Previous Year Marksheet|Family Income Certificate|Bank Account Details|Passport-size Photograph'
        ),
        (
            'AICTE Pragati Scholarship (Degree)',
            6.0, 800000, 'B.Tech', 'Any', 'All', 'Female',
            '₹50,000/year', '2026-09-30',
            'https://www.aicte-india.org/bureaus/bos/pragati',
            'AICTE scholarship for girl students pursuing B.Tech degree.',
            'Aadhaar Card|AICTE Approved College Proof|B.Tech Admission Letter|Previous Year Marksheet|Family Income Certificate|Bank Account Details|Passport-size Photograph'
        ),
        (
            'Sitaram Jindal Foundation Scholarship',
            6.5, 250000, 'Any', 'Any', 'All', 'Any',
            '₹24,000/year', '2026-09-30',
            'https://www.sitaramjindalfoundation.org',
            'For meritorious students from economically weaker sections.',
            'Aadhaar Card|Latest Marksheet|Income Certificate (below ₹2.5 lakh)|College ID Card|Bank Passbook Copy|Passport-size Photograph'
        ),
        (
            'Post-Matric Scholarship for SC Students',
            0.0, 250000, 'Any', 'Any', 'SC', 'Any',
            '₹1,20,000/year', '2026-10-31',
            'https://scholarships.gov.in',
            'Central government scholarship for SC category post-matric students.',
            'Aadhaar Card|SC Caste Certificate|Income Certificate|Admission Proof|Previous Year Marksheet|Bank Account Details|Passport-size Photograph'
        ),
        (
            'Post-Matric Scholarship for ST Students',
            0.0, 250000, 'Any', 'Any', 'ST', 'Any',
            '₹1,20,000/year', '2026-10-31',
            'https://scholarships.gov.in',
            'Central government scholarship for ST category post-matric students.',
            'Aadhaar Card|ST Caste Certificate|Income Certificate|Admission Proof|Previous Year Marksheet|Bank Account Details|Passport-size Photograph'
        ),
        (
            'OBC Pre-Matric & Post-Matric Scholarship',
            5.0, 100000, 'Any', 'Any', 'OBC', 'Any',
            '₹24,000/year', '2026-10-31',
            'https://scholarships.gov.in',
            'Central government scholarship for OBC students.',
            'Aadhaar Card|OBC Non-Creamy Layer Certificate|Income Certificate|Admission Proof|Previous Year Marksheet|Bank Account Details|Passport-size Photograph'
        ),

        # ── Telangana State Scholarships ───────────────────────────────────────
        (
            'Pragati Scholarship for Women',
            6.0, 800000, 'B.Tech', 'Telangana', 'All', 'Female',
            '₹30,000/year', '2026-11-15',
            'https://tsche.ac.in',
            'Telangana scholarship for women pursuing technical education in B.Tech.',
            'Aadhaar Card|Telangana Domicile Certificate|B.Tech Admission Letter|Previous Year Marksheet|Family Income Certificate|Bank Account Details|Passport-size Photograph'
        ),
        (
            'TS EPASS Scholarship (Telangana)',
            0.0, 200000, 'Any', 'Telangana', 'SC', 'Any',
            'Full tuition fee reimbursement', '2026-10-31',
            'https://telanganaepass.cgg.gov.in',
            'Telangana e-Pass scheme for SC students – covers full tuition & maintenance.',
            'Aadhaar Card|SC Caste Certificate|Telangana Domicile Certificate|College Fee Receipt|Income Certificate|Bank Passbook Copy|Passport-size Photograph'
        ),
        (
            'TS EPASS Scholarship for ST (Telangana)',
            0.0, 200000, 'Any', 'Telangana', 'ST', 'Any',
            'Full tuition fee reimbursement', '2026-10-31',
            'https://telanganaepass.cgg.gov.in',
            'Telangana e-Pass for ST students – full tuition & hostel fee reimbursement.',
            'Aadhaar Card|ST Caste Certificate|Telangana Domicile Certificate|College Fee Receipt|Hostel Certificate (if applicable)|Income Certificate|Bank Passbook Copy|Passport-size Photograph'
        ),
        (
            'TS EPASS for OBC/EBC (Telangana)',
            0.0, 200000, 'Any', 'Telangana', 'OBC', 'Any',
            'Tuition fee reimbursement', '2026-10-31',
            'https://telanganaepass.cgg.gov.in',
            'Telangana e-Pass for OBC/EBC students pursuing higher education.',
            'Aadhaar Card|OBC/EBC Caste Certificate|Telangana Domicile Certificate|College Fee Receipt|Income Certificate|Bank Passbook Copy|Passport-size Photograph'
        ),
        (
            'Telangana State Merit Scholarship',
            8.5, 500000, 'Any', 'Telangana', 'All', 'Any',
            '₹15,000/year', '2026-11-30',
            'https://tsche.ac.in',
            'Merit-based scholarship for Telangana domicile students with high GPA.',
            'Aadhaar Card|Telangana Domicile Certificate|Latest Marksheet (merit proof)|Income Certificate|College Enrollment Letter|Bank Account Details|Passport-size Photograph'
        ),
        (
            'Dr. B.R. Ambedkar Overseas Scholarship (Telangana)',
            6.5, 250000, 'Any', 'Telangana', 'SC', 'Any',
            '₹20,00,000 (for overseas study)', '2026-06-30',
            'https://bcsw.telangana.gov.in',
            'Scholarship for SC students from Telangana to pursue higher education abroad.',
            'Aadhaar Card|SC Caste Certificate|Telangana Domicile Certificate|Passport|Admission Letter from Overseas University|GRE/GMAT/IELTS Score Card|Income Certificate|Bank Account Details'
        ),
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO scholarships
            (name, min_gpa, max_income, required_course, required_state,
             category, gender_req, amount, deadline, apply_link, description, documents_required)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', scholarships)

    # Update documents for already-existing rows (idempotent)
    for s in scholarships:
        cursor.execute(
            'UPDATE scholarships SET documents_required=? WHERE name=?',
            (s[11], s[0])
        )

    conn.commit()
    conn.close()
    print(f"[DB] Initialized with {len(scholarships)} scholarships → {DB_PATH}")


def get_all_scholarships():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM scholarships')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


if __name__ == '__main__':
    init_db()
