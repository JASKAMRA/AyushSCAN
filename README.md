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
  <a href="https://youtu.be/pqgdbEKCr8Y" target="_blank">
    <img src="https://img.youtube.com/vi/pqgdbEKCr8Y/0.jpg" alt="AyushScan Demo" width="60%" />
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

<img width="213" height="213" alt="image" src="https://github.com/user-attachments/assets/9f9932eb-12eb-4b5b-bbc2-e050b904ce81" />



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
```

## 🔐 Environment Variables (`.env`)

To run **AyushScan** locally, you need to provide your **Gemini API key** using a `.env` file.

### 📄 Step-by-step:

1. **Create a file named** `.env` at the **root** of the project (same level as `app.py`).

2. Add the following line inside it:

   ```.env
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

3. You can get your **Google Gemini API key** from:

   👉 [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

4. The key is automatically loaded using `python-dotenv` which is already included in `requirements.txt`.

---

### ⚠️ Important Notes:

* Your `.env` file is **excluded from version control** using `.gitignore`.
* **Never upload `.env` to GitHub** — keep your keys safe!

---



