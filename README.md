<h1 align="center">🩺 AyushScan</h1>

<p align="center">
  <b>A medical bill analyzer and AI health assistant designed for Bharat 🇮🇳</b><br>
  <i>Built for Code for Bharat Hackathon 2025</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Flask-WebApp-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/AI-Chatbot-green?style=for-the-badge"/>
</p>

---

## 🎥 Live Demo

<p align="center">
  <a href="https://www.youtube.com/watch?v=YOUR_VIDEO_ID">
    <img src="https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg" alt="AyushScan Demo" width="60%" />
  </a><br>
  <i>🔗 Click the image to view the full demo (Unlisted YouTube)</i>
</p>

---

## 🚀 What is AyushScan?

> AyushScan is a powerful AI-powered web application that allows users to scan medical bills, detect overcharges, get simplified explanations for each charge, and receive hospital recommendations — all in a user-friendly, multilingual interface.

---

## 🌟 Features

<table>
<tr>
<td>📄 <b>Bill Scanner</b></td>
<td>Extracts and analyzes medical bills with overcharge detection and clarity.</td>
</tr>
<tr>
<td>💬 <b>Ask Didi: AI Chatbot</b></td>
<td>Friendly chatbot trained to answer health, nutrition, and billing queries (Hindi, English, Hinglish).</td>
</tr>
<tr>
<td>🏥 <b>Nearby Hospitals</b></td>
<td>Shows affordable hospital options based on location.</td>
</tr>
<tr>
<td>🧾 <b>User Dashboard</b></td>
<td>Tracks uploaded bills, user profile, and scanned history.</td>
</tr>
<tr>
<td>🔐 <b>Secure Authentication</b></td>
<td>Sign-up/login with password, OTP for update/reset, account delete options.</td>
</tr>
</table>

---

## 🧠 Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python (Flask), Google Generative AI (Gemini API)
- **Database**: SQLite
- **Deployment Ready**: Runs locally, deployable on Render/Heroku

---

## 📌 How to Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/ayushscan.git
cd ayushscan

# 2. Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py

# App will start on http://127.0.0.1:5000
