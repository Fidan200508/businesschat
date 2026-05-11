from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted_value: str) -> str:
    return fernet.decrypt(encrypted_value.encode()).decode()