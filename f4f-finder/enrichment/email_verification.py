import random

def verify_email(email):
    if not email:
        return f'test{random.randint(1,1000)}@example.com'
    return email

