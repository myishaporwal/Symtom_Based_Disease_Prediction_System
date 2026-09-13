import sys
import joblib
import mysql.connector
import speech_recognition as sr
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QWidget, QDialog , QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from gensim.models import Word2Vec
import os
from login import LoginWindow
from datetime import datetime
# Ensure nltk resources are downloaded
nltk.download('stopwords')
nltk.download('wordnet')

# Initialize NLP tools
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# Connect to the MySQL database
import mysql.connector
from db_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME  # Import credentials from the module

# Establish database connection
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    print("Database connected successfully.")
except mysql.connector.Error as err:
    print(f"Error connecting to the database: {err}")

# Load the ML model and vectorizer
model = joblib.load("disease_prediction_model.pkl")
vectorizer = joblib.load("vectorizer.pkl")


# Function to train a Word2Vec model and save it
def train_word2vec_model(corpus):
    # Train a Word2Vec model
    word2vec_model = Word2Vec(sentences=corpus, vector_size=100, window=5, min_count=1, workers=4)
    word2vec_model.save("word2vec_model.pkl")  # Save the model
    return word2vec_model

# Check if the Word2Vec model exists, if not, train and save it
def load_or_train_word2vec_model():
    if os.path.exists("word2vec_model.pkl"):
        word2vec_model = Word2Vec.load("word2vec_model.pkl")  # Load the existing model
    else:
        corpus = [
    ['pain', 'fever', 'headache'], 
    ['vomit', 'nausea', 'headache'], 
    ['stomach', 'ache', 'pain'], 
    ['cough', 'fever', 'sore_throat'], 
    ['fatigue', 'weight_loss', 'fever'], 
    ['joint_pain', 'swelling', 'stiffness'], 
    ['rash', 'itching', 'redness'], 
    ['chest_pain', 'shortness_of_breath', 'palpitations'], 
    ['diarrhea', 'abdominal_cramps', 'dehydration'], 
    ['burning_urination', 'frequent_urination', 'pain_in_urination'], 
    ['back_pain', 'stiff_neck', 'fatigue'], 
    ['dizziness', 'blurred_vision', 'nausea'], 
    ['sneezing', 'runny_nose', 'watery_eyes'], 
    ['cold', 'cough', 'congestion'], 
    ['weakness', 'loss_of_appetite', 'weight_loss'], 
    ['sensitivity_to_light', 'blurred_vision', 'headache'], 
    ['difficulty_breathing', 'wheezing', 'coughing'], 
    ['high_blood_pressure', 'dizziness', 'headache'], 
    ['sweating', 'palpitations', 'anxiety'], 
    ['numbness', 'tingling', 'muscle_weakness'], 
    ['yellow_skin', 'fatigue', 'abdominal_pain'], 
    ['bleeding_gums', 'fatigue', 'easy_bruising'], 
    ['high_fever', 'chills', 'body_ache'], 
    ['loss_of_smell', 'loss_of_taste', 'fever']
]
 # Example corpus
        word2vec_model = train_word2vec_model(corpus)  # Train the model and save it
    return word2vec_model

# Function to preprocess the input: Tokenization, Lemmatization, and Stopword Removal
def preprocess_input(symptoms_input):
    words = symptoms_input.lower().split()  # Convert to lowercase and split by spaces
    words = [lemmatizer.lemmatize(word) for word in words if word not in stop_words]
    return words

# Query expansion: Map the symptoms to a broader range of similar terms
def expand_symptoms(symptoms_input, model, threshold=0.5):
    synonym_map = {
        'bodypain': 'body pain',
        'sick': 'ill',
        'feeling': '',  # Skip feeling as it's too vague
    }

    processed_input = preprocess_input(symptoms_input)
    expanded_terms = []
    
    for word in processed_input:
        if word in synonym_map:
            word = synonym_map[word]
            if word == '':  # Skip if the word is empty (like 'feeling')
                continue
        
        try:
            similar_words = model.wv.most_similar(word, topn=5)
            for similar_word, similarity_score in similar_words:
                if similarity_score >= threshold:
                    expanded_terms.append(similar_word)
        except KeyError:
            print(f"Word '{word}' not found in vocabulary. Skipping.")
            continue
    
    return expanded_terms

def identify_disease(symptoms_input, user_id):
    if not symptoms_input.strip():
        return "Please enter at least one symptom."
    processed_symptoms = preprocess_input(symptoms_input)
    word2vec_model = load_or_train_word2vec_model()  # Load or train the Word2Vec model
    
    expanded_symptoms = expand_symptoms(symptoms_input, word2vec_model)

    query = "SELECT disease, symptoms, possible_medication, cure, severity FROM disease_info"
    cursor.execute(query)
    disease_data = cursor.fetchall()

    diseases = []
    possible_medication = []
    cures = []
    severities = []
    disease_vectors = []

    for disease, symptoms, medication, cure, severity in disease_data:
        disease_vector = vectorizer.transform([symptoms]).toarray()
        diseases.append(disease)
        possible_medication.append(medication)
        cures.append(cure)
        severities.append(severity)
        disease_vectors.append(disease_vector)

    similarities = []
    for disease_vector in disease_vectors:
        similarity = cosine_similarity(vectorizer.transform([symptoms_input]).toarray(), disease_vector)
        similarities.append(similarity[0][0])

    disease_scores = list(zip(diseases, similarities, possible_medication, cures, severities))
    disease_scores.sort(key=lambda x: x[1], reverse=True)

    top_5_diseases = disease_scores[:5]

    if not top_5_diseases:
        return "No matching diseases found."

    # Store the search history in the database
    user_id = 1  # Replace with actual user ID (from the logged-in user)
    current_date = datetime.now()
    formatted_date = current_date.strftime('%Y-%m-%d %H:%M:%S')
    for disease, similarity, medication, cure, severity in top_5_diseases:

        query = """INSERT INTO user_search_history (user_id, predicted_diseases, possible_medication, cure, severity, search_date)
           VALUES (%s, %s, %s, %s, %s, %s)"""
        

        # Fetch current date and time
        
        cursor.execute(query, (user_id, disease, medication, cure, severity, formatted_date))
    conn.commit()

    return [(disease, medication, cure, severity) for disease, _, medication, cure, severity in top_5_diseases]

# Class for Voice Input Thread
class VoiceInputThread(QThread):
    update_text = pyqtSignal(str)  # Signal to update the text in the symptom input field
    update_status = pyqtSignal(str)  # Signal to update the status label

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False

    def run(self):
        with self.microphone as source:
            while True:
                if self.is_listening:
                    self.update_status.emit("Listening... Please speak clearly.")
                    self.recognizer.adjust_for_ambient_noise(source, duration=3)

                    try:
                        audio = self.recognizer.listen(source, timeout=20, phrase_time_limit=15)
                        spoken_text = self.recognizer.recognize_google(audio)
                        self.update_text.emit(spoken_text)  # Emit signal to update the input field
                    except sr.UnknownValueError:
                        self.update_status.emit("Could not understand the audio.")
                    except sr.RequestError:
                        self.update_status.emit("Request failed, please try again.")

    def start_listening(self):
        self.is_listening = True
        self.start()

    def stop_listening(self):
        self.is_listening = False
        self.update_status.emit("Stopped listening.")
'''class HistoryDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Previous Prediction History")
        self.setGeometry(300, 300, 600, 400)
        layout = QVBoxLayout()

        # Create a QTableWidget to display the history
        self.history_table = QTableWidget(self)
        self.history_table.setRowCount(0)  # Initially empty
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(['Disease Name', 'Possible Medication', 'Cure', 'Severity'])
        self.history_table.setStyleSheet("QTableWidget {background-color: #f9f9f9;} QTableWidget::item { padding: 5px;}")

        # Color the column headers
        self.history_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.history_table)
        self.setLayout(layout)
    def load_history(self):
        # This method should load and display the history of diseases
        # Example: Load from database or file
        history_data = self.fetch_history_from_db()
        
        # Assuming you have a table widget or other UI elements to display history
        for data in history_data:
            # Add each entry to the UI element (like a table widget)
            self.history_table.insertRow(self.history_table.rowCount())
            self.history_table.setItem(self.history_table.rowCount() - 1, 0, QTableWidgetItem(data))

    def fetch_history_from_db(self):
        # This function could query your MySQL database for the user's disease search history
        # Replace with actual database querying logic
        return ["Disease 1", "Disease 2", "Disease 3"]  # Example data
# Disease Prediction App without Theme Selection'''
class HistoryDialog(QDialog):
    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle("Previous Prediction History")
        self.setGeometry(300, 300, 600, 400)
        self.user_id = user_id  # Store the user_id
        layout = QVBoxLayout()

        # Create a QTableWidget to display the history
        self.history_table = QTableWidget(self)
        self.history_table.setRowCount(0)  # Initially empty
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(['Disease Name', 'Possible Medication', 'Cure', 'Severity', 'Date'])
        self.history_table.setStyleSheet("QTableWidget {background-color: #f9f9f9;} QTableWidget::item { padding: 5px;}")

        # Color the column headers
        self.history_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.history_table)
        self.setLayout(layout)

    def load_history(self):
        # Fetch history data from the database
        history_data = self.fetch_history_from_db()

        # Add each entry to the UI element (like a table widget)
        for data in history_data:
            self.history_table.insertRow(self.history_table.rowCount())
            for col, value in enumerate(data):
                if isinstance(value, datetime):  # Check if the value is a datetime object
                    value = value.strftime('%Y-%m-%d %H:%M:%S')  # Convert it to string
                self.history_table.setItem(self.history_table.rowCount() - 1, col, QTableWidgetItem(value))

    def fetch_history_from_db(self):
        # Fetch user's disease search history from the database
        query = """SELECT predicted_diseases, possible_medication, cure, severity, search_date FROM user_search_history WHERE user_id = %s"""
        cursor.execute(query, (self.user_id,))  # Use the actual user_id here
        history_data = cursor.fetchall()

        return history_data


class DiseasePredictionApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Symptom-Based Disease Prediction System")
        self.setGeometry(200, 200, 800, 600)
        self.current_user_id = None
        # Layout setup
        self.layout = QVBoxLayout()

        # Title label
        self.title_label = QLabel("Symptom-Based Disease Prediction System", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF; background-color: #4CAF50; padding: 10px;")
        self.layout.addWidget(self.title_label)

        # Symptom input field
        self.symptom_label = QLabel("Enter symptoms separated by commas:")
        self.symptom_input = QLineEdit(self)
        self.symptom_input.setPlaceholderText("e.g., cough, fever")
        self.symptom_input.setStyleSheet("padding: 10px; border-radius: 5px; background-color: #f2f2f2;")

        # Voice input button (Microphone Icon)
        self.voice_button = QPushButton(self)
        self.voice_button.setIcon(QIcon.fromTheme("microphone"))
        self.voice_button.setIconSize(self.voice_button.sizeHint())
        self.voice_button.setStyleSheet("background-color: #008CBA; color: white; padding: 10px; border-radius: 5px;")
        self.voice_button.setFixedHeight(50)
        self.voice_button.setText("Voice Input for Mic")  # Changed text here
        self.voice_button.clicked.connect(self.toggle_voice_input)

        # Identifying disease button
        self.identify_button = QPushButton("Identify Disease", self)
        self.identify_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px;")
        self.identify_button.setFixedHeight(50)
        self.identify_button.clicked.connect(self.identify_disease)
        
        # Create a "Show History" button
        self.history_button = QPushButton("Show History", self)
        self.history_button.setStyleSheet("background-color: #FF9800; color: white; padding: 10px; border-radius: 5px;")
        self.history_button.setFixedHeight(50)
        self.history_button.clicked.connect(self.show_history)

        # Add widgets to a layout
        input_layout = QVBoxLayout()
        input_layout.addWidget(self.symptom_label)
        input_layout.addWidget(self.symptom_input)
        input_layout.addWidget(self.voice_button)
        input_layout.addWidget(self.identify_button)
        input_layout.addWidget(self.history_button)
        self.layout.addLayout(input_layout)

        # Result table
        self.result_table = QTableWidget(self)
        self.result_table.setRowCount(1)  # Placeholder row
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(['Disease Name', 'Possible Medication', 'Cure', 'Severity'])
        self.result_table.setStyleSheet("QTableWidget {background-color: #f9f9f9;} QTableWidget::item { padding: 5px;}")

        # Color the column headers
        self.result_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4CAF50;  /* Green background */
                color: white;  /* White text */
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        self.layout.addWidget(self.result_table)

        self.setLayout(self.layout)

        self.voice_thread = VoiceInputThread()
        self.voice_thread.update_text.connect(self.update_symptom_input)
        self.voice_thread.update_status.connect(self.update_status_label)

    def update_status_label(self, status):
        # Update the status label (you can add a status label to your layout for this)
        pass
    def get_user_id(self):
        if self.current_user_id is not None:
            return self.current_user_id
        else:
            print("User not logged in!")
            return None
 

    def update_symptom_input(self, text):
        self.symptom_input.setText(text)

    def toggle_voice_input(self):
        if self.voice_button.text() == "Voice Input for Mic":
            self.voice_button.setText("Stop Listening")
            self.voice_thread.start_listening()
        else:
            self.voice_button.setText("Voice Input for Mic")
            self.voice_thread.stop_listening()

    def identify_disease(self):
        symptoms_input = self.symptom_input.text()
        predictions = identify_disease(symptoms_input)

        if predictions == "Please enter at least one symptom." or predictions == "No matching diseases found.":
            self.result_table.setRowCount(1)
            self.result_table.setItem(0, 0, QTableWidgetItem(predictions))
        else:
            self.result_table.setRowCount(len(predictions))
            for i, (disease, medication, cure, severity) in enumerate(predictions):
                self.result_table.setItem(i, 0, QTableWidgetItem(disease))
                self.result_table.setItem(i, 1, QTableWidgetItem(medication))
                self.result_table.setItem(i, 2, QTableWidgetItem(cure))
                severity_item = QTableWidgetItem(severity)
                if severity.lower() == "low":
                    severity_item.setBackground(QColor(0, 255, 0))  # Green for low
                elif severity.lower() == "moderate":
                    severity_item.setBackground(QColor(255, 255, 0))  # Yellow for moderate
                elif severity.lower() == "high":
                    severity_item.setBackground(QColor(255, 0, 0))  # Red for high
                self.result_table.setItem(i, 3, severity_item)

        self.result_table.resizeColumnsToContents()
        symptoms_input = symptoms_input.strip()
        if not symptoms_input:
            return "Please enter at least one symptom."

        processed_symptoms = preprocess_input(symptoms_input)
        word2vec_model = load_or_train_word2vec_model()  # Load or train the Word2Vec model
        
        expanded_symptoms = expand_symptoms(symptoms_input, word2vec_model)

        query = "SELECT disease, symptoms, possible_medication, cure, severity FROM disease_info"
        cursor.execute(query)
        disease_data = cursor.fetchall()

        diseases = []
        possible_medication = []
        cures = []
        severities = []
        disease_vectors = []

        for disease, symptoms, medication, cure, severity in disease_data:
            disease_vector = vectorizer.transform([symptoms]).toarray()
            diseases.append(disease)
            possible_medication.append(medication)
            cures.append(cure)
            severities.append(severity)
            disease_vectors.append(disease_vector)

        similarities = []
        for disease_vector in disease_vectors:
            similarity = cosine_similarity(vectorizer.transform([symptoms_input]).toarray(), disease_vector)
            similarities.append(similarity[0][0])

        disease_scores = list(zip(diseases, similarities, possible_medication, cures, severities))
        disease_scores.sort(key=lambda x: x[1], reverse=True)

        top_5_diseases = disease_scores[:5]

        if not top_5_diseases:
            return "No matching diseases found."

    # Store the search history in the database
        user_id = 1  # Replace with actual user ID (from the logged-in user)
        for disease, _, medication, cure, severity in top_5_diseases:
            query = """INSERT INTO user_search_history (user_id, predicted_diseases, possible_medication, cure, severity)
                    VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(query, (user_id, disease, medication, cure, severity))
            conn.commit()

        return [(disease, medication, cure, severity) for disease, _, medication, cure, severity in top_5_diseases]

    def show_history(self):
        user_id = self.get_user_id()  # This will now return the correct user_id
        if user_id is not None:
            history_dialog = HistoryDialog(user_id)
            history_dialog.exec_()
        else:
            print("User not logged in!")

    def login(self, username, password):
        # After checking the credentials, set the current_user_id
        query = "SELECT user_id FROM users WHERE username = %s AND password = %s"
        cursor = self.db.cursor()
        cursor.execute(query, (username, password))
        result = cursor.fetchone()

        if result:
            self.current_user_id = result[0]  # Assuming result[0] is the user_id
        else:
            print("Invalid login credentials!")


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Show the login window first
    login_window = LoginWindow()

    # Only proceed if login was successful
    if login_window.exec_() == QDialog.Accepted:  # Check if login was successful
        window = DiseasePredictionApp()  # Create main window
        window.show()  # Show the main window
    else:
        print("Login failed. Exiting.")

    sys.exit(app.exec_())