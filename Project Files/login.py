from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
import mysql.connector
import bcrypt # type: ignore

# Database connection
db_connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="ktom2005",
    database="health_management_2"
)

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setGeometry(300, 200, 400, 250)

        # Layout
        self.layout = QVBoxLayout()

        # Username field
        self.username_label = QLabel("Username")
        self.username_input = QLineEdit(self)
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)

        # Password field
        self.password_label = QLabel("Password")
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)

        # Login button
        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.)
        self.layout.addWidget(self.login_button)

        # Error label
        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet("color: red;")
        self.layout.addWidget(self.error_label)

        self.setLayout(self.layout)

    def (self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.show_error("Both fields are required!")
            return

        # Authenticate the user
        if self.authenticate_user(username, password):
            self.error_label.setStyleSheet("color: green;")
            self.show_error("Login successful!")
            self.accept()  # Close the  window
        else:
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setFocus()
            self.show_error("Invalid credentials. Please try again.")

    def authenticate_user(self, username, password):
        try:
            query = "SELECT password FROM users WHERE username = %s"
            with db_connection.cursor() as cursor:
                cursor.execute(query, (username,))
                result = cursor.fetchone()
                if result:
                    stored_hashed_password = result[0]
                    # Compare the hashed password
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                        return True
            return False
        except mysql.connector.Error as e:
            self.show_error(f"Database error: {e}")
            return False

    def show_error(self, message):
        self.error_label.setText(message)

    def closeEvent(self, event):
        # Close database connection only if it's open
        if db_connection.is_connected():
            db_connection.close()
        event.accept()
