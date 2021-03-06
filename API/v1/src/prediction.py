# -*- coding: utf-8 -*-
import falcon
import json
import sys
import logging
import pandas as pd
import numpy as np
import pmdarima as pm
from statsmodels.tsa.arima_model import ARIMA
from falcon_cors import CORS
from bson import ObjectId
from datetime import datetime
from falcon import HTTP_400, HTTP_501, HTTP_404, HTTP_200

#Clase creada para procesar el campo 'data' que será devuelto
#como parte del 'body' en la respuesta al request realizado.
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        #Si es del tipo ObjectID, es necesario pasar la respuesta
        #a String para evitar errores.
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

#Clase para la definición del recurso 'Receipe', encargado de
#gestionar las peticiones al endpoint '/receipes'.
class Prediction(object):
    #Establecemos el manejador de la BD para respetar la
    #'Single source of truth'.
    def __init__(self, dbManager):
        #Inyección de dependencia
        self.dbManager = dbManager
        cors = CORS(allow_all_origins=True)
        self.model_temp = None
        self.model_humd = None
        
        
    #Método para procesar un petición Get.
    def get(self, method):
        #Estrutura de respuesta por defecto
        res = {
            "status": HTTP_400, #Bad request
            "data": method,
            "msg": "Default"
        }
        #Discriminamos el método indicado como parámetro
        #para realizar el get atendiendo al atributo deseado
        #del documento.
        print(method)
        n_periods = 0
        if(method == '24'):
            n_periods = 24
        elif(method == '48'):
            n_periods = 48
        elif(method == '72'):
            n_periods = 72
        elif(method == 'ok'):
            res['status'] = HTTP_200 
            res['data'] = 'OK!' 
            res['msg'] = 'OK'
            return res
        #Manejar error en cado de llamar a un método no definido
        else:
            res['status'] = HTTP_501 #Método no implementado
            res['msg'] = 'Error: method not implemented'
            return res
        if(self.model_humd != None and self.model_temp != None):
            res = self.getPrediction(n_periods)
        #Devolvemos la respuesta
        return res


    def get_models(self):
        #Obtener datos de temperatura y humedad de la BD
        res = self.dbManager.get()
        #Convertir datos a dataframe
        df = pd.DataFrame(data=res['data'])
        logging.warning(datetime.now())
        self.model_temp = pm.auto_arima(df.temperature.values, start_p=1, start_q=1, test='adf', max_p=3, max_q=3, m=1, d=None, seasonal=False, start_P=0, D=0,trace=True, error_action='ignore', suppress_warnings=True, stepwise=True)
        logging.warning(datetime.now())
        self.model_humd = pm.auto_arima(df.humidity.values, start_p=1, start_q=1, test='adf', max_p=3, max_q=3, m=1, d=None, seasonal=False, start_P=0, D=0,trace=True, error_action='ignore', suppress_warnings=True, stepwise=True)
        logging.warning(datetime.now())

    def getPrediction(self, nperiods):
        #Estrutura de respuesta por defecto
        res = {
            "status": HTTP_200, #Bad request
            "data": None,
            "msg": "Default"
        }
        #Predicciones 
        predictionsTemperature = self.predict(self.model_temp, nperiods)
        predictionsHumidity = self.predict(self.model_humd, nperiods)
        res['data'] = self.format_json(nperiods, predictionsTemperature, predictionsHumidity)
        return res

    def predict(self, model, n_periods_param):
        # Forecast
        fc, confint = model.predict(n_periods=n_periods_param, return_conf_int=True)
        return fc

    def format_json(self, n_periods, fc_temp, fc_humd):
        hours = ["00:00","01:00","02:00","03:00","04:00","05:00","06:00","07:00","08:00","09:00","10:00",
        "11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00","19:00","20:00","21:00","22:00",
        "23:00"]
        resp_data = []
        for i in range(n_periods):
            resp_data.append(dict(hour=hours[i%24],temperature=str(fc_temp[i]),humidity=str(fc_humd[i])))
        return resp_data

    def post(self, data):
        #Estrutura de respuesta por defecto
        res = {
            "status": HTTP_501, #Bad request
            "data": None,
            "msg": "Error: method POST not implemented"
        }
        #Devolvemos la respuesta
        return res

    #Método que será llamado cuando se ejecute una petición
    #get sobre el el recurso para el API.
    def on_get(self, req, resp):
        #Obtenemos los parámetros como queryParams en el URL
        methodParam = req.params['hours'] or ""
        #Procesamos la petición
        res = self.get(method=methodParam)
        #Establecemos la respuesta
        resp.status = res['status']
        resp.body = JSONEncoder().encode(res['data'])

    #Método que será llamado cuando se ejecute una petición
    #post sobre el el recurso para el API.
    def on_post(self, req, resp):
        #Obtenemos los parámetros como json en el body de la petición
        data = json.loads(req.stream.read(sys.maxsize).decode('utf-8'))
        #Procesamos la petición
        res = self.post(data=data)
        #Establecemos la respuesta
        resp.status = res['status']
        resp.body = JSONEncoder().encode(res['data'])

