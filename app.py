import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
from google.genai import types
import datetime
import json
import os
import tomllib

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Nova | AI Habit & Addiction Coach",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# LOAD CUSTOM CSS — cached so file is only read once per session
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _read_css():
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

_css = _read_css()
if _css:
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GEMINI CLIENT — created once, reused across all reruns
# ─────────────────────────────────────────────
def _load_gemini_api_key():
    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(env_name, "")
        if value and value.strip():
            return value.strip()

    try:
        for secret_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            value = st.secrets.get(secret_name, "")
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception:
        pass

    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "rb") as f:
                config = tomllib.load(f)
            for secret_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                value = config.get(secret_name, "")
                if isinstance(value, str) and value.strip():
                    return value.strip()
        except Exception:
            pass

    return ""

GEMINI_API_KEY = _load_gemini_api_key()
MODEL = "gemini-2.5-flash"

if not GEMINI_API_KEY:
    st.error("Missing Gemini API key. Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in your Streamlit secrets or environment variables.")
    st.stop()

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)

client = get_gemini_client()

NOVA_SYSTEM_PROMPT = (
    "You are Nova, an empathetic, highly skilled AI Cognitive Behavioral Therapy (CBT) and Habit Recovery Coach. "
    "You help users reduce or overcome harmful habits such as excessive screen time, smoking, procrastination, sugar dependency, "
    "caffeine, alcohol, or any substance/behavioral addiction. "
    "Use evidence-based CBT principles, motivational interviewing, mindfulness, and behavioral activation. "
    "Speak with warmth, compassion, and psychological insight. Keep responses concise and actionable. "
    "Use bullet points, numbered steps, and clear sections when helpful. "
    "When the user needs scientific/medical backing, use the Google Search tool to find reputable sources "
    "(Mayo Clinic, NIH, APA, PubMed, Harvard Health) and cite them clearly. "
    "Never be judgmental. Always encourage progress, no matter how small."
)

# ─────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────
DEFAULTS = {
    "habit_name": "",
    "habit_details": "",
    "user_name": "",
    "onboarded": False,
    "clean_since": None,
    "cravings_log": [],
    "chat_history": [],
    "daily_nudge": "",
    "nudge_date": None,
    "ai_assessment": "",
    "assessment_done": False,
    "checkin_date": None,
    "daily_mood": "",
    "daily_goal": "",
    "analytics_insight": "",
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────
def get_streak_seconds():
    if st.session_state.clean_since is None:
        return 0
    return max(0, (datetime.datetime.now() - st.session_state.clean_since).total_seconds())

def fmt_streak(s):
    d, rem = divmod(int(s), 86400)
    h, rem = divmod(rem, 3600)
    m, sec = divmod(rem, 60)
    return f"{d}d {h:02d}h {m:02d}m {sec:02d}s"

def reset_streak():
    st.session_state.clean_since = datetime.datetime.now()
    st.toast("Streak reset. Recovery is non-linear — keep going! 🌱", icon="🔄")

def get_badges(seconds):
    items = [
        ("👣", "First Hour",       "Completed 1 hour",     3600),
        ("🌅", "Half Day",         "12 hours clear",        43200),
        ("☀️", "Full Day",         "24 hours habit-free",   86400),
        ("⚡", "3-Day Warrior",    "3 days of control",     259200),
        ("🏆", "Week Champion",    "7 full days",           604800),
        ("🧘", "Fortnight Hero",   "14 days of clarity",    1209600),
    ]
    return [{"icon": ic, "name": nm, "desc": ds, "unlocked": seconds >= req}
            for ic, nm, ds, req in items]

def export_data():
    data = {
        "user_name": st.session_state.user_name,
        "habit_name": st.session_state.habit_name,
        "habit_details": st.session_state.habit_details,
        "clean_since": st.session_state.clean_since.isoformat() if st.session_state.clean_since else None,
        "cravings_log": st.session_state.cravings_log,
    }
    return json.dumps(data, indent=2)

def import_data(f):
    try:
        data = json.load(f)
        st.session_state.user_name = data.get("user_name", "")
        st.session_state.habit_name = data.get("habit_name", "")
        st.session_state.habit_details = data.get("habit_details", "")
        cs = data.get("clean_since")
        st.session_state.clean_since = datetime.datetime.fromisoformat(cs) if cs else None
        st.session_state.cravings_log = data.get("cravings_log", [])
        st.session_state.onboarded = True
        st.toast("Recovery profile restored! ✅", icon="✅")
    except Exception as e:
        st.error(f"Import failed: {e}")

# ─────────────────────────────────────────────
# AI FUNCTIONS
# ─────────────────────────────────────────────
def generate_nova_response(prompt, enable_search=False):
    """Non-streaming Gemini call, used for background generation."""
    config = types.GenerateContentConfig(
        system_instruction=NOVA_SYSTEM_PROMPT,
        temperature=0.7,
    )
    if enable_search:
        config.tools = [{"google_search": {}}]
    try:
        response = client.models.generate_content(
            model=MODEL, contents=prompt, config=config
        )
        citations = []
        try:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks or []:
                if chunk.web:
                    citations.append({"title": chunk.web.title, "uri": chunk.web.uri})
        except Exception:
            pass
        return response.text, citations
    except Exception as e:
        return f"⚠️ Error: {str(e)}", []

def stream_nova_response(prompt, enable_search=False):
    """Streaming Gemini call — yields tokens in real-time inside st.chat_message."""
    config = types.GenerateContentConfig(
        system_instruction=NOVA_SYSTEM_PROMPT,
        temperature=0.7,
    )
    if enable_search:
        config.tools = [{"google_search": {}}]
    try:
        full_text = ""
        placeholder = st.empty()
        for chunk in client.models.generate_content_stream(
            model=MODEL, contents=prompt, config=config
        ):
            if chunk.text:
                full_text += chunk.text
                placeholder.markdown(full_text + "▌")
        placeholder.markdown(full_text)
        return full_text, []
    except Exception as e:
        err = f"⚠️ Error: {str(e)}"
        st.error(err)
        return err, []

def generate_nudge():
    """Generate a daily motivational nudge — only called once per day."""
    secs = get_streak_seconds()
    prompt = (
        f"User: {st.session_state.user_name or 'the user'}. "
        f"Habit: '{st.session_state.habit_name}'. "
        f"Context: {st.session_state.habit_details}. "
        f"Clean streak: {fmt_streak(secs)}. "
        "Write ONE short (2-3 sentence) motivational daily message that is personalized, warm, and actionable. "
        "No greetings or sign-offs. Just the insight."
    )
    text, _ = generate_nova_response(prompt)
    st.session_state.daily_nudge = text
    st.session_state.nudge_date = datetime.date.today().isoformat()

def generate_assessment():
    """Generate initial habit assessment — called once on onboarding."""
    prompt = (
        f"User '{st.session_state.user_name}' wants to overcome: '{st.session_state.habit_name}'. "
        f"Triggers/context: {st.session_state.habit_details}. "
        "As their CBT coach:\n"
        "1. Top 3 psychological drivers (1-2 sentences each).\n"
        "2. Key withdrawal risks to watch.\n"
        "3. A 3-phase recovery roadmap (Week 1 / Week 2-4 / Month 2+) with one key action each.\n"
        "4. One science-backed coping technique specific to this habit.\n"
        "Under 300 words. Clear headers and bullet points."
    )
    text, _ = generate_nova_response(prompt, enable_search=True)
    st.session_state.ai_assessment = text
    st.session_state.assessment_done = True

def get_ai_analytics_insight():
    """One-shot analytics insight generation."""
    if not st.session_state.cravings_log:
        return "No data yet."
    df = pd.DataFrame(st.session_state.cravings_log)
    top_trigger = df["trigger"].value_counts().idxmax() if "trigger" in df else "unknown"
    top_mood = df["mood"].value_counts().idxmax() if "mood" in df else "unknown"
    avg_sev = df["severity"].mean() if "severity" in df else 5
    cbt_rate = df["cbt_completed"].mean() * 100 if "cbt_completed" in df else 0
    prompt = (
        f"Recovery data for '{st.session_state.habit_name}':\n"
        f"- Cravings logged: {len(df)}\n"
        f"- Top trigger: {top_trigger}\n"
        f"- Top mood: {top_mood}\n"
        f"- Avg intensity: {avg_sev:.1f}/10\n"
        f"- CBT usage rate: {cbt_rate:.0f}%\n\n"
        "Provide:\n"
        "1. 2-sentence pattern interpretation.\n"
        "2. Two specific lifestyle changes.\n"
        "3. One encouraging observation.\n"
        "Under 150 words. Warm and direct."
    )
    text, _ = generate_nova_response(prompt)
    return text

# ─────────────────────────────────────────────
# ONBOARDING SCREEN
# ─────────────────────────────────────────────
if not st.session_state.onboarded:
    st.markdown("""
    <div style="max-width:680px; margin:60px auto; text-align:center;">
        <div style="font-size:4rem; margin-bottom:12px;">🧬</div>
        <h1 style="font-size:2.8rem; font-weight:800;
            background:linear-gradient(90deg,#8B5CF6,#EC4899);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:8px;">
            Welcome to Nova
        </h1>
        <p style="color:#94A3B8; font-size:1.05rem; line-height:1.65; margin-bottom:32px;">
            Your personal AI-powered habit recovery coach. Nova uses CBT, motivational science,
            and real-time Gemini AI to help you break harmful habits — for good.
        </p>
    </div>
    """, unsafe_allow_html=True)

    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown("### 🚀 Let's get you set up")
        with st.form("onboarding_form"):
            user_name = st.text_input("Your first name:", placeholder="e.g. Alex")
            habit_opts = [
                "Excessive Screen Time / Social Media",
                "Smoking / Vaping / Nicotine",
                "Alcohol / Substance Use",
                "Procrastination",
                "Sugar / Junk Food Cravings",
                "Caffeine / Energy Drink Overuse",
                "Gambling / Gaming Compulsion",
                "Custom — I'll describe it below"
            ]
            habit_choice = st.selectbox("What habit are you working to overcome?", habit_opts)
            custom_habit = ""
            if habit_choice.startswith("Custom"):
                custom_habit = st.text_input("Describe your habit:", placeholder="e.g. Nail biting when anxious")
            habit_details = st.text_area(
                "Your triggers & context (the more detail, the better):",
                placeholder="e.g. I scroll TikTok for 3+ hours every evening. I feel anxious when I stop. Biggest trigger: deadline stress.",
                height=120
            )
            submitted = st.form_submit_button("Begin My Recovery Journey →", type="primary", use_container_width=True)

            if submitted:
                if not user_name.strip():
                    st.error("Please enter your name.")
                elif not habit_details.strip():
                    st.error("Please describe your triggers so Nova can personalize your plan.")
                else:
                    st.session_state.user_name = user_name.strip()
                    st.session_state.habit_name = custom_habit.strip() if custom_habit.strip() else habit_choice
                    st.session_state.habit_details = habit_details.strip()
                    st.session_state.clean_since = datetime.datetime.now()
                    st.session_state.onboarded = True
                    with st.spinner("Nova is building your personalized plan…"):
                        generate_assessment()
                        generate_nudge()
                    st.session_state.chat_history = [{
                        "role": "assistant",
                        "content": (
                            f"Hi {st.session_state.user_name}! 👋 I'm Nova, your personal habit recovery coach. "
                            f"I've reviewed your profile — you're working to overcome **{st.session_state.habit_name}**. "
                            "I'm here with you every step of the way. What's on your mind right now?"
                        ),
                        "citations": []
                    }]
                    st.rerun()

        st.markdown("---")
        st.markdown("<p style='text-align:center; color:#475569; font-size:0.85rem;'>Already have a recovery profile?</p>",
                    unsafe_allow_html=True)
        up = st.file_uploader("Restore from backup:", type=["json"], label_visibility="collapsed")
        if up:
            import_data(up)
            st.rerun()
    st.stop()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 8px 0;">
        <div style="font-size:2rem;">🧬</div>
        <h2 style="color:#8B5CF6; margin:4px 0 2px 0; font-size:1.3rem;">Nova</h2>
        <p style="color:#64748B; font-size:0.8rem; margin:0;">Recovery Coach</p>
    </div>
    <div style="background:rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.25);
         border-radius:12px; padding:12px 14px; margin:8px 0 16px 0;">
        <p style="color:#94A3B8; font-size:0.72rem; margin:0 0 2px 0;
           text-transform:uppercase; letter-spacing:0.05em;">Active Goal</p>
        <p style="color:#FFFFFF; font-weight:700; font-size:0.92rem; margin:0;">{st.session_state.habit_name}</p>
        <p style="color:#64748B; font-size:0.78rem; margin:4px 0 0 0;">Hi, {st.session_state.user_name}! 👋</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**⚙️ Settings**")
    if st.button("🔄 Reset Clean Streak", type="secondary", use_container_width=True):
        reset_streak()
        st.rerun()
    if st.button("🔁 Change Habit / Re-Onboard", type="secondary", use_container_width=True):
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

    st.markdown("---")
    st.markdown("**💾 Data**")
    st.download_button("⬇️ Export My Data", export_data(), "nova_recovery.json",
                       "application/json", use_container_width=True)
    up2 = st.file_uploader("⬆️ Import:", type=["json"])
    if up2:
        if st.button("Restore", use_container_width=True):
            import_data(up2)
            st.rerun()

# ─────────────────────────────────────────────
# GENERATE NUDGE — once per day, not on every rerun
# ─────────────────────────────────────────────
today_str = datetime.date.today().isoformat()
if st.session_state.nudge_date != today_str and st.session_state.daily_nudge == "":
    # Only generate if we don't have one at all; daily refresh is done in check-in
    generate_nudge()

# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(139,92,246,0.12) 0%,rgba(236,72,153,0.08) 100%);
     padding:20px 26px; border-radius:20px; border:1px solid rgba(255,255,255,0.05); margin-bottom:18px;">
    <h1 style="margin:0; font-size:1.9rem; color:#FFFFFF;">🧬 Nova Recovery Dashboard</h1>
    <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.92rem;">
        AI-powered habit tracking · CBT coaching · Live analytics
    </p>
</div>
""", unsafe_allow_html=True)

if st.session_state.daily_nudge:
    st.markdown(f"""
    <div style="background:rgba(139,92,246,0.08); border-left:4px solid #8B5CF6;
         border-radius:0 12px 12px 0; padding:13px 18px; margin-bottom:18px;">
        <p style="color:#A78BFA; font-size:0.72rem; font-weight:700; text-transform:uppercase;
           letter-spacing:0.06em; margin:0 0 5px 0;">✨ Nova's Daily Insight</p>
        <p style="color:#F1F5F9; font-size:0.97rem; font-style:italic; margin:0; line-height:1.55;">
            "{st.session_state.daily_nudge}"
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard",
    "💬 Nova Chat",
    "🚨 Craving SOS",
    "📈 Analytics",
    "🗓️ Daily Check-In"
])

# ═══════════════════════════════════════════════
# TAB 1 — DASHBOARD
# Live streak via client-side JS (zero Streamlit reruns)
# ═══════════════════════════════════════════════
with tab1:
    st.markdown("### ⏱️ Your Live Clean Streak")

    # Pass the start timestamp to JS; JS handles all ticking — no Python blocking
    clean_since_iso = st.session_state.clean_since.isoformat() if st.session_state.clean_since else datetime.datetime.now().isoformat()
    secs_now = int(get_streak_seconds())
    badges = get_badges(secs_now)
    unlocked_count = sum(1 for b in badges if b["unlocked"])
    cbt_count = sum(1 for log in st.session_state.cravings_log if log.get("cbt_completed"))

    # Static metric cards (no rerun needed — values only change on form submit)
    st.markdown(f"""
    <div class="metrics-grid">
        <div class="metric-card-custom">
            <div class="metric-value" id="live-streak" style="font-size:1.6rem; font-family:'Outfit',sans-serif;">
                Calculating…
            </div>
            <div class="metric-label">Live Clean Streak</div>
        </div>
        <div class="metric-card-custom">
            <div class="metric-value">{len(st.session_state.cravings_log)}</div>
            <div class="metric-label">Cravings Logged</div>
        </div>
        <div class="metric-card-custom">
            <div class="metric-value">{cbt_count}</div>
            <div class="metric-label">CBT Tools Used</div>
        </div>
        <div class="metric-card-custom">
            <div class="metric-value">{unlocked_count}/{len(badges)}</div>
            <div class="metric-label">Badges Unlocked</div>
        </div>
    </div>

    <script>
    (function() {{
        const start = new Date("{clean_since_iso}").getTime();
        const el = document.getElementById("live-streak");
        if (!el) return;
        function tick() {{
            const diff = Math.max(0, Math.floor((Date.now() - start) / 1000));
            const d = Math.floor(diff / 86400);
            const h = Math.floor((diff % 86400) / 3600);
            const m = Math.floor((diff % 3600) / 60);
            const s = diff % 60;
            el.innerText = d + "d " +
                String(h).padStart(2,"0") + "h " +
                String(m).padStart(2,"0") + "m " +
                String(s).padStart(2,"0") + "s";
        }}
        tick();
        setInterval(tick, 1000);
    }})();
    </script>
    """, unsafe_allow_html=True)

    # Badges (static, computed once)
    badge_html = '<div style="display:flex; flex-wrap:wrap; gap:10px; margin:16px 0;">'
    for b in badges:
        cls = "badge-unlocked" if b["unlocked"] else "badge-locked"
        badge_html += f"""
        <div class="{cls}">
            <span style="font-size:1.15rem;">{b["icon"]}</span>
            <div>
                <div style="font-weight:700; font-size:0.8rem;">{b["name"]}</div>
                <div style="font-size:0.7rem; opacity:0.8;">{b["desc"]}</div>
            </div>
        </div>"""
    badge_html += "</div>"
    st.markdown(badge_html, unsafe_allow_html=True)

    st.markdown("---")

    col_form, col_assess = st.columns([3, 2])

    with col_form:
        st.markdown("### 📝 Log a Craving Incident")
        st.caption("Recording cravings builds pattern awareness — one of the most powerful CBT interventions.")
        with st.form("craving_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                severity = st.slider("Craving Intensity:", 1, 10, 5)
                mood = st.selectbox("Current Mood:", [
                    "Stressed", "Anxious", "Bored", "Fatigued",
                    "Lonely", "Celebratory", "Restless", "Depressed", "Overwhelmed"
                ])
            with c2:
                trigger = st.selectbox("Immediate Trigger:", [
                    "Boredom / Idleness", "Work / Academic Stress",
                    "Social Media Notification", "Environmental Cue",
                    "Peer / Social Pressure", "Fatigue / Sleep Deprivation",
                    "Emotional Pain", "Habit Autopilot", "Other"
                ])
                location = st.selectbox("Where are you?", [
                    "Home", "Work / Office", "Social Situation",
                    "Commuting", "In Bed", "Other"
                ])
            notes = st.text_input("Quick note (optional):", placeholder="What were you doing?")
            cbt_used = st.checkbox("I used a mindfulness or CBT tool to manage this craving")
            if st.form_submit_button("📋 Record Craving", type="primary", use_container_width=True):
                st.session_state.cravings_log.append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "severity": severity, "mood": mood,
                    "trigger": trigger, "location": location,
                    "cbt_completed": cbt_used, "notes": notes
                })
                st.toast("Craving logged! Awareness is your superpower 🧠", icon="📝")
                st.rerun()

    with col_assess:
        st.markdown("### 🧠 AI Recovery Assessment")
        st.caption("Personalized plan powered by Gemini + live medical research.")
        if st.session_state.assessment_done:
            st.markdown(f"""
            <div style="background:rgba(15,23,42,0.7); border:1px solid rgba(255,255,255,0.08);
                 border-radius:14px; padding:16px; font-size:0.87rem; line-height:1.6;
                 color:#E2E8F0; max-height:340px; overflow-y:auto;">
                {st.session_state.ai_assessment.replace(chr(10), "<br>")}
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Refresh Assessment", use_container_width=True):
                with st.spinner("Refreshing…"):
                    generate_assessment()
                st.rerun()
        else:
            if st.button("🔬 Generate My AI Assessment", type="primary", use_container_width=True):
                with st.spinner("Analyzing your habit profile with live medical research…"):
                    generate_assessment()
                st.rerun()

# ═══════════════════════════════════════════════
# TAB 2 — AI CHAT (Streaming)
# ═══════════════════════════════════════════════
with tab2:
    st.markdown("### 💬 Talk to Nova")
    st.caption("Discuss cravings, triggers, or ask for science-backed recovery advice. Responses stream in real-time.")

    enable_search = st.toggle(
        "🔍 Enable Google Search Grounding (live medical references)",
        value=True,
        help="When on, Nova cites real sources — NIH, Mayo Clinic, APA, etc."
    )

    # Render chat history using native st.chat_message (fast, no HTML parsing overhead)
    for msg in st.session_state.chat_history:
        avatar = "👤" if msg["role"] == "user" else "🧬"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("citations"):
                unique = list({c["uri"]: c for c in msg["citations"]}.values())[:5]
                st.markdown("**📚 Sources:**")
                for c in unique:
                    name = (c["title"][:40] + "…") if len(c["title"]) > 40 else c["title"]
                    st.markdown(f"🔗 [{name}]({c['uri']})")

    user_input = st.chat_input(f"Talk to Nova about your {st.session_state.habit_name} journey…")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input, "citations": []})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Build context from only the last 6 exchanges (12 messages) to keep prompt short and fast
        recent = st.session_state.chat_history[-12:]
        context = "\n".join(
            f"{'User' if m['role']=='user' else 'Nova'}: {m['content']}"
            for m in recent
        )
        full_prompt = (
            f"User profile — Name: {st.session_state.user_name}, "
            f"Habit: {st.session_state.habit_name}, "
            f"Triggers: {st.session_state.habit_details[:200]}\n\n"
            f"Conversation:\n{context}"
        )

        with st.chat_message("assistant", avatar="🧬"):
            response_text, citations = stream_nova_response(full_prompt, enable_search=enable_search)

        st.session_state.chat_history.append({
            "role": "assistant", "content": response_text, "citations": citations
        })
        st.rerun()

    # Quick prompts
    st.markdown("---")
    st.markdown("**💡 Quick Topics:**")
    qcols = st.columns(4)
    quick_prompts = [
        ("🧠 Why am I craving?",  f"Explain the neuroscience of why I crave {st.session_state.habit_name}."),
        ("🌬️ Breathing tip",      "Give me a 2-minute breathing exercise to reduce craving intensity right now."),
        ("📅 Week 1 plan",         f"Give me a concrete day-by-day plan for my first week reducing {st.session_state.habit_name}."),
        ("💪 Stay motivated",      "I'm feeling weak and want to give in. Give me a powerful motivational message grounded in behavioral science."),
    ]
    for i, (label, prompt) in enumerate(quick_prompts):
        with qcols[i]:
            if st.button(label, use_container_width=True, key=f"qp_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": prompt, "citations": []})
                st.rerun()

# ═══════════════════════════════════════════════
# TAB 3 — CRAVING SOS
# ═══════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div style="text-align:center; padding:8px 0 18px 0;">
        <h2 style="color:#F43F5E; margin-bottom:6px;">🚨 Craving Emergency Kit</h2>
        <p style="color:#94A3B8; max-width:540px; margin:0 auto; font-size:0.93rem; line-height:1.5;">
            Craving right now? These clinically-proven tools down-regulate your stress response in under 5 minutes.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tool = st.radio("Choose your technique:", [
        "🌬️ Box Breathing",
        "🧩 5-4-3-2-1 Grounding",
        "🌊 Urge Surfing (CBT)",
        "🤖 AI Emergency Coach"
    ], horizontal=True)

    st.markdown("---")

    if "🌬️" in tool:
        st.markdown("""
        <div style="text-align:center; margin-bottom:14px;">
            <h3 style="color:#06B6D4; margin:0;">Navy SEAL Box Breathing</h3>
            <p style="color:#94A3B8; font-size:0.84rem; margin-top:4px;">
                Activates your parasympathetic nervous system. Reduces cortisol and craving intensity within 90 seconds.
            </p>
        </div>""", unsafe_allow_html=True)

        # Full client-side breathing visualiser — no Python sleep at all
        st.components.v1.html("""
        <div style="display:flex; flex-direction:column; align-items:center; background:#0F172A;
             padding:30px; border-radius:20px; border:1px solid rgba(255,255,255,0.08);
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
            <div style="position:relative; width:220px; height:220px; display:flex;
                 justify-content:center; align-items:center; margin-bottom:20px;">
                <div style="position:absolute; width:220px; height:220px; border-radius:50%;
                     border:2px dashed rgba(6,182,212,0.3);"></div>
                <div id="ring" style="width:80px; height:80px; border-radius:50%;
                     background:radial-gradient(circle,#06B6D4 0%,rgba(6,182,212,0.3) 100%);
                     transition:all 4s cubic-bezier(0.4,0,0.2,1);
                     box-shadow:0 0 20px rgba(6,182,212,0.4);"></div>
                <div id="timer" style="position:absolute; font-size:2rem; font-weight:800; color:white;">4</div>
            </div>
            <div id="phase" style="font-size:1.6rem; font-weight:800; color:#06B6D4;
                 text-transform:uppercase; letter-spacing:0.08em; margin-bottom:6px;">Get Ready</div>
            <div id="hint" style="color:#64748B; font-size:0.85rem; text-align:center;
                 max-width:260px; line-height:1.4;">
                The circle expands on inhale and contracts on exhale. Follow its rhythm.
            </div>
        </div>
        <script>
            const ring=document.getElementById('ring'),phase=document.getElementById('phase'),
                  timer=document.getElementById('timer'),hint=document.getElementById('hint');
            const steps=[
                {n:'Inhale', d:4, sz:'190px', bg:'radial-gradient(circle,#06B6D4 0%,rgba(6,182,212,0.4) 100%)', tc:'#06B6D4', sh:'0 0 35px rgba(6,182,212,0.6)', h:'Breathe deep into your belly slowly'},
                {n:'Hold',   d:4, sz:'190px', bg:'radial-gradient(circle,#8B5CF6 0%,rgba(139,92,246,0.4) 100%)', tc:'#A78BFA', sh:'0 0 45px rgba(139,92,246,0.8)', h:'Hold gently — relax your shoulders'},
                {n:'Exhale', d:4, sz:'80px',  bg:'radial-gradient(circle,#EC4899 0%,rgba(236,72,153,0.4) 100%)', tc:'#F472B6', sh:'0 0 20px rgba(236,72,153,0.4)', h:'Slowly release all tension'},
                {n:'Hold',   d:4, sz:'80px',  bg:'radial-gradient(circle,#1E293B 0%,rgba(30,41,59,0.6) 100%)', tc:'#475569', sh:'0 0 8px rgba(255,255,255,0.05)', h:'Rest before the next breath'},
            ];
            let idx=0;
            function run(){
                const s=steps[idx];
                phase.innerText=s.n; phase.style.color=s.tc;
                hint.innerText=s.h;
                ring.style.width=s.sz; ring.style.height=s.sz;
                ring.style.background=s.bg; ring.style.boxShadow=s.sh;
                let cnt=s.d; timer.innerText=cnt;
                const iv=setInterval(()=>{ cnt--; timer.innerText=cnt>=0?cnt:'';
                    if(cnt<0){clearInterval(iv); idx=(idx+1)%4; run();} },1000);
            }
            setTimeout(run, 800);
        </script>
        """, height=380)

    elif "🧩" in tool:
        st.markdown("""<h3 style="color:#8B5CF6; margin:0 0 10px 0;">5-4-3-2-1 Sensory Grounding</h3>""",
                    unsafe_allow_html=True)
        st.caption("Pulls attention from the internal craving loop to external physical reality, reducing amygdala activation.")
        cols = st.columns(5)
        steps_data = [
            ("👀","5 — SEE","Name 5 distinct objects with detail: color, shape, texture."),
            ("🖐️","4 — FEEL","Physical contact: feet on floor, chair, air on skin, clothing."),
            ("👂","3 — HEAR","Close eyes. Identify 3 distinct sounds, near or far."),
            ("👃","2 — SMELL","Notice any scent: fresh, stale, food, fabric, soap."),
            ("👅","1 — TASTE","Focus on the current taste. Take a slow sip of water."),
        ]
        for i, (icon, title, desc) in enumerate(steps_data):
            with cols[i]:
                st.markdown(f"""
                <div style="background:rgba(139,92,246,0.08); border:1px solid rgba(139,92,246,0.2);
                     border-radius:14px; padding:16px; text-align:center; min-height:170px;">
                    <div style="font-size:2rem; margin-bottom:8px;">{icon}</div>
                    <div style="font-weight:700; color:#FFFFFF; font-size:0.83rem; margin-bottom:6px;">{title}</div>
                    <div style="color:#94A3B8; font-size:0.76rem; line-height:1.4;">{desc}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ I completed the 5-4-3-2-1 exercise", type="primary", use_container_width=True):
            st.session_state.cravings_log.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "severity": 4, "mood": "Craving SOS",
                "trigger": "Urge Emergency", "location": "Unknown",
                "cbt_completed": True, "notes": "Completed 5-4-3-2-1 Sensory Grounding."
            })
            st.toast("Logged! You just rewired your brain's response 🧠", icon="🧩")
            st.rerun()

    elif "🌊" in tool:
        st.markdown("""<h3 style="color:#EC4899; margin:0 0 10px 0;">Urge Surfing — Ride the Wave</h3>""",
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
**Cravings peak and pass within 15-20 minutes.** Observe them as passing sensations, not commands.

**Step 1 — Locate it:** Where in your body? Chest tightness? Restless hands?

**Step 2 — Describe objectively:** *"I feel warm tension in my chest and restless energy in my legs."*

**Step 3 — Watch it rise:** Observe with curiosity: *"This craving is peaking right now."*

**Step 4 — Breathe through it:** 3 slow breaths. *"This wave will break. I am safe."*

**Step 5 — Watch it pass:** Notice the intensity fading. You surfed a craving. 🏄
            """)
        with c2:
            st.markdown("""
            <div style="background:rgba(236,72,153,0.06); border:1px solid rgba(236,72,153,0.2);
                 border-radius:14px; padding:18px;">
                <h4 style="color:#FFFFFF; margin-top:0;">🧠 The Science</h4>
                <p style="color:#94A3B8; font-size:0.84rem; line-height:1.55;">
                    Validated by Dr. Alan Marlatt (UW). Activates the <b style="color:#F1F5F9;">prefrontal cortex</b>
                    while the <b style="color:#F1F5F9;">amygdala</b> naturally de-escalates — without suppression.
                    Studies show up to <b style="color:#F472B6;">38% reduction</b> in relapse rates vs willpower alone.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🌊 I surfed this craving wave!", type="primary", use_container_width=True):
                st.session_state.cravings_log.append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "severity": 6, "mood": "Craving SOS",
                    "trigger": "Urge Emergency", "location": "Unknown",
                    "cbt_completed": True, "notes": "Completed Urge Surfing."
                })
                st.toast("Brilliant! You just trained your brain 🌊", icon="🏄")
                st.rerun()

    elif "🤖" in tool:
        st.markdown("""<h3 style="color:#8B5CF6; margin:0 0 10px 0;">🤖 AI Emergency Coach</h3>""",
                    unsafe_allow_html=True)
        st.caption("Describe your craving right now — Nova responds immediately with personalized guidance.")
        emergency_input = st.text_area(
            "What are you feeling right now?",
            placeholder=f"e.g. I'm having a strong urge to {st.session_state.habit_name}. I'm stressed and feel like I need it...",
            height=110
        )
        if st.button("🚨 Get Immediate Help from Nova", type="primary", use_container_width=True):
            if emergency_input.strip():
                prompt = (
                    f"URGENT — user experiencing a craving RIGHT NOW. "
                    f"Habit: {st.session_state.habit_name}. They say: '{emergency_input}'\n\n"
                    "Respond immediately with:\n"
                    "1. Validation (1 sentence)\n"
                    "2. An immediate action they can take in the next 60 seconds\n"
                    "3. A brief reminder of why they started\n"
                    "Under 100 words. Warm, urgent, direct."
                )
                with st.spinner("Nova is responding…"):
                    response, _ = generate_nova_response(prompt)
                st.markdown(f"""
                <div style="background:rgba(139,92,246,0.1); border:1px solid rgba(139,92,246,0.3);
                     border-radius:14px; padding:18px; margin-top:12px; color:#F1F5F9;
                     font-size:0.96rem; line-height:1.6;">
                    {response.replace(chr(10), "<br>")}
                </div>""", unsafe_allow_html=True)
                st.session_state.cravings_log.append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "severity": 8, "mood": "Craving SOS",
                    "trigger": "Urge Emergency", "location": "Unknown",
                    "cbt_completed": True, "notes": f"AI Emergency Coach: {emergency_input[:80]}"
                })
            else:
                st.warning("Please describe what you're feeling.")

# ═══════════════════════════════════════════════
# TAB 4 — ANALYTICS
# ═══════════════════════════════════════════════
with tab4:
    st.markdown("### 📈 Behavioral Analytics & Patterns")

    if not st.session_state.cravings_log:
        st.info("📊 Log craving incidents on the Dashboard to generate your analytics.")
    else:
        df = pd.DataFrame(st.session_state.cravings_log)
        df["datetime"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("datetime")

        # AI Insight (on-demand only — not generated automatically)
        st.markdown("#### 🤖 AI Pattern Insight")
        if st.session_state.analytics_insight:
            st.markdown(f"""
            <div style="background:rgba(139,92,246,0.08); border:1px solid rgba(139,92,246,0.2);
                 border-radius:12px; padding:16px; color:#E2E8F0; font-size:0.91rem;
                 line-height:1.6; margin-bottom:16px;">
                {st.session_state.analytics_insight.replace(chr(10),'<br>')}
            </div>""", unsafe_allow_html=True)

        btn_label = "🔄 Refresh AI Analysis" if st.session_state.analytics_insight else "🔍 Generate AI Behavioral Analysis"
        if st.button(btn_label, type="primary"):
            with st.spinner("Nova is analyzing your patterns…"):
                st.session_state.analytics_insight = get_ai_analytics_insight()
            st.rerun()

        st.markdown("---")

        LAYOUT = dict(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#F8FAFC", margin=dict(l=10, r=10, t=30, b=10)
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Craving Intensity Over Time**")
            fig1 = px.line(df, x="timestamp", y="severity", markers=True,
                           color_discrete_sequence=["#EC4899"],
                           labels={"timestamp": "", "severity": "Intensity"})
            fig1.update_layout(**LAYOUT,
                               yaxis=dict(range=[0,10.5], gridcolor="rgba(255,255,255,0.06)"),
                               xaxis=dict(showgrid=False))
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            st.markdown("**Cravings by Trigger**")
            tc = df["trigger"].value_counts().reset_index()
            tc.columns = ["Trigger", "Count"]
            fig2 = px.bar(tc, x="Count", y="Trigger", orientation="h",
                          color_discrete_sequence=["#8B5CF6"])
            fig2.update_layout(**LAYOUT, showlegend=False,
                               xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                               yaxis=dict(showgrid=False))
            st.plotly_chart(fig2, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("**Mood During Cravings**")
            fig3 = px.pie(df, names="mood", hole=0.45,
                          color_discrete_sequence=px.colors.qualitative.Pastel)
            fig3.update_layout(**LAYOUT,
                               legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
            st.plotly_chart(fig3, use_container_width=True)

        with c4:
            st.markdown("**CBT Tool Usage Rate**")
            cbt_df = df["cbt_completed"].value_counts().reset_index()
            cbt_df.columns = ["CBT Used", "Count"]
            cbt_df["CBT Used"] = cbt_df["CBT Used"].map({True: "Used CBT ✅", False: "No Tool ❌"})
            fig4 = px.pie(cbt_df, values="Count", names="CBT Used", hole=0.45,
                          color="CBT Used",
                          color_discrete_map={"Used CBT ✅": "#10B981", "No Tool ❌": "#F43F5E"})
            fig4.update_layout(**LAYOUT,
                               legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("---")
        st.markdown("**📋 Full Craving Log**")
        disp = df[["timestamp","severity","mood","trigger","location","cbt_completed","notes"]].copy()
        disp.columns = ["Time","Intensity","Mood","Trigger","Location","CBT Used?","Notes"]
        disp["CBT Used?"] = disp["CBT Used?"].map({True: "✅ Yes", False: "❌ No"})
        st.dataframe(disp.style.background_gradient(subset=["Intensity"], cmap="RdPu"),
                     use_container_width=True)

# ═══════════════════════════════════════════════
# TAB 5 — DAILY CHECK-IN
# ═══════════════════════════════════════════════
with tab5:
    st.markdown("### 🗓️ Daily Check-In")
    st.caption("A quick daily reflection helps Nova personalize your coaching and nudges.")

    today = datetime.date.today().isoformat()
    already_done = st.session_state.checkin_date == today

    if already_done:
        st.success("✅ You've already checked in today! Come back tomorrow.")
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2);
             border-radius:12px; padding:16px; margin-top:12px;">
            <p style="color:#94A3B8; font-size:0.83rem; margin:0 0 3px 0;">Today's mood:</p>
            <p style="color:#F1F5F9; font-weight:700; margin:0 0 8px 0;">{st.session_state.daily_mood}</p>
            <p style="color:#94A3B8; font-size:0.83rem; margin:0 0 3px 0;">Today's intention:</p>
            <p style="color:#F1F5F9; font-weight:700; margin:0;">{st.session_state.daily_goal}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.form("checkin_form"):
            mood_today = st.select_slider("How are you feeling?", [
                "😞 Terrible","😕 Low","😐 Neutral","🙂 Okay","😊 Good","🌟 Great"
            ], value="😐 Neutral")
            energy = st.select_slider("Energy level:", [
                "🪫 Exhausted","😴 Tired","😐 Moderate","⚡ Energised","🚀 Pumped"
            ], value="😐 Moderate")
            craving_now = st.slider("Current craving intensity (0 = none):", 0, 10, 0)
            goal_today = st.text_input(
                "Set one intention for today:",
                placeholder=f"e.g. I will not use {st.session_state.habit_name} after 9 PM."
            )
            share_win = st.text_area(
                "Share a recent win or positive step (optional):",
                placeholder="e.g. Yesterday I went 6 hours without scrolling.",
                height=80
            )
            if st.form_submit_button("✅ Submit Daily Check-In", type="primary", use_container_width=True):
                st.session_state.daily_mood = mood_today
                st.session_state.daily_goal = goal_today
                st.session_state.checkin_date = today
                with st.spinner("Nova is crafting your personalized message…"):
                    prompt = (
                        f"User {st.session_state.user_name} daily check-in. "
                        f"Habit: {st.session_state.habit_name}. "
                        f"Mood: {mood_today}. Energy: {energy}. "
                        f"Craving now: {craving_now}/10. "
                        f"Intention: '{goal_today}'. Win: '{share_win}'. "
                        "Write a warm, 3-sentence coaching message: acknowledge mood, reinforce intention, one tip. "
                        "Be warm and energizing. Under 80 words."
                    )
                    msg, _ = generate_nova_response(prompt)
                st.session_state.daily_nudge = msg
                st.session_state.nudge_date = today
                st.success("Check-in complete!")
                st.markdown(f"""
                <div style="background:rgba(139,92,246,0.1); border-left:4px solid #8B5CF6;
                     border-radius:0 12px 12px 0; padding:16px; margin-top:12px; color:#F1F5F9;
                     font-size:0.96rem; line-height:1.6;">
                    <b style="color:#A78BFA;">Nova says:</b><br>{msg.replace(chr(10),'<br>')}
                </div>""", unsafe_allow_html=True)
                if craving_now >= 7:
                    st.warning("⚠️ High craving intensity detected! Head to the **🚨 Craving SOS** tab now.")
                st.rerun()
