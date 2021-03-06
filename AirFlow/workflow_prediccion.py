from datetime import timedelta
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
import pandas as pd
import datetime

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email': ['osc9718@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=4500),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}

#Inicialización del grafo DAG de tareas para el flujo de trabajo
dag = DAG(
    'practica2_forecast',
    default_args=default_args,
    description='Orquestación del servicio de prediccion',
    schedule_interval=timedelta(days=1),
)

def componerDatos():
    #Leemos fichero csv
    df_temp = pd.read_csv("/tmp/workflow/datos/temperature.csv", sep=",")
    df_hum = pd.read_csv("/tmp/workflow/datos/humidity.csv", sep=",")
    #Seleccionamos datos para San Francisco
    temp = df_temp[['datetime', 'San Francisco']]
    hum = df_hum[['datetime', 'San Francisco']]
    #Renombramos columnas
    temp.rename(columns={"San Francisco": "temperature"}, inplace=True)
    hum.rename(columns={"San Francisco": "humidity"}, inplace=True)
    #Join de los datos
    data = pd.merge(temp, hum, on='datetime')
    #Eliminamos valores nulos y exportamos a csv
    data = data.dropna()
    data.to_csv('/tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/data.csv', index=False, header=True, sep=',', decimal='.')
    print(data.head(5))

# Operadores o tareas
PrepararEntorno = BashOperator(
    task_id='PrepararEntorno',
    depends_on_past=False,
    bash_command='mkdir -p /tmp/workflow/datos/',
    dag=dag,
)

DescargaApi = BashOperator(
    task_id='DescargaApi',
    depends_on_past=True,
    bash_command='wget -O /tmp/workflow/master.zip https://github.com/yoskitar/API-Prediccion-Humedad-Temperatura-CC/archive/master.zip',
    dag=dag,
)

DescargaDatosHumedad = BashOperator(
    task_id='DescargaHumedad',
    depends_on_past=True,
    bash_command='wget -O /tmp/workflow/datos/humidity.csv.zip https://github.com/manuparra/MaterialCC2020/raw/master/humidity.csv.zip',
    dag=dag,
)

DescargaDatosTemperatura = BashOperator(
    task_id='DescargaTemperatura',
    depends_on_past=True,
    bash_command='wget -O /tmp/workflow/datos/temperature.csv.zip https://github.com/manuparra/MaterialCC2020/raw/master/temperature.csv.zip',
    dag=dag,
)

'''
Segunda opción de cara a mejorar la eficiencia, paralelizando el 
proceso de descompresión de cada .zip descargado

DescargaDatosYDescomprime = BashOperator(
    task_id='DescargaTemperatura',
    depends_on_past=True,
    bash_command='wget -O /tmp/workflow/datos/temperature.csv.zip https://github.com/manuparra/MaterialCC2020/raw/master/temperature.csv.zip && unzip -o /tmp/workflow/datos/temperature.csv.zip -d /tmp/workflow/datos',
    dag=dag,
)
'''

Descomprimir = BashOperator(
    task_id='Descomprimir',
    depends_on_past=True,
    bash_command='unzip -o /tmp/workflow/master.zip -d /tmp/workflow & unzip -o /tmp/workflow/datos/temperature.csv.zip -d /tmp/workflow/datos & unzip -o /tmp/workflow/datos/humidity.csv.zip -d /tmp/workflow/datos',
    dag=dag,
)

ComponerDatos = PythonOperator(
    task_id='ComponerDatos',
    depends_on_past=True,
    python_callable=componerDatos,
    dag=dag,
)

"""
ConstruirDBContainer = BashOperator(
    task_id='ConstruirDBContainer',
    depends_on_past=True,
    bash_command='cd /tmp/API-Prediccion-Humedad-Temperatura-CC-master/API/ && docker build -f ./mongodb.dockerfile -t mongodb_container_prediction .',
    dag=dag,
)

LanzarDBContainer = BashOperator(
    task_id='LanzarDBContainer',
    depends_on_past=True,
    bash_command='docker run --rm -d -p 27017:27017 --name db_mongo_container mongodb_container_prediction:latest',
    dag=dag,
)

IntegrarDatosDB = BashOperator(
    task_id='IntegrarDatosDB',
    depends_on_past=True,
    bash_command='docker exec db_mongo_container mongoimport --db PredictionsDB --collection predictions --headerline --file /usr/datos/data.csv --type csv',
    dag=dag,
)
"""

LanzarDBContainer = BashOperator(
    task_id='LanzarDBContainer',
    depends_on_past=True,
    bash_command='cd /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/ && docker-compose up --build -d',
    dag=dag,
)


TestServiceV1 = BashOperator(
    task_id='TestServiceV1',
    depends_on_past=True,
    bash_command='pip install -r /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/requirements.txt && cd /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/v1/ && coverage run -m unittest src/test/app_test.py',
    dag=dag,
)

TestServiceV2 = BashOperator(
    task_id='TestServiceV2',
    depends_on_past=True,
    bash_command='pip install -r /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/requirements_v2.txt && cd /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/v2/ && export API_KEY_WEATHER_FORECAST=<api_key> && coverage run -m unittest src/test/app_test.py',
    dag=dag,
)

'''
TestServices = BashOperator(
    task_id='TestServices',
    depends_on_past=True,
    bash_command='cd /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/ && docker-compose -f docker-compose_test.yml up --build -d',
    dag=dag,
)
'''

LanzarServices = BashOperator(
    task_id='LanzarServices',
    depends_on_past=True,
    bash_command='cd /tmp/workflow/API-Prediccion-Humedad-Temperatura-CC-master/API/ && export API_KEY_WEATHER_FORECAST=<api_key> && docker-compose -f docker-compose_services.yml up --build -d',
    dag=dag,
)

#Dependencias - Construcción del grafo DAG
PrepararEntorno >> [DescargaApi,DescargaDatosTemperatura,DescargaDatosHumedad] >> Descomprimir >> ComponerDatos >> LanzarDBContainer >> [TestServiceV1,TestServiceV2] >> LanzarServices