"""
Rule-Based AI Engine
~~~~~~~~~~~~~~~~~~~~
Uses IF-THEN logic to match a student profile against scholarship
eligibility criteria stored in the database.
"""


class RuleEngine:
    """Matches a student dict against a list of scholarship dicts."""

    # Courses that are considered compatible with 'B.Tech'
    BTECH_ALIASES = {'b.tech', 'btech', 'be', 'b.e', 'engineering'}
    DIPLOMA_ALIASES = {'diploma'}

    def match(self, student: dict, scholarships: list) -> list:
        """
        Returns a list of dicts:
            { 'scholarship': <scholarship dict>, 'reasons': [str, ...] }
        """
        results = []
        for s in scholarships:
            matched, reasons = self._evaluate(student, s)
            if matched:
                results.append({
                    'scholarship': s,
                    'reasons': reasons
                })
        return results

    # ── Private helpers ────────────────────────────────────────────────────────

    def _evaluate(self, student: dict, s: dict):
        """
        Evaluate a single scholarship against the student profile.
        Returns (bool, list[str]).
        """
        reasons = []

        # ── 1. GPA Check ──────────────────────────────────────────────────────
        try:
            student_gpa = float(student.get('gpa', 0))
        except (TypeError, ValueError):
            student_gpa = 0.0

        min_gpa = float(s.get('min_gpa', 0))
        if student_gpa < min_gpa:
            return False, []
        if min_gpa > 0:
            reasons.append(f'GPA {student_gpa} ≥ required {min_gpa}')

        # ── 2. Income Check ───────────────────────────────────────────────────
        try:
            student_income = float(student.get('income', 0))
        except (TypeError, ValueError):
            student_income = 0.0

        max_income = float(s.get('max_income', 9_999_999))
        if student_income > max_income:
            return False, []
        if max_income < 9_000_000:
            reasons.append(
                f'Income ₹{int(student_income):,} ≤ limit ₹{int(max_income):,}'
            )

        # ── 3. Course Check ───────────────────────────────────────────────────
        req_course = (s.get('required_course') or 'Any').strip()
        student_course = (student.get('course') or '').strip()

        if req_course.lower() != 'any':
            if not self._course_matches(student_course, req_course):
                return False, []
            reasons.append(f'Course = {student_course}')

        # ── 4. State / Domicile Check ─────────────────────────────────────────
        req_state = (s.get('required_state') or 'Any').strip()
        student_state = (student.get('state') or '').strip()

        if req_state.lower() != 'any':
            if student_state.lower() != req_state.lower():
                return False, []
            reasons.append(f'Domicile = {student_state}')

        # ── 5. Category Check ─────────────────────────────────────────────────
        req_category = (s.get('category') or 'All').strip()
        student_category = (student.get('category') or '').strip()

        if req_category.lower() not in ('all', 'any', ''):
            if student_category.upper() != req_category.upper():
                return False, []
            reasons.append(f'Category = {student_category}')

        # ── 6. Gender Check ───────────────────────────────────────────────────
        req_gender = (s.get('gender_req') or 'Any').strip()
        student_gender = (student.get('gender') or '').strip()

        if req_gender.lower() != 'any':
            if student_gender.lower() != req_gender.lower():
                return False, []
            reasons.append(f'Gender = {student_gender}')

        # ── All checks passed ─────────────────────────────────────────────────
        if not reasons:
            reasons.append('Open to all eligible students')

        return True, reasons

    def _course_matches(self, student_course: str, req_course: str) -> bool:
        sc = student_course.lower().strip()
        rc = req_course.lower().strip()

        # Direct match
        if sc == rc:
            return True

        # Alias matching
        if rc in ('b.tech', 'btech'):
            return sc in self.BTECH_ALIASES
        if rc == 'diploma':
            return sc in self.DIPLOMA_ALIASES

        # Partial / keyword match
        return rc in sc or sc in rc
