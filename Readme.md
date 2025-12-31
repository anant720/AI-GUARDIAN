# 🛡️ AI Guardian – Scam Detection Engine

AI Guardian is an AI-powered security tool designed to detect scam and phishing messages in real time.
It combines machine learning and rule-based security checks to analyze messages and generate a risk score.

This project was built as a hackathon project to demonstrate a practical and real-world application of AI in cybersecurity.

---

## 🚀 Features

* Uses a scikit-learn machine learning model combined with rule-based checks for better accuracy
* Detects suspicious keywords, urgent or threatening phrases, risky links, and malicious domains
* Generates a risk score and classifies messages as **Safe**, **Suspicious**, or **Dangerous**
* Simple web-based demo to test messages live
* REST API endpoint `/analyse` for easy integration
* Logs all analyses in `guardian_log.csv`
* `/report` endpoint to flag incorrect detections

---

## 🧑‍💻 Getting Started

### Prerequisites

* Python 3.8 or above

### Installation & Setup

1. Navigate to the project folder:

   ```bash
   cd path/to/your/Guardian
   ```

2. Install required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the demo application:

   ```bash
   python start_demo.py
   ```

4. Open your browser and visit:

   ```
   http://127.0.0.1:5000
   ```

---

## 📂 Project Structure

```
Guardian/
├── .gitignore
├── config.py
├── LICENSE.md
├── README.md
├── requirements.txt
├── start_demo.py
│
├── src/
│   ├── __init__.py
│   ├── analyser.py
│   ├── rules.py
│   ├── ml_model.pkl
│   └── utils.py
│
├── webapp/
│   ├── app.py
│   ├── static/
│   │   └── style.css
│   └── templates/
│       └── index.html
│
├── guardian_log.csv
│
└── tests/
    ├── __init__.py
    └── test_analyser.py
```

---

## ⚙️ How It Works

1. The user submits a message
2. The message is cleaned and tokenized
3. Rule-based checks analyze keywords, urgency patterns, and suspicious links
4. The machine learning model predicts scam probability
5. A final risk score is calculated
6. The message is classified as **Safe**, **Suspicious**, or **Dangerous**

---

## 🌐 Live Demo

Run locally at:

```
http://127.0.0.1:5000
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

All contributions are welcome.

---

## 📜 License

This project is licensed under the MIT License.
See `LICENSE.md` for more information.
