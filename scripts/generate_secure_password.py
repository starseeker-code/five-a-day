#!/usr/bin/env python3
"""
Generador de contraseñas seguras
Uso: python scripts/generate_secure_password.py [length]
"""
import secrets
import string
import sys

def generate_password(length=32):
    """Genera una contraseña segura con mayúsculas, minúsculas, números y símbolos"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    while True:
        password = ''.join(secrets.choice(chars) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*-_=+" for c in password)):
            return password

if __name__ == "__main__":
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    print(generate_password(length))
