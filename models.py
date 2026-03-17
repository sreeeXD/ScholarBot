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
            description      TEXT
        )
    ''')

    scholarships = [
        # ── National Scholarships ──────────────────────────────────────────────
        (
            'Reliance Foundation Scholarship',
            7.5, 600000, 'Any', 'Any', 'All', 'Any',
            '₹2,00,000/year',
            '2026-10-31',
            'https://scholarships.reliancefoundation.org',
            'Merit-cum-means scholarship for undergraduate students across India.'
        ),
        (
            'NSP Central Sector Scholarship',
            8.0, 800000, 'Any', 'Any', 'All', 'Any',
            '₹12,000/year',
            '2026-10-15',
            'https://scholarships.gov.in',
            'For students who scored in top 20 percentile in Class XII.'
        ),
        (
            'AICTE Pragati Scholarship (Diploma)',
            6.0, 800000, 'Diploma', 'Any', 'All', 'Female',
            '₹50,000/year',
            '2026-09-30',
            'https://www.aicte-india.org/bureaus/bos/pragati',
            'AICTE scholarship for girl students studying Diploma courses.'
        ),
        (
            'AICTE Pragati Scholarship (Degree)',
            6.0, 800000, 'B.Tech', 'Any', 'All', 'Female',
            '₹50,000/year',
            '2026-09-30',
            'https://www.aicte-india.org/bureaus/bos/pragati',
            'AICTE scholarship for girl students pursuing B.Tech degree.'
        ),
        (
            'Sitaram Jindal Foundation Scholarship',
            6.5, 250000, 'Any', 'Any', 'All', 'Any',
            '₹24,000/year',
            '2026-09-30',
            'https://www.sitaramjindalfoundation.org',
            'For meritorious students from economically weaker sections.'
        ),
        (
            'Post-Matric Scholarship for SC Students',
            0.0, 250000, 'Any', 'Any', 'SC', 'Any',
            '₹1,20,000/year',
            '2026-10-31',
            'https://scholarships.gov.in',
            'Central government scholarship for SC category post-matric students.'
        ),
        (
            'Post-Matric Scholarship for ST Students',
            0.0, 250000, 'Any', 'Any', 'ST', 'Any',
            '₹1,20,000/year',
            '2026-10-31',
            'https://scholarships.gov.in',
            'Central government scholarship for ST category post-matric students.'
        ),
        (
            'OBC Pre-Matric & Post-Matric Scholarship',
            5.0, 100000, 'Any', 'Any', 'OBC', 'Any',
            '₹24,000/year',
            '2026-10-31',
            'https://scholarships.gov.in',
            'Central government scholarship for OBC students.'
        ),

        # ── Telangana State Scholarships ───────────────────────────────────────
        (
            'Pragati Scholarship for Women',
            6.0, 800000, 'B.Tech', 'Telangana', 'All', 'Female',
            '₹30,000/year',
            '2026-11-15',
            'https://tsche.ac.in',
            'Telangana scholarship for women pursuing technical education in B.Tech.'
        ),
        (
            'TS EPASS Scholarship (Telangana)',
            0.0, 200000, 'Any', 'Telangana', 'SC', 'Any',
            'Full tuition fee reimbursement',
            '2026-10-31',
            'https://telanganaepass.cgg.gov.in',
            'Telangana e-Pass scheme for SC students – covers full tuition & maintenance.'
        ),
        (
            'TS EPASS Scholarship for ST (Telangana)',
            0.0, 200000, 'Any', 'Telangana', 'ST', 'Any',
            'Full tuition fee reimbursement',
            '2026-10-31',
            'https://telanganaepass.cgg.gov.in',
            'Telangana e-Pass for ST students – full tuition & hostel fee reimbursement.'
        ),
        (
            'TS EPASS for OBC/EBC (Telangana)',
            0.0, 200000, 'Any', 'Telangana', 'OBC', 'Any',
            'Tuition fee reimbursement',
            '2026-10-31',
            'https://telanganaepass.cgg.gov.in',
            'Telangana e-Pass for OBC/EBC students pursuing higher education.'
        ),
        (
            'Telangana State Merit Scholarship',
            8.5, 500000, 'Any', 'Telangana', 'All', 'Any',
            '₹15,000/year',
            '2026-11-30',
            'https://tsche.ac.in',
            'Merit-based scholarship for Telangana domicile students with high GPA.'
        ),
        (
            'Dr. B.R. Ambedkar Overseas Scholarship (Telangana)',
            6.5, 250000, 'Any', 'Telangana', 'SC', 'Any',
            '₹20,00,000 (for overseas study)',
            '2026-06-30',
            'https://bcsw.telangana.gov.in',
            'Scholarship for SC students from Telangana to pursue higher education abroad.'
        ),
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO scholarships
            (name, min_gpa, max_income, required_course, required_state,
             category, gender_req, amount, deadline, apply_link, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', scholarships)

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
