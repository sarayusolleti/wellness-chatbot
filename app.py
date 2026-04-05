import streamlit as st
import sqlite3
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd
import matplotlib.pyplot as plt
import random
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------- DATABASE ----------
conn = sqlite3.connect('chat_history.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    message TEXT,
    sentiment TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# ---------- SENTIMENT ----------
sia = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    score = sia.polarity_scores(text)['compound']
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    return "neutral"

# ---------- RESPONSE ----------
def generate_response(sentiment, user_message):
    text = user_message.lower().split()

    distress_keywords = ["suicide","die","depressed","hopeless","sad","lonely","anxious","hurt","crying"]
    health_keywords = ["fever","vomit","pain","tired","weak","nausea","sick"]

    if any(word in text for word in health_keywords):
        return "🤒 You may not be feeling well. Rest, hydrate, and consult a doctor if needed."

    if any(word in text for word in distress_keywords):
        return "💛 You are not alone. Consider reaching out to someone you trust or a helpline."

    # Context-based upgrade
    if "exam" in text:
        return "📚 Exams can be stressful. Take breaks and stay calm!"

    positive = [
        "That’s amazing ✨",
        "Keep shining 🌸"
    ]
    negative = [
        "It’s okay to feel this way 💛",
        "You’re doing your best 🌿"
    ]
    neutral = [
        "Tell me more 🙂",
        "I’m listening 💬"
    ]

    if sentiment == "positive":
        return random.choice(positive)
    elif sentiment == "negative":
        return random.choice(negative)
    return random.choice(neutral)

# ---------- DB FUNCTIONS ----------
def save_message(sender, message, sentiment):
    c.execute("INSERT INTO messages (sender, message, sentiment) VALUES (?, ?, ?)",
              (sender, message, sentiment))
    conn.commit()

def get_messages():
    c.execute("SELECT sender, message, sentiment, timestamp FROM messages")
    return c.fetchall()

def clear_messages():
    c.execute("DELETE FROM messages")
    conn.commit()

# ---------- PDF ----------
def generate_pdf(pos, neg, neu):
    doc = SimpleDocTemplate("report.pdf")
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("Weekly Wellness Report", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Positive: {pos}", styles['Normal']))
    content.append(Paragraph(f"Negative: {neg}", styles['Normal']))
    content.append(Paragraph(f"Neutral: {neu}", styles['Normal']))
    content.append(Spacer(1, 12))

    if neg > pos:
        suggestion = "Consider taking PHQ-9 or GAD-7 mental health tests."
    elif pos > neg:
        suggestion = "Great job! Maintain your positive habits."
    else:
        suggestion = "Try journaling and mindfulness."

    content.append(Paragraph(f"Suggestion: {suggestion}", styles['Normal']))
    content.append(Spacer(1, 12))
    content.append(Paragraph("⚠️ Not a substitute for medical advice.", styles['Normal']))

    doc.build(content)

# ---------- UI ----------
st.set_page_config(page_title="Wellness Chatbot")

st.title("💛 Wellness Chatbot")

if st.button("Clear Chat"):
    clear_messages()
    st.rerun()

# ---------- INPUT ----------
with st.form("chat", clear_on_submit=True):
    user_input = st.text_input("How are you feeling?")
    submit = st.form_submit_button("Send")

    if submit and user_input:
        sentiment = analyze_sentiment(user_input)
        save_message("You", user_input, sentiment)

        reply = generate_response(sentiment, user_input)
        save_message("Bot", reply, sentiment)

# ---------- CHAT ----------
st.subheader("Chat")

for sender, msg, _, _ in get_messages():
    if sender == "You":
        st.write(f"🧑 {msg}")
    else:
        st.write(f"🤖 {msg}")

# ---------- MOOD ANALYSIS ----------
st.subheader("📊 Mood Report")

c.execute("""
SELECT sentiment, COUNT(*)
FROM messages WHERE sender='You'
GROUP BY sentiment
""")

data = c.fetchall()

if data:
    df = pd.DataFrame(data, columns=["sentiment", "count"])

    pos = df[df.sentiment=="positive"]["count"].sum()
    neg = df[df.sentiment=="negative"]["count"].sum()
    neu = df[df.sentiment=="neutral"]["count"].sum()

    total = pos + neg + neu

    pos_r = pos/total if total else 0
    neg_r = neg/total if total else 0
    neu_r = neu/total if total else 0

    # Graph
    plt.figure()
    plt.bar(df["sentiment"], df["count"])
    st.pyplot(plt)

    # ---------- SUGGESTIONS ----------
    st.subheader("🧠 Suggestions")

    if neg_r > 0.5:
        st.warning("High negative trend detected 💛 Consider taking PHQ-9 or GAD-7 tests.")
        st.markdown("https://www.mind-diagnostics.org")

    elif pos_r > 0.5:
        st.success("Great mood overall 🌈 Keep it up!")

    elif neu_r > 0.5:
        st.info("Try journaling or mindfulness 🌼")

    else:
        st.info("Mixed emotions — reflect and take care 💛")

    # ---------- PDF ----------
    if st.button("Download Report"):
        generate_pdf(pos, neg, neu)

        with open("report.pdf", "rb") as f:
            st.download_button("Download PDF", f, "report.pdf")

else:
    st.info("Start chatting to generate report")

# ---------- DISCLAIMER ----------
st.caption("⚠️ This is not a substitute for professional help.")
