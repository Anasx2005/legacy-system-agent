import os

import psycopg

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


try:

    connection = psycopg.connect(DATABASE_URL)

    print("Database Connected Successfully.")

    connection.close()

except Exception as e:

    print("Connection Failed.")

    print(e)