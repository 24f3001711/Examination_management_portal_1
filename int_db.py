from db import db
from app import app
from seed_data import create_admin, seed_data

def initialize_dbs():
    with app.app_context():
        db.create_all()
        create_admin()
        seed_data()
        print("DATABASE Init Successfully")

if __name__ == "__main__":
    initialize_dbs()


 