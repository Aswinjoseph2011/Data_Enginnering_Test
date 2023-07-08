from fastapi import FastAPI
import pandas as pd
import os
import json
from sqlalchemy import create_engine

app = FastAPI()

class DataFrameToMySQL:
    def __init__(self, host, port, database, username):
        self.host = host
        self.port = port
        self.database = database
        self.username = username

    def convert_and_push_to_mysql(self):
        # Create MySQL connection
        engine = create_engine(f'mysql+pymysql://{self.username}@{self.host}:{self.port}/')

        # Create the database
        create_database_query = f"CREATE DATABASE IF NOT EXISTS {self.database}"
        engine.execute(create_database_query)
        engine = create_engine(f'mysql+pymysql://{self.username}@{self.host}:{self.port}/{self.database}')

        folder_path = os.getcwd()  # Get the current working directory

        json_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))

        data_list = []
        for file_path in json_files:
            with open(file_path, encoding='utf-8') as file:
                data = json.load(file)

            # Extract patient data
            patient_data = data['entry'][0]['resource']
            name = patient_data.get('name', [])
            if isinstance(name, list):
                given_names = [name_part.get('given', [''])[0] for name_part in name]
                family_name = name[0].get('family', [''])[0]
                full_name = ' '.join(given_names + [family_name])
            else:
                full_name = name.get('text', '')
            extracted_data = {
                'Name': full_name,
                'Gender': patient_data.get('gender', ''),
                'Birthdate': patient_data.get('birthDate', ''),
                'Race': patient_data.get('extension', [{}])[0].get('extension', [{}])[0].get('valueCoding', {}).get('display', ''),
                'Ethnicity': patient_data.get('extension', [{}])[1].get('extension', [{}])[0].get('valueCoding', {}).get('display', ''),
                'Address': patient_data.get('address', [{}])[0].get('line', [''])[0],
                'Contact': patient_data.get('telecom', [{}])[0].get('value', '')
            }
            data_list.append(extracted_data)

        # Create a DataFrame with patient data
        df = pd.DataFrame(data_list)

        # Push DataFrame to MySQL database table
        table_name = 'patient_data'
        df.to_sql(table_name, engine, if_exists='append', index=False)

        return f"DataFrame successfully pushed to the '{table_name}' table in the '{self.database}' database."

@app.post("/convert-and-push")
def convert_and_push_to_mysql(host: str, port: str, database: str, username: str):
    df_to_mysql = DataFrameToMySQL('host.docker.internal', port, database, username)
    result = df_to_mysql.convert_and_push_to_mysql()
    return {"message": result}
