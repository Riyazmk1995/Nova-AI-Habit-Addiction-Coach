# 🧬 Nova – AI Habit & Addiction Coach

> **An AI-powered recovery companion that helps individuals build healthier habits using Cognitive Behavioral Therapy (CBT), Motivational Interviewing, behavioral analytics, and Google's Gemini AI.**

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red?logo=streamlit)
![Gemini](https://img.shields.io/badge/Google-Gemini%202.5-blue?logo=google)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

</p>

<p align="center">

## 🚀 Live Demo

### 👉 https://riyazmk1995-nova-ai-habit-addiction-coach-app-pp6mog.streamlit.app/

⭐ **Try Nova instantly in your browser — no installation required!**

</p>

---

# 🌟 Overview

**Nova** is an AI-powered Habit & Addiction Recovery Coach designed to provide personalized guidance, emotional support, and evidence-based recovery techniques.

Instead of simply tracking habits, Nova acts like a compassionate AI coach that helps users:

- Break unhealthy habits
- Reduce addictive behaviors
- Build positive routines
- Handle cravings
- Track recovery progress
- Stay motivated every day

The application combines **Generative AI**, **Behavioral Psychology**, **CBT techniques**, and **interactive analytics** into one intelligent recovery platform.

---

# 🎯 Problem Statement

Millions of people struggle with:

- Smoking
- Alcohol addiction
- Excessive screen time
- Social media addiction
- Sugar cravings
- Procrastination
- Gaming addiction
- Other behavioral habits

Most habit trackers only record progress.

Nova goes much further by providing:

- Personalized AI coaching
- Recovery planning
- Crisis support
- Daily motivation
- Behavioral insights
- Nearby professional care recommendations

---

# ✨ Key Features

## 🤖 AI Recovery Coach

Powered by **Google Gemini 2.5 Flash**

Nova provides:

- Personalized recovery plans
- CBT-based coaching
- Motivational Interviewing
- Mindfulness guidance
- Emotional support
- Habit replacement suggestions

---

## 📅 Daily Recovery Check-In

Users can log:

- Mood
- Energy level
- Daily intention
- Recovery goals

Nova generates a personalized AI coaching message based on the user's emotional state.

---

## 📊 Recovery Dashboard

Track progress using:

- Clean streak timer
- Craving history
- Recovery badges
- AI recovery assessment
- Progress indicators

---

## 📈 Recovery Analytics

Interactive Plotly dashboards provide insights into:

- Craving intensity trends
- Mood distribution
- Trigger analysis
- CBT technique usage
- Recovery progress over time

---

## 🚨 Craving SOS Toolkit

During high craving moments Nova provides immediate support through:

- 🫁 Box Breathing
- 🌊 Urge Surfing
- 🧠 5-4-3-2-1 Grounding Technique
- Emergency AI coaching

---

## 🏆 Recovery Achievement System

Users unlock milestones such as:

- First Hour
- Half Day
- One Day
- Three Days
- One Week
- Two Weeks

to reinforce positive behavior.

---

## 📍 Nearby Professional Care Search

Nova can help locate nearby:

- Psychologists
- Psychiatrists
- Clinics
- Hospitals
- Therapists

using:

- Google Places API
- OpenStreetMap
- Nominatim Geocoding
- Overpass API

Results are automatically sorted by distance.

---

## 💾 Recovery Data Backup

Users can:

- Export recovery data as JSON
- Restore previous sessions
- Continue recovery seamlessly

---

# 🏗️ System Architecture

```text
                   User
                     │
                     ▼
          Streamlit Web Interface
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼
 Gemini AI      Analytics Engine   Recovery Tracker
     │               │                │
     ▼               ▼                ▼
 CBT Coach      Plotly Dashboard   Streak Manager
     │
     ▼
 Emergency Recovery Support
     │
     ▼
 Nearby Care Search
 (Google Places + OpenStreetMap)
```

---

# 🧠 AI Capabilities

Nova uses Google's **Gemini 2.5 Flash** to provide:

- Personalized recovery coaching
- Motivational interviewing
- Habit analysis
- CBT recommendations
- Mindfulness exercises
- Scientific explanations
- Recovery encouragement

The assistant follows principles including:

- Cognitive Behavioral Therapy (CBT)
- Behavioral Activation
- Motivational Interviewing
- Compassionate communication
- Evidence-based guidance

---

# 📂 Project Structure

```
Nova-AI-Habit-Addiction-Coach/
│
├── app.py                     # Main Streamlit application
├── care_support.py            # Nearby care search utilities
├── style.css                  # Custom UI styling
├── requirements.txt
│
├── tests/
│   └── test_care_support.py
│
├── .streamlit/
│   └── config.toml
│
└── .github/
    └── workflows/
        └── python-tests.yml
```

---

# 🛠️ Technology Stack

| Category | Technologies |
|-----------|--------------|
| Language | Python |
| Frontend | Streamlit |
| AI Model | Google Gemini 2.5 Flash |
| Visualization | Plotly |
| Data Processing | Pandas |
| Location Services | Google Places API |
| Maps | OpenStreetMap |
| Geocoding | Nominatim |
| API Calls | Requests |
| Testing | PyTest |
| Styling | Custom CSS |

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/Riyazmk1995/Nova-AI-Habit-Addiction-Coach.git
```

Move into the project

```bash
cd Nova-AI-Habit-Addiction-Coach
```

Create virtual environment

```bash
python -m venv .venv
```

Activate environment

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.streamlit/secrets.toml`

```toml
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

GOOGLE_PLACES_API_KEY="YOUR_GOOGLE_PLACES_API_KEY"
```

Alternatively use environment variables:

```bash
GEMINI_API_KEY=xxxxxxxx

GOOGLE_PLACES_API_KEY=xxxxxxxx
```

---

# ▶️ Run the Application

```bash
streamlit run app.py
```

Open:

```
http://localhost:8501
```

---

# 🧪 Running Tests

```bash
pytest
```

---

# 🚀 Future Enhancements

- Voice conversation with Nova
- Wearable device integration
- Sleep tracking
- Smart reminders
- Therapist dashboard
- Recovery community
- AI relapse prediction
- Multi-language support
- Mobile application
- Weekly PDF recovery reports

---

# 🔒 Responsible AI

Nova is designed to support—not replace—professional medical or psychological care.

The AI:

- Avoids judgmental language
- Encourages evidence-based recovery
- Promotes healthy coping strategies
- Suggests professional help when appropriate
- Supports users with empathy and compassion

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repository

2. Create a feature branch

```bash
git checkout -b feature-name
```

3. Commit your changes

```bash
git commit -m "Added new feature"
```

4. Push

```bash
git push origin feature-name
```

5. Open a Pull Request

---

# 📄 License

This project is released under the **MIT License**.

---

# 👨‍💻 Author

**Riyaz Khorasi**

AI/ML Engineer | Generative AI | Agentic AI | LLMs | RAG | Multi-Agent Systems

GitHub

https://github.com/Riyazmk1995

LinkedIn

https://linkedin.com/in/riyazmk1995

---

⭐ If you found this project useful, consider giving it a **Star** on GitHub.
