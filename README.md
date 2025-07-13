<h1 align="center">📊 AyushScan</h1>

<p align="center"><i>AI-powered medical bill analyzer and health assistant for Bharat 🇮🇳</i></p>
<p align="center">("This is around 60-70% working right now")</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Flask-WebApp-orange?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Chatbot-AI-green?style=for-the-badge"/>
</p>

---

## 🎥 Demo Video

<p align="center">
  <a href="https://www.youtube.com/watch?v=YOUR_VIDEO_ID">
    <img src="https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg" alt="AyushScan Demo" width="60%" />
  </a><br>
  <i>Click the image to view the demo (Unlisted)</i>
</p>

---

## 🚀 What is AyushScan?

**AyushScan** is a smart healthcare web app that lets users upload medical bills, analyze them for overpricing using a curated dataset, and get quick AI-backed responses to medical queries. Designed especially for India's healthcare needs, it's a step toward accessible and transparent medical expense tracking.

---

## 🌟 Key Features

| Feature | Description |
|--------|-------------|
| 📄 Bill Scanner | Uploads and scans bills to detect overpriced medicines/services |
| 💬 AI Chatbot | Currently a basic Gemini-powered chatbot  |
| 🏥 Nearby Hospitals | Shows a static list based on location input (Google Maps API not yet integrated) |
| 🧾 User Dashboard | Displays past scans, profile info, and analysis history |
| 🔐 Auth System | Basic login/signup with sessions (password encryption not yet added) |

---

## 🚧 Room for Improvement

| Planned Feature | Current Status | Completion Target |
|----------------|----------------|-------------------|
| 🔒 Password Hashing | ❌ Not yet implemented | Will be added before hackathon submission |
| 🗺️ Google Maps API for Hospitals | ❌ Not used | Post-hackathon |
| ✅ Ayushman Bharat Scheme Filter | ⚠️ Planned | In-progress |
| 🎤 Voice Chat in Chatbot | ⚠️ Planned | Before final submission |
| 📧 OTP via Email | ✅ Functional (console log only) | Email delivery can be added later |

---

## Project Structure

<img width="185" height="154" alt="image" src="https://github.com/user-attachments/assets/26333d4e-56a4-47ff-bca6-68f4a7baa804" />


---

## 👤 Developers

->Akshita Sachdeva

->Jas Kamra

---
## 🛠️ How to Run Locally

```bash
# Clone the repository
git clone https://github.com/JASKAMRA/AyushSCAN
cd ayushscan

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Start the Flask app
python app.py

# Open in browser
http://127.0.0.1:5000


