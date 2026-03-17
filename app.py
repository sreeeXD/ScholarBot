"""
ScholarPath – AI Chatbot Scholarship Finder
Flask backend with free-form NLP conversation and Rule Engine.
Behaves like Gemini: user can describe themselves naturally, bot extracts
details and asks follow-up only for what's missing.
"""
import re
import json
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

# List of Indian states for extraction
INDIAN_STATES = [
    'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
    'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
    'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya',
    'mizoram', 'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim',
    'tamil nadu', 'telangana', 'tripura', 'uttar pradesh', 'uttarakhand',
    'west bengal', 'delhi', 'jammu and kashmir', 'ladakh', 'puducherry',
    'chandigarh', 'andaman', 'lakshadweep', 'ap', 'ts', 'up', 'mp',
]

# Course keyword → normalized name
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
    r'\bengineering\b':     'B.Tech',
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


# ── NLP Extractor ─────────────────────────────────────────────────────────────

def extract_profile_fields(text: str, existing: dict) -> dict:
    """
    Extract profile fields from free-form text.
    Only fills fields not already in `existing`.
    Returns dict of newly extracted fields.
    """
    t = text.strip()
    tl = t.lower()
    extracted = {}

    # ── Name ──────────────────────────────────────────────────────────────────
    if 'name' not in existing:
        # Patterns: "I'm X", "I am X", "my name is X", "call me X"
        name_patterns = [
            r"i[''`]?m\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:[,.\n]|$)",
            r"my\s+name\s+is\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:[,.\n]|$)",
            r"i\s+am\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:[,.\n]|$)",
            r"call\s+me\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:[,.\n]|$)",
            r"this\s+is\s+([A-Za-z][A-Za-z\s]{1,30}?)(?:[,.\n]|$)",
        ]
        for pat in name_patterns:
            m = re.search(pat, t, re.I)
            if m:
                candidate = m.group(1).strip().rstrip('.,')
                # Reject if it's a common non-name word
                bad = {'obc', 'sc', 'st', 'male', 'female', 'general', 'student',
                       'studying', 'btech', 'tech', 'year', 'telangana', 'from'}
                if candidate.lower().split()[0] not in bad and len(candidate) > 1:
                    extracted['name'] = candidate.title()
                    break

    # ── Course ────────────────────────────────────────────────────────────────
    if 'course' not in existing:
        for pattern, normalized in COURSE_MAP.items():
            if re.search(pattern, tl):
                extracted['course'] = normalized
                break

    # ── Year of study ─────────────────────────────────────────────────────────
    if 'year' not in existing:
        # Match patterns like "2nd year", "second year", "year 2"
        ym = re.search(
            r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|\d+(?:st|nd|rd|th)?)\s*year\b',
            tl
        )
        if not ym:
            ym = re.search(r'\byear\s*(\d+)\b', tl)
        if ym:
            raw = ym.group(0).strip().lower()
            # Normalise
            for k, v in YEAR_MAP.items():
                if k in raw:
                    extracted['year'] = v
                    break
            if 'year' not in extracted:
                # Fallback: use raw matched text capitalised
                extracted['year'] = raw.title()

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
        # Last-resort: lone decimal between 5.0–9.9 if no other context
        if 'gpa' not in extracted:
            lone = re.findall(r'\b([89]\.\d|[5-9]\.\d{1,2})\b', tl)
            if len(lone) == 1:
                val = float(lone[0])
                if 0 <= val <= 10:
                    extracted['gpa'] = str(val)

    # ── Income ────────────────────────────────────────────────────────────────
    if 'income' not in existing:
        # "4 lakhs", "4L", "₹4,50,000", "4.5 lakh", raw numbers
        lakh_m = re.search(
            r'\b(\d+\.?\d*)\s*(?:l(?:akh)?s?|lac)\b',
            tl
        )
        if lakh_m:
            extracted['income'] = str(int(float(lakh_m.group(1)) * 100000))
        else:
            rupee_m = re.search(r'(?:₹|rs\.?\s*|income\s*(?:is|:|=)?\s*)(\d[\d,]*)', tl)
            if rupee_m:
                extracted['income'] = rupee_m.group(1).replace(',', '')
            else:
                # Last-resort: lone large number that could be income
                inc_m = re.search(
                    r'\bincome\s*(?:is|[:=])?\s*(\d[\d,]+)\b|\b(\d[\d,]+)\s*(?:per\s*year|annual|yearly)\b',
                    tl
                )
                if inc_m:
                    raw = (inc_m.group(1) or inc_m.group(2)).replace(',', '')
                    extracted['income'] = raw

    # ── Category ──────────────────────────────────────────────────────────────
    if 'category' not in existing:
        cat_m = re.search(r'\b(general|obc|sc|st)\b', tl)
        if cat_m:
            extracted['category'] = cat_m.group(1).upper()

    # ── Gender ────────────────────────────────────────────────────────────────
    if 'gender' not in existing:
        g_map = {'male': 'Male', 'female': 'Female', 'other': 'Other',
                 'man': 'Male', 'woman': 'Female', 'boy': 'Male', 'girl': 'Female'}
        gm = re.search(r'\b(male|female|other|man|woman|boy|girl)\b', tl)
        if gm:
            extracted['gender'] = g_map[gm.group(1)]

    # ── State ─────────────────────────────────────────────────────────────────
    if 'state' not in existing:
        # Try full state names first (longest first to avoid partial matches)
        sorted_states = sorted(INDIAN_STATES, key=len, reverse=True)
        for state in sorted_states:
            if re.search(r'\b' + re.escape(state) + r'\b', tl):
                # Title-case the state name for display
                extracted['state'] = state.title()
                break

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

    # ── Acknowledge what we just extracted ────────────────────────────────────
    ack_parts = []
    field_labels = {
        'name': lambda v: f"your name (**{v}**)",
        'course': lambda v: f"your course (**{v}**)",
        'year': lambda v: f"year of study (**{v}**)",
        'gpa': lambda v: f"GPA (**{v}**)",
        'income': lambda v: f"income (**₹{int(float(v)):,}**)",
        'category': lambda v: f"category (**{v}**)",
        'gender': lambda v: f"gender (**{v}**)",
        'state': lambda v: f"state (**{v}**)",
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

    # ── Ask for remaining fields ───────────────────────────────────────────────
    if not missing:
        return '\n'.join(lines)  # Caller handles the "all done" case

    name_val = profile.get('name', '')
    address = f"**{name_val.split()[0]}**" if name_val else "you"

    if len(missing) == len(FIELDS):
        # Nothing collected yet — just ask naturally
        return (
            f"Hi there! 👋 I'm **ScholarBot**, your AI scholarship assistant.\n\n"
            "Tell me a bit about yourself and I'll find scholarships you're eligible for. "
            "You can share everything at once or one step at a time — whatever works for you!\n\n"
            "I'll need: **your name, course, year of study, GPA, annual family income, "
            "category** (General/OBC/SC/ST), **gender**, and **state**."
        )

    if len(missing) >= 4:
        labels = ', '.join(f['label'] for f in missing)
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

    # ── Extract fields from this message ─────────────────────────────────────
    newly_extracted = extract_profile_fields(user_input, profile)
    profile.update(newly_extracted)
    session['profile'] = profile

    missing = get_missing_fields(profile)
    fields_collected = len(FIELD_KEYS) - len(missing)

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
    if not newly_extracted:
        # Couldn't extract anything new from this message
        name_val = profile.get('name', '')
        address  = f"**{name_val.split()[0]}**" if name_val else "you"

        if len(missing) == len(FIELDS):
            # No profile at all yet — re-prompt gently
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
                bot_msg = f"I couldn't quite parse that. Could you clarify these for {address}?\n\n{formatted}"
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
