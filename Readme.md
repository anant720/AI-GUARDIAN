--- /dev/null
+++ b/c:\Users\Anant\OneDrive\Desktop\Guardian\README.md
@@ -0,0 +1,81 @@
+# 🛡️ AI Guardian - Scam Detection Engine
+
+AI Guardian is a real-time scam and phishing detection engine designed to analyze messages and identify potential threats. It uses a hybrid approach, combining a machine learning model with a robust set of rule-based checks to provide a comprehensive risk score.
+
+This project was developed for a hackathon to showcase a practical application of AI in everyday security.
+
+## ✨ Features
+
+- **Hybrid Detection:** Utilizes both a `scikit-learn` ML model and a rich set of pattern-matching rules for high accuracy.
+- **Multi-faceted Analysis:** Scans for suspicious keywords, phrases indicating urgency, risky link patterns, and known malicious domains.
+- **Clear Risk Assessment:** Classifies messages into **Safe**, **Suspicious**, or **Dangerous** categories with a corresponding risk score.
+- **Interactive Web Demo:** A simple and intuitive web interface to test messages and see the analysis in real-time.
+- **REST API:** A simple `/analyse` endpoint for easy integration with other applications.
+- **CSV Logging:** Automatically logs every analysis to `guardian_log.csv` for auditing and data collection.
+- **User Feedback:** Includes a `/report` endpoint allowing users to flag messages that were incorrectly marked as safe, helping to improve the model over time.
+
+---
+
+## 🚀 Getting Started
+
+Follow these steps to get the AI Guardian demo running on your local machine.
+
+### Prerequisites
+
+- Python 3.8+
+- `pip` for package management
+
+### Installation & Setup
+
+1.  **Navigate to the project directory:**
+    ```bash
+    cd path/to/your/Guardian
+    ```
+
+2.  **Install the required dependencies:**
+    ```bash
+    pip install -r requirements.txt
+    ```
+
+3.  **Run the demo:**
+    ```bash
+    python start_demo.py
+    ```
+
+This will start the web server and automatically open the demo interface in your default web browser at `http://127.0.0.1:5000`.
+
+---
+
+## 📂 Project Structure
+
+The project is organized using a standard `src` layout for clarity and maintainability.
+
+```
+Guardian/
+├── .gitignore
+├── config.py               # Main configuration for the application
+├── LICENSE.md
+├── README.md               # You are here!
+├── requirements.txt        # Python dependencies
+├── start
