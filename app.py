"""
ScholarPath – AI Chatbot Scholarship Finder
Flask backend with free-form NLP conversation and Rule Engine.
Behaves like Gemini: user can describe themselves naturally, bot extracts
details and asks follow-up only for what's missing.
Improvements:
  - Smarter name extraction: stops at known keywords or special characters
  - Field correction: "it's X not Y", "my name is actually X" overwrites stored values
  - Fuzzy matching via rapidfuzz for course/year/category/gender/state typos
"""
import re
from flask import Flask, render_template, request, jsonify, session
from models import init_db, get_all_scholarships
from rule_engine import RuleEngine

app = Flask(__name__)
app.secret_key = 'scholarpath-secret-2026'

with app.app_context():
    init_db()

engine = RuleEngine()

# ── Profile field metadata ─────────────────────────────────────────────────────
FIELDS = [
    {'key': 'name',     'label': 'your full name'},
    {'key': 'course',   'label': 'your course (e.g. B.Tech, MBBS, B.Sc…)'},
    {'key': 'year',     'label': 'your year of study (e.g. 1st Year, 2nd Year…)'},
    {'key': 'gpa',      'label': 'your GPA/CGPA (out of 10, e.g. 8.5)'},
    {'key': 'income',   'label': 'your annual family income in ₹ (e.g. 4,50,000)'},
    {'key': 'category', 'label': 'your category — **General**, **OBC**, **SC**, or **ST**'},
    {'key': 'gender',   'label': 'your gender — **Male**, **Female**, or **Other**'},
    {'key': 'state',    'label': 'your home state (e.g. Telangana, Maharashtra…)'},
]
FIELD_KEYS = [f['key'] for f in FIELDS]

# List of Indian states for extraction (no short abbreviations — handled separately)
INDIAN_STATES = [
    'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
    'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
    'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya',
    'mizoram', 'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim',
    'tamil nadu', 'telangana', 'tripura', 'uttar pradesh', 'uttarakhand',
    'west bengal', 'delhi', 'jammu and kashmir', 'ladakh', 'puducherry',
    'chandigarh', 'andaman', 'lakshadweep',
]

# Short state abbreviations — matched only as whole words after explicit state context
STATE_ABBREVIATIONS = {
    'ap':  'Andhra Pradesh',
    'ts':  'Telangana',
    'up':  'Uttar Pradesh',
    'mp':  'Madhya Pradesh',
    'hp':  'Himachal Pradesh',
    'jk':  'Jammu And Kashmir',
    'wb':  'West Bengal',
    'tn':  'Tamil Nadu',
}

# Course keyword → normalized name (regex → value)
COURSE_MAP = {
    r'\bb\.?\s*tech\b':     'B.Tech',
    r'\bm\.?\s*tech\b':     'M.Tech',
    r'\bb\.?\s*e\.?\b':     'B.E.',
    r'\bm\.?\s*e\.?\b':     'M.E.',
    r'\bmbbs\b':            'MBBS',
    r'\bmd\b':              'M.D.',
    r'\bms\b':              'M.S.',
    r'\bbsc?\b|\bb\.?\s*sc\b':   'B.Sc',
    r'\bmsc?\b|\bm\.?\s*sc\b':   'M.Sc',
    r'\bbcom?\b|\bb\.?\s*com\b': 'B.Com',
    r'\bmcom?\b|\bm\.?\s*com\b': 'M.Com',
    r'\bba\b|\bb\.?\s*a\.?\b':   'B.A.',
    r'\bma\b|\bm\.?\s*a\.?\b':   'M.A.',
    r'\bmba\b':             'MBA',
    r'\bbca\b':             'BCA',
    r'\bmca\b':             'MCA',
    r'\bdiploma\b':         'Diploma',
    r'\bphd\b|\bph\.?\s*d\.?\b': 'Ph.D',
    r'\bllb\b|\bll\.?\s*b\.?\b': 'LLB',
    r'\bllm\b|\bll\.?\s*m\.?\b': 'LLM',
    r'\bbpharm\b|\bb\.?\s*pharm\b': 'B.Pharm',
    r'\bmpharm\b|\bm\.?\s*pharm\b': 'M.Pharm',
    r'\bbarch\b|\bb\.?\s*arch\b':   'B.Arch',
    r'\bengineering\b|\bengg?\.?\b|\beng\.?\b|\benginering\b|\bengineerin\b': 'B.Tech',
    r'\bmedical\b':         'MBBS',
    r'\blaw\b':             'LLB',
}

YEAR_MAP = {
    'first': '1st Year', '1st': '1st Year', '1st year': '1st Year', '1 year': '1st Year',
    'second': '2nd Year', '2nd': '2nd Year', '2nd year': '2nd Year', '2 year': '2nd Year',
    'third': '3rd Year', '3rd': '3rd Year', '3rd year': '3rd Year', '3 year': '3rd Year',
    'fourth': '4th Year', '4th': '4th Year', '4th year': '4th Year', '4 year': '4th Year',
    'fifth': '5th Year', '5th': '5th Year', '5th year': '5th Year', '5 year': '5th Year',
}

# Regex for "year" with common typos
YEAR_WORD_RE = r'y(?:e+a?r?|(?:w|r|a)e?a?r?)s?'
# Regex for "lakh" with common typos (lakh, lakhs, lack, lacks, lak, lac, lacs)
LAKH_WORD_RE = r'la(?:kh?s?|c(?:ks?|s)?)\b'

# ── Stop-keywords for name extraction ─────────────────────────────────────────
# Walk tokens after a trigger phrase and stop when any of these appear
NAME_STOP_KEYWORDS = {
    # courses
    'btech', 'mtech', 'be', 'me', 'bsc', 'msc', 'bcom', 'mcom', 'ba', 'ma',
    'mba', 'bca', 'mca', 'mbbs', 'md', 'ms', 'phd', 'llb', 'llm', 'bpharm',
    'mpharm', 'barch', 'diploma', 'engineering', 'engg', 'eng', 'medical', 'law',
    # years
    'year', 'yr', 'first', 'second', 'third', 'fourth', 'fifth',
    '1st', '2nd', '3rd', '4th', '5th',
    # gender / category
    'male', 'female', 'other', 'man', 'woman', 'boy', 'girl',
    'general', 'obc', 'sc', 'st',
    # misc
    'student', 'studying', 'college', 'university', 'institute', 'school',
    'from', 'is', 'my', 'the', 'a', 'an', 'and', 'with', 'at', 'in',
    'gpa', 'cgpa', 'income', 'family', 'category', 'state', 'course',
    # common state names (prevent state from being grabbed as name)
    'telangana', 'maharashtra', 'karnataka', 'delhi', 'hyderabad',
    'andhra', 'pradesh', 'gujarat', 'rajasthan',
}

# ── Fuzzy matching tables ─────────────────────────────────────────────────────
FUZZY_COURSE_CHOICES = [
    'btech', 'mtech', 'be', 'me', 'mbbs', 'md', 'ms', 'bsc', 'msc',
    'bcom', 'mcom', 'ba', 'ma', 'mba', 'bca', 'mca', 'diploma', 'phd',
    'llb', 'llm', 'bpharm', 'mpharm', 'barch', 'engineering',
]
FUZZY_COURSE_NORMALIZED = {
    'btech': 'B.Tech', 'mtech': 'M.Tech', 'be': 'B.E.',  'me': 'M.E.',
    'mbbs': 'MBBS',   'md': 'M.D.',       'ms': 'M.S.',  'bsc': 'B.Sc',
    'msc': 'M.Sc',    'bcom': 'B.Com',    'mcom': 'M.Com','ba': 'B.A.',
    'ma': 'M.A.',     'mba': 'MBA',        'bca': 'BCA',  'mca': 'MCA',
    'diploma': 'Diploma', 'phd': 'Ph.D',   'llb': 'LLB',  'llm': 'LLM',
    'bpharm': 'B.Pharm', 'mpharm': 'M.Pharm', 'barch': 'B.Arch',
    'engineering': 'B.Tech',
}
FUZZY_YEAR_CHOICES = [
    '1st year', '2nd year', '3rd year', '4th year', '5th year',
    'first year', 'second year', 'third year', 'fourth year', 'fifth year',
]
FUZZY_YEAR_NORMALIZED = {
    '1st year': '1st Year',    'first year': '1st Year',
    '2nd year': '2nd Year',    'second year': '2nd Year',
    '3rd year': '3rd Year',    'third year': '3rd Year',
    '4th year': '4th Year',    'fourth year': '4th Year',
    '5th year': '5th Year',    'fifth year': '5th Year',
}
FUZZY_CATEGORY_CHOICES = ['general', 'obc', 'sc', 'st']
FUZZY_GENDER_CHOICES   = ['male', 'female', 'other']
FUZZY_GENDER_NORMALIZED = {'male': 'Male', 'female': 'Female', 'other': 'Other'}


# ── Helper: case-preserving name format ───────────────────────────────────────
def _fmt_name(raw: str) -> str:
    """Return raw as-is if ALL-CAPS (user typed their name in caps), else title-case."""
    alpha = re.sub(r'[^A-Za-z]', '', raw)
    return raw.strip() if (alpha and alpha == alpha.upper()) else raw.strip().title()


# ── Name token walker ─────────────────────────────────────────────────────────
def _extract_name_from_trigger(text: str, trigger_match) -> str | None:
    """
    After a trigger phrase match (e.g. "i'm ", "my name is "), walk tokens
    and stop at the first known-keyword token or non-letter character.
    Preserves ALL-CAPS names; title-cases mixed-case names.
    """
    after = text[trigger_match.end():]
    # Take only the part before the first non-letter/space/hyphen character
    name_segment = re.split(r"[^A-Za-z\s'\-]", after)[0]
    tokens = name_segment.split()
    name_tokens = []
    for tok in tokens:
        clean = tok.strip("'\",-.")
        if not clean:
            break
        if clean.lower() in NAME_STOP_KEYWORDS:
            break
        if re.match(r'^\d+', clean):        # digit-starting token → stop
            break
        name_tokens.append(clean)
    if name_tokens:
        return _fmt_name(' '.join(name_tokens))
    return None


# ── Correction helper ─────────────────────────────────────────────────────────
def _try_apply_correction(candidate: str, corrections: dict, profile: dict):
    """
    Guess which profile field `candidate` corrects and write into `corrections`.
    Priority: name (if already set) → category → gender.
    """
    from rapidfuzz.process import extractOne
    from rapidfuzz.fuzz import ratio

    cl = candidate.lower().strip()

    # Name: if name is already stored and candidate looks like a proper name
    if 'name' in profile:
        words = cl.split()
        if words and all(w not in NAME_STOP_KEYWORDS for w in words) and 1 <= len(words) <= 4:
            corrections['name'] = _fmt_name(candidate)
            return

    # Category
    cat_hit = extractOne(cl, FUZZY_CATEGORY_CHOICES, scorer=ratio, score_cutoff=70)
    if cat_hit:
        corrections['category'] = cat_hit[0].upper()
        return

    # Gender
    gen_hit = extractOne(cl, FUZZY_GENDER_CHOICES, scorer=ratio, score_cutoff=70)
    if gen_hit:
        corrections['gender'] = FUZZY_GENDER_NORMALIZED[gen_hit[0]]
        return


# ── Correction detector ───────────────────────────────────────────────────────
def detect_correction(text: str, profile: dict) -> dict:
    """
    Detect explicit correction intent and return {field: corrected_value}.
    Supported patterns:
      "it's X not Y"           → X is correct
      "not X, it's Y"          → Y is correct
      "my name is actually X"  → X (overwrites stored name)
      "no, I'm X" / "no it's X"
      "correct it to X" / "change it to X" / "it should be X"
      "X not Y"  (standalone)  → X is correct
    """
    t = text.strip()
    corrections = {}

    # "it's/it is X not Y"
    m = re.search(r"it[''`]?s\s+([A-Za-z][A-Za-z\s]{0,30}?)\s+not\s+\S+", t, re.I)
    if not m:
        m = re.search(r"it\s+is\s+([A-Za-z][A-Za-z\s]{0,30}?)\s+not\s+\S+", t, re.I)
    if m:
        _try_apply_correction(m.group(1).strip(), corrections, profile)

    # "not X, it's Y"
    if not corrections:
        m = re.search(r"not\s+\S+[,\s]+it[''`]?s\s+([A-Za-z][A-Za-z\s]{0,30}?)(?:[,.\n]|$)", t, re.I)
        if m:
            _try_apply_correction(m.group(1).strip(), corrections, profile)

    # "my name is [actually/really] X"  (explicit overwrite)
    if not corrections:
        m = re.search(
            r"my\s+name\s+is\s+(?:actually|really)?\s*([A-Za-z][A-Za-z\s]{1,30}?)(?:[,.\n]|$)",
            t, re.I
        )
        if m and 'name' in profile:
            corrections['name'] = _fmt_name(m.group(1).strip())

    # "no[,] I'm X" / "no[,] it's X"
    if not corrections:
        m = re.search(
            r"\bno[,]?\s+(?:i[''`]?m|it[''`]?s)\s+([A-Za-z][A-Za-z\s]{0,30}?)(?:[,.\n]|$)",
            t, re.I
        )
        if m:
            _try_apply_correction(m.group(1).strip(), corrections, profile)

    # "correct/change [it] to X" / "it should be X" / "update to X"
    if not corrections:
        m = re.search(
            r"(?:correct(?:\s+it)?|change(?:\s+it)?|should\s+be|update)\s+(?:to\s+)?([A-Za-z][A-Za-z\s]{0,30}?)(?:[,.\n]|$)",
            t, re.I
        )
        if m:
            _try_apply_correction(m.group(1).strip(), corrections, profile)

    # Standalone "X not Y"
    if not corrections:
        m = re.match(r'^([A-Za-z][A-Za-z]{1,30})\s+not\s+[A-Za-z][A-Za-z]{1,30}$', t, re.I)
        if m:
            _try_apply_correction(m.group(1).strip(), corrections, profile)

    return corrections


# ── Main NLP extractor ────────────────────────────────────────────────────────
def extract_profile_fields(text: str, existing: dict) -> dict:
    """
    Extract profile fields from free-form text.
    Uses regex first, then rapidfuzz as a fuzzy fallback.
    Only fills fields NOT already in `existing`.
    Returns dict of newly extracted fields.
    """
    from rapidfuzz.process import extractOne
    from rapidfuzz.fuzz import ratio, partial_ratio

    t  = text.strip()
    tl = t.lower()
    extracted = {}

    # ── Name ──────────────────────────────────────────────────────────────────
    if 'name' not in existing:
        trigger_patterns = [
            r"i[''`]?m\s+",
            r"i\s+am\s+",
            r"my\s+name\s+is\s+",
            r"my\s+name\s+",
            r"call\s+me\s+",
            r"this\s+is\s+",
            r"name\s*[:\-]?\s*",
        ]
        for pat in trigger_patterns:
            m = re.search(pat, t, re.I)
            if m:
                name = _extract_name_from_trigger(t, m)
                if name and len(name) > 1:
                    extracted['name'] = name
                    break

    # ── Course ────────────────────────────────────────────────────────────────
    if 'course' not in existing:
        # Regex (fast, exact / near-exact)
        for pattern, normalized in COURSE_MAP.items():
            if re.search(pattern, tl):
                extracted['course'] = normalized
                break
        # Fuzzy fallback
        if 'course' not in extracted:
            for word in re.findall(r'[a-z]+', tl):
                if len(word) >= 2:
                    hit = extractOne(word, FUZZY_COURSE_CHOICES, scorer=ratio, score_cutoff=80)
                    if hit:
                        extracted['course'] = FUZZY_COURSE_NORMALIZED[hit[0]]
                        break

    # ── Year of study ─────────────────────────────────────────────────────────
    if 'year' not in existing:
        ym = re.search(
            r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|\d+(?:st|nd|rd|th)?)\s*'
            + YEAR_WORD_RE, tl
        )
        if not ym:
            ym = re.search(r'\b' + YEAR_WORD_RE + r'\s*(\d+)\b', tl)
        if not ym:
            ym = re.search(r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\b', tl)

        if ym:
            raw = ym.group(0).strip().lower()
            for k, v in YEAR_MAP.items():
                if k in raw:
                    extracted['year'] = v
                    break
            if 'year' not in extracted:
                extracted['year'] = raw.title()
        else:
            # Fuzzy fallback for typo-heavy ordinals like "ssecond", "scond", "thrid"
            for word in re.findall(r'[a-z]+', tl):
                if len(word) >= 4:
                    hit = extractOne(word, FUZZY_YEAR_CHOICES, scorer=ratio, score_cutoff=75)
                    if hit:
                        extracted['year'] = FUZZY_YEAR_NORMALIZED[hit[0]]
                        break

    # ── GPA ───────────────────────────────────────────────────────────────────
    if 'gpa' not in existing:
        gpa_patterns = [
            r'\b(?:gpa|cgpa|grade|marks?)\s*(?:is|:|-|=)?\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:gpa|cgpa|out\s*of\s*10|\/\s*10)',
            r'\bscored?\s+(\d+\.?\d*)\b',
        ]
        for pat in gpa_patterns:
            m = re.search(pat, tl)
            if m:
                try:
                    val = float(m.group(1))
                    if 0 <= val <= 10:
                        extracted['gpa'] = str(val)
                        break
                except ValueError:
                    pass
        if 'gpa' not in extracted:
            lone = re.findall(r'\b([89]\.\d|[5-9]\.\d{1,2})\b', tl)
            if len(lone) == 1:
                val = float(lone[0])
                if 0 <= val <= 10:
                    extracted['gpa'] = str(val)

    # ── Income ────────────────────────────────────────────────────────────────
    if 'income' not in existing:
        lakh_m = re.search(
            r'(?:below|under|around|above|upto|up\s*to|less\s*than|more\s*than)?\s*'
            r'(\d+\.?\d*)\s*' + LAKH_WORD_RE,
            tl
        )
        if not lakh_m:
            lakh_m = re.search(
                r'(?:income|family)\s*(?:is|below|under|around|=|:)?\s*(\d+\.?\d*)\s*' + LAKH_WORD_RE,
                tl
            )
        if lakh_m:
            extracted['income'] = str(int(float(lakh_m.group(1)) * 100000))
        else:
            rupee_m = re.search(r'(?:₹|rs\.?\s*|income\s*(?:is|:|=)?\s*)(\d[\d,]*)', tl)
            if rupee_m:
                extracted['income'] = rupee_m.group(1).replace(',', '')
            else:
                inc_m = re.search(
                    r'\bincome\s*(?:is|[:=])?\s*(\d[\d,]+)\b'
                    r'|\b(\d[\d,]+)\s*(?:per\s*year|annual|yearly)\b',
                    tl
                )
                if inc_m:
                    raw = (inc_m.group(1) or inc_m.group(2)).replace(',', '')
                    extracted['income'] = raw

    # ── Category ──────────────────────────────────────────────────────────────
    # Year ordinal suffixes (st/nd/rd/th) must NOT be mistaken for categories.
    # Use a negative lookbehind for digits to avoid matching "1st", "2nd" etc.
    _YEAR_SUFFIX_RE = re.compile(r'\d(?:st|nd|rd|th)\b', re.I)
    _tl_no_ordinals = _YEAR_SUFFIX_RE.sub('', tl)   # strip "1st", "2nd" …

    if 'category' not in existing:
        cat_m = re.search(r'\b(general|obc|sc|st)\b', _tl_no_ordinals)
        if cat_m:
            extracted['category'] = cat_m.group(1).upper()
        else:
            # Fuzzy fallback — use longer words only (len>=4) to avoid
            # year-suffix fragments ("st", "nd", "rd") scoring 100% against SC/ST.
            # Also skip known stop-words and ordinal suffixes.
            _ORDINAL_SUFFIXES = {'st', 'nd', 'rd', 'th'}
            for word in re.findall(r'[a-z]+', _tl_no_ordinals):
                if len(word) >= 4 and word not in _ORDINAL_SUFFIXES:
                    hit = extractOne(word, FUZZY_CATEGORY_CHOICES, scorer=ratio, score_cutoff=75)
                    if hit:
                        extracted['category'] = hit[0].upper()
                        break

    # ── Gender ────────────────────────────────────────────────────────────────
    if 'gender' not in existing:
        g_map = {'male': 'Male', 'female': 'Female', 'other': 'Other',
                 'man': 'Male', 'woman': 'Female', 'boy': 'Male', 'girl': 'Female'}
        gm = re.search(r'\b(male|female|other|man|woman|boy|girl)\b', tl)
        if gm:
            extracted['gender'] = g_map[gm.group(1)]
        else:
            for word in re.findall(r'[a-z]+', tl):
                if len(word) >= 3:
                    hit = extractOne(word, FUZZY_GENDER_CHOICES, scorer=ratio, score_cutoff=80)
                    if hit:
                        extracted['gender'] = FUZZY_GENDER_NORMALIZED[hit[0]]
                        break

    # ── State ─────────────────────────────────────────────────────────────────
    if 'state' not in existing:
        sorted_states = sorted(INDIAN_STATES, key=len, reverse=True)
        found_state = None

        # 1. Check abbreviations only when preceded by a state-context keyword
        #    OR when the abbreviation appears standalone (very short word matching
        #    is only safe with explicit context to avoid false positives).
        abbrev_context_re = re.compile(
            r'(?:state|from|domicile|home|resident(?:\s+of)?|belong(?:s)?\s+to|i\s+am\s+from|i[''`]?m\s+from)'
            r'\s+([a-z]{2,3})\b',
            re.I
        )
        abbrev_m = abbrev_context_re.search(tl)
        if abbrev_m:
            code = abbrev_m.group(1).lower()
            if code in STATE_ABBREVIATIONS:
                found_state = STATE_ABBREVIATIONS[code]

        # Also allow bare abbreviations that are the ONLY word-like token
        # that could represent a state (only when unambiguous)
        if not found_state:
            for code, full_name in STATE_ABBREVIATIONS.items():
                # Match "my state is ts" or "state: ts" patterns
                if re.search(
                    r'(?:state|from|domicile)\s*(?:is|:|=)?\s*\b' + re.escape(code) + r'\b',
                    tl
                ):
                    found_state = full_name
                    break

        # 2. Exact regex match against full state names (longest first)
        if not found_state:
            for state in sorted_states:
                if re.search(r'\b' + re.escape(state) + r'\b', tl):
                    found_state = state.title()
                    break

        # 3. Fuzzy fallback — only on candidates with length >= 5 to avoid
        #    short abbreviations / college names matching multi-word state names.
        #    Use ratio (not partial_ratio) so partial substrings don't score high.
        if not found_state:
            words = tl.split()
            candidates = words + [' '.join(words[i:i+2]) for i in range(len(words) - 1)]
            for cand in candidates:
                if len(cand) >= 5:          # must be reasonably long
                    hit = extractOne(cand, sorted_states, scorer=ratio, score_cutoff=85)
                    if hit:
                        found_state = hit[0].title()
                        break

        if found_state:
            extracted['state'] = found_state

    return extracted


def get_missing_fields(profile: dict) -> list:
    """Return list of field metadata for fields not yet in profile."""
    return [f for f in FIELDS if f['key'] not in profile]


def build_bot_reply(newly_extracted: dict, profile: dict, missing: list) -> str:
    """
    Build a natural conversational reply:
    - Acknowledge what was just understood
    - Ask for missing fields naturally
    """
    lines = []

    # Acknowledge what we just extracted
    ack_parts = []
    field_labels = {
        'name':     lambda v: f"your name (**{v}**)",
        'course':   lambda v: f"your course (**{v}**)",
        'year':     lambda v: f"year of study (**{v}**)",
        'gpa':      lambda v: f"GPA (**{v}**)",
        'income':   lambda v: f"income (**₹{int(float(v)):,}**)",
        'category': lambda v: f"category (**{v}**)",
        'gender':   lambda v: f"gender (**{v}**)",
        'state':    lambda v: f"state (**{v}**)",
    }
    for key, val in newly_extracted.items():
        fmt = field_labels.get(key)
        if fmt:
            ack_parts.append(fmt(val))

    if ack_parts:
        if len(ack_parts) == 1:
            lines.append(f"Got it! I've noted {ack_parts[0]}. ✅")
        else:
            last = ack_parts[-1]
            rest = ', '.join(ack_parts[:-1])
            lines.append(f"Got it! I've noted {rest}, and {last}. ✅")

    # Ask for remaining fields
    if not missing:
        return '\n'.join(lines)   # caller handles "all done" case

    name_val = profile.get('name', '')
    address  = f"**{name_val.split()[0]}**" if name_val else "you"

    if len(missing) == len(FIELDS):
        return (
            "Hi there! 👋 I'm **ScholarBot**, your AI scholarship assistant.\n\n"
            "Tell me a bit about yourself and I'll find scholarships you're eligible for. "
            "You can share everything at once or one step at a time — whatever works for you!\n\n"
            "I'll need: **your name, course, year of study, GPA, annual family income, "
            "category** (General/OBC/SC/ST), **gender**, and **state**."
        )

    if len(missing) >= 4:
        lines.append(
            f"\nTo find your scholarships, I still need a few more details from {address}:\n"
            + '\n'.join(f"- {f['label'].capitalize()}" for f in missing)
        )
    elif len(missing) > 1:
        labels_str = ' and '.join(
            [', '.join(f['label'] for f in missing[:-1]), missing[-1]['label']]
            if len(missing) > 2
            else [missing[0]['label'], missing[1]['label']]
        )
        lines.append(f"\nAlmost there, {address}! I just need **{labels_str}**.")
    else:
        lines.append(f"\nOne last thing, {address} — I need **{missing[0]['label']}**.")

    return '\n'.join(lines)


def build_results_payload(profile: dict) -> dict:
    """Run the rule engine and return structured match data."""
    scholarships = get_all_scholarships()
    normalised = {
        'name':     profile.get('name', ''),
        'course':   profile.get('course', ''),
        'gpa':      float(profile.get('gpa', 0)),
        'income':   float(str(profile.get('income', 0)).replace(',', '')),
        'category': profile.get('category', '').upper(),
        'gender':   profile.get('gender', '').capitalize(),
        'state':    profile.get('state', '').strip().title(),
        'year':     profile.get('year', ''),
    }
    matches = engine.match(normalised, scholarships)
    return {'profile': normalised, 'matches': matches}


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    total = len(get_all_scholarships())
    return render_template('index.html', total_scholarships=total)


@app.route('/chat')
def chat():
    session.clear()
    session['profile'] = {}
    return render_template('chat.html')


@app.route('/chat/start', methods=['GET'])
def chat_start():
    """Return the opening greeting."""
    session.clear()
    session['profile'] = {}
    greeting = (
        "Hi there! 👋 I'm **ScholarBot**, your AI scholarship assistant.\n\n"
        "Tell me about yourself and I'll instantly find scholarships you qualify for. "
        "You can share everything at once — like:\n\n"
        "*\"I'm Priya, B.Tech 2nd year, GPA 8.2, Female, OBC, Telangana, income 3 lakhs\"*\n\n"
        "Or just start typing and we'll figure it out together! 😊"
    )
    return jsonify({
        'type': 'question',
        'bot_message': greeting,
        'fields_collected': 0,
    })


@app.route('/chat/message', methods=['POST'])
def chat_message():
    """
    Handle one free-form user message.
    Returns JSON: { type, bot_message, fields_collected, results? }
    """
    data       = request.get_json(force=True)
    user_input = (data.get('message') or '').strip()

    if not user_input:
        return jsonify({'type': 'error',
                        'bot_message': "I didn't catch that — could you type a bit more?"})

    profile = session.get('profile', {})

    # ── Handle "restart" keyword ──────────────────────────────────────────────
    if re.search(r'\b(restart|reset|start over|start again|new chat)\b', user_input, re.I):
        session['profile'] = {}
        return jsonify({
            'type': 'restart',
            'bot_message': (
                "🔄 **Restarted!** Let's begin fresh.\n\n"
                "Tell me about yourself — name, course, year, GPA, income, category, gender, and state. "
                "Share as much or as little as you like!"
            ),
            'fields_collected': 0,
        })

    # ── Correction detection (runs BEFORE normal extraction) ──────────────────
    corrections = detect_correction(user_input, profile)
    correction_applied = False
    if corrections:
        for field, new_val in corrections.items():
            old_val = profile.get(field, '—')
            profile[field] = new_val
        correction_applied = True
        session['profile'] = profile

    # ── Normal extraction (only fills still-missing fields) ──────────────────
    newly_extracted = extract_profile_fields(user_input, profile)
    profile.update(newly_extracted)
    session['profile'] = profile

    missing           = get_missing_fields(profile)
    fields_collected  = len(FIELD_KEYS) - len(missing)

    # Merge correction acks into newly_extracted for the reply builder
    if correction_applied:
        newly_extracted.update(corrections)

    # ── All collected → run the engine ───────────────────────────────────────
    if not missing:
        payload = build_results_payload(profile)
        name    = profile.get('name', 'there').split()[0]
        n       = len(payload['matches'])

        ack = ''
        if newly_extracted:
            ack_labels = [f['label'].split('(')[0].strip() for f in FIELDS
                          if f['key'] in newly_extracted]
            if ack_labels:
                ack = f"Got it — noted your {', '.join(ack_labels)}. ✅\n\n"

        if n == 0:
            msg = (
                ack +
                f"I've analysed your full profile, **{name}** 🔍\n\n"
                "Unfortunately, **no scholarships matched** your current profile.\n\n"
                "**Tips:**\n"
                "- Double-check your income and GPA values.\n"
                "- Telangana state students have several ePASS options — make sure your state is correct.\n"
                "- Type **restart** to try again with different details."
            )
        else:
            msg = (
                ack +
                f"Great news, **{name}**! 🎉 I've analysed your full profile.\n\n"
                f"You're eligible for **{n} scholarship{'s' if n > 1 else ''}**! Here are your matches 👇"
            )

        return jsonify({
            'type':             'results',
            'bot_message':      msg,
            'results':          payload['matches'],
            'fields_collected': fields_collected,
        })

    # ── Still collecting — build a natural follow-up ──────────────────────────
    if not newly_extracted and not correction_applied:
        name_val = profile.get('name', '')
        address  = f"**{name_val.split()[0]}**" if name_val else "you"

        if len(missing) == len(FIELDS):
            bot_msg = (
                "I'd love to help! Could you tell me a little about yourself?\n\n"
                "For example: *\"I'm Rahul, B.Tech 2nd year, GPA 8.0, OBC, Telangana, income 2 lakhs, Male\"*"
            )
        else:
            missing_labels = [f['label'] for f in missing]
            if len(missing_labels) == 1:
                bot_msg = f"I still need one more thing from {address} — **{missing_labels[0]}**."
            else:
                formatted = '\n'.join(f"- {lbl.capitalize()}" for lbl in missing_labels)
                bot_msg   = f"I couldn't quite parse that. Could you clarify these for {address}?\n\n{formatted}"
    else:
        bot_msg = build_bot_reply(newly_extracted, profile, missing)

    return jsonify({
        'type':             'question',
        'bot_message':      bot_msg,
        'fields_collected': fields_collected,
    })


@app.route('/chat/restart', methods=['POST'])
def chat_restart():
    session.clear()
    session['profile'] = {}
    return jsonify({
        'type': 'question',
        'bot_message': (
            "🔄 **Restarted!** Let's begin fresh.\n\n"
            "Tell me about yourself — name, course, year, GPA, income, category, gender, and state. "
            "Share as much or as little as you like!"
        ),
        'fields_collected': 0,
    })


@app.route('/api/scholarships')
def api_scholarships():
    return jsonify(get_all_scholarships())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
