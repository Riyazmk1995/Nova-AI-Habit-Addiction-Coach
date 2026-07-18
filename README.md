# Nova - AI Habit & Addiction Coach

Nova is a Streamlit-based AI habit recovery dashboard designed to help users manage and reduce harmful habits using evidence-based coaching techniques, live analytics, and Gemini-powered assistance.

## Overview

Nova combines:

- AI-guided habit coaching through Gemini
- CBT-inspired recovery support
- A daily check-in flow for personalized nudges
- Craving logging and behavior analytics
- Emergency coping tools for high-craving moments

The app is built for people working on habits such as:

- excessive screen time
- smoking or nicotine use
- procrastination
- sugar or junk food cravings
- alcohol or substance-related habits
- other behavioral addictions

## Features

### Dashboard
- Live clean streak timer
- Craving incident logging
- Recovery badges and progress tracking
- Personalized AI recovery assessment

### AI Chat
- Real-time conversational support with Nova
- Optional Google Search grounding for science-backed responses
- Quick prompt suggestions for motivation and coping

### Craving SOS
- Box breathing visual guide
- 5-4-3-2-1 grounding exercise
- Urge surfing technique
- Immediate AI emergency coach for urgent cravings

### Analytics
- Craving intensity trend graph
- Trigger analysis
- Mood distribution
- CBT tool usage breakdown
- Full craving log export in the interface

### Daily Check-In
- Mood and energy tracking
- Daily intention setting
- Personalized daily nudge from Nova

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- Google Generative AI SDK
- Custom CSS styling for a modern UI

## Project Structure

- `app.py` – Main Streamlit application logic
- `style.css` – Custom styling and UI customization
- `requirements.txt` – Python dependencies

## Setup

1. Clone or open this project folder.
2. Create and activate a virtual environment.
3. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Run the App

From the project directory, run:

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## How to Use

1. Complete the onboarding form with your name and habit information.
2. Review your personalized AI recovery assessment.
3. Log craving incidents on the Dashboard.
4. Use the Craving SOS tab whenever you need immediate support.
5. Visit the Analytics tab to understand behavioral patterns.
6. Submit the Daily Check-In to receive a personalized coaching message.

## Notes

- The app uses Gemini for AI-generated coaching and analysis.
- The recovery data can be exported/imported as JSON for backup and restore.
- The UI styling is customized in `style.css` for a polished dark-mode experience.

## License

This project is provided for educational or personal use. Add a license if you plan to share or distribute it publicly.
