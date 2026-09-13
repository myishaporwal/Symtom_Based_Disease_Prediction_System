Symptom-Based Disease Prediction System

This document outlines the module requirements, purpose, and instructions for setting up and running the Symptom-Based Disease Prediction System.

Overview

This project is a Python-based application that uses machine learning and natural language processing to predict diseases based on user-provided symptoms. It features voice input capabilities, a graphical user interface, and a database for storing user history.

Features

Symptom-based disease prediction using machine learning models.

Voice input for symptoms.

User-friendly GUI built with PyQt5.

Database connectivity for storing and retrieving prediction history.

etup Instructions

Ensure all required Python modules are installed (refer to the module requirements above).

Configure the database connection in db_config.py with valid credentials.

Place the pretrained models (disease_prediction_model.pkl, vectorizer.pkl, word2vec_model.pkl) in the project directory.

Place the following CSV files in the appropriate folder for database initialization:

user_search_history.csv

user.csv

disease_info.csv

Run the script using:

python script_name.py

Usage

Launch the application.

Log in using your credentials.

Enter symptoms manually or use the voice input feature.

View the predicted disease and possible treatments.