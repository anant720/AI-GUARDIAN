AI Guardian - Scam Detection Engine
AI Guardian is a tool to detect scam and phishing messages in real time.
It uses machine learning and rule-based checks to give a risk score.
It was made for a hackathon as a practical AI security project.

Features

Uses scikit-learn model and rule checks for better accuracy
Scans for suspicious keywords, urgent phrases, risky links, and malicious domains
Gives risk score and marks message as Safe, Suspicious, or Dangerous
Simple web demo to test messages live
REST API endpoint /analyse for integration
Logs all analyses in guardian_log.csv
/report endpoint to flag wrong detections
Getting Started

Install Python 3.8 or above

Go to project folder using cd path/to/your/Guardian

Install requirements using pip install -r requirements.txt

Run demo using python start_demo.py

Open browser and go to http://127.0.0.1:5000

Project Structure
Guardian/

.gitignore

config.py

LICENSE.md

README.md

requirements.txt

start_demo.py

src/

init.py

analyser.py

rules.py

ml_model.pkl

utils.py

webapp/

static/style.css

templates/index.html

app.py

guardian_log.csv

tests/

init.py

test_analyser.py

How It Works

Message is cleaned and tokenized

Rules check for keywords, suspicious links, formats

ML model predicts scam probability

Risk score is calculated

Message is classified as Safe, Suspicious, or Dangerous

Live Demo
Run locally on http://127.0.0.1:5000

Contributing
You can fork the repo, make changes, and create a pull request

License
MIT License, see LICENSE.md
