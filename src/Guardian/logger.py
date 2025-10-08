# src/Guardian/logger.py
import logging
import csv
import os
from datetime import datetime
import config

LOG_FILE = config.LOG_CONFIG['LOG_FILE']
LOG_HEADER = ['timestamp', 'message', 'level', 'score', 'reasons']
 
class CsvFormatter(logging.Formatter): # Renamed for clarity
    """Custom formatter to write specific log records to a CSV file."""
    def __init__(self, header):
        super().__init__()
        self.header = header
        self.log_file = LOG_FILE
        self._ensure_header()

    def _ensure_header(self):
        """Ensure the log file exists and has a header."""
        if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.header)
 
    def format(self, record):
        # Only format records that have the 'analysis_result' attribute
        if hasattr(record, 'analysis_result'):
            # The base formatter handles the string conversion
            return super().format(record)
        return "" # Return empty string for records we want to ignore
 
def setup_csv_logging(app):
    """Sets up a CSV logger and attaches it to the Flask app."""
    # This custom handler will write the formatted record to the CSV file
    class CsvFileHandler(logging.FileHandler):
        def emit(self, record):
            if hasattr(record, 'analysis_result') and record.analysis_result:
                with open(self.baseFilename, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=LOG_HEADER)
                    # Add timestamp to the record before writing
                    log_data = {'timestamp': datetime.utcnow().isoformat(), **record.analysis_result}
                    writer.writerow(log_data)
    
    csv_handler = CsvFileHandler(LOG_FILE, mode='a', encoding='utf-8')
    csv_handler.setFormatter(CsvFormatter(header=LOG_HEADER))
    csv_handler.setLevel(logging.INFO)
    # Add the handler to the Flask app's logger
    app.logger.addHandler(csv_handler)
    app.logger.setLevel(logging.INFO)