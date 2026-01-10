import sqlite3
import requests
import json
from datetime import datetime
import logging
from mqtt_client import get_mqtt_handler
import subprocess
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
DB_NAME = 'firo_access.db'

def setup_scenarios_db():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        trigger_type TEXT NOT NULL,
        trigger_value TEXT NOT NULL,
        action_type TEXT NOT NULL,
        action_value TEXT NOT NULL,
        enabled BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    connection.commit()
    connection.close()

def get_scenarios():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    cursor.execute('SELECT * FROM Scenarios ORDER BY name')
    rows = cursor.fetchall()
    
    scenarios = []
    for row in rows:
        scenarios.append({
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'trigger_type': row[3],
            'trigger_value': row[4],
            'action_type': row[5],
            'action_value': row[6],
            'enabled': bool(row[7]),
            'created_at': row[8]
        })
    
    connection.close()
    return scenarios

def add_scenario(name, description, trigger_type, trigger_value, action_type, action_value, enabled=True):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    cursor.execute('''
    INSERT INTO Scenarios (name, description, trigger_type, trigger_value, action_type, action_value, enabled)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, trigger_type, trigger_value, action_type, action_value, 1 if enabled else 0))
    
    connection.commit()
    connection.close()

def update_scenario(scenario_id, **kwargs):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    if not kwargs:
        connection.close()
        return
    
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(scenario_id)
    
    cursor.execute(f'UPDATE Scenarios SET {set_clause} WHERE id = ?', values)
    connection.commit()
    connection.close()

def delete_scenario(scenario_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    cursor.execute('DELETE FROM Scenarios WHERE id = ?', (scenario_id,))
    connection.commit()
    connection.close()

def check_card_scenario(card_number, user_name):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    cursor.execute('SELECT * FROM Scenarios WHERE enabled = 1 AND trigger_type = "card_scanned" AND trigger_value = ?', (card_number,))
    
    rows = cursor.fetchall()
    connection.close()
    
    for row in rows:
        scenario = {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'trigger_type': row[3],
            'trigger_value': row[4],
            'action_type': row[5],
            'action_value': row[6],
            'enabled': row[7],
            'created_at': row[8]
        }
        execute_scenario_action(scenario, {'card_number': card_number, 'user_name': user_name})
    
    return len(rows) > 0

def execute_scenario_action(scenario, context_data):
    try:
        logger.info(f"START SCENARIO {scenario['name']}")
        
        action_type = scenario['action_type']
        action_value = scenario['action_value']
        
        if action_type == 'webhook':
            logger.info(f"Sending webhook to {action_value}")
            
            payload = {
                'event_type': 'scenario_triggered',
                'timestamp': datetime.now().isoformat(),
                'data': context_data,
                'scenario_name': scenario['name']
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(action_value, json=payload, headers=headers, timeout=10)
            logger.info(f"Webhook status {response.status_code}")
            
        elif action_type == 'open_door':
            mqtt = get_mqtt_handler()
            if mqtt:
                mqtt.open_door(action_value)
                logger.info(f"Door opened {action_value}")
                
        elif action_type == 'send_notification':
            try:
                from web_Server import socketio
                message = action_value
                socketio.emit('scenario_notification', {
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"Notification sent {message}")
            except:
                logger.error("SocketIO error")
        
        logger.info(f"END SCENARIO {scenario['name']}")
        
    except Exception as e:
        logger.error(f"Scenario error {str(e)}")

def check_door_trigger(device_id, event_type):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    cursor.execute('SELECT * FROM Scenarios WHERE enabled = 1 AND trigger_type = ?', (event_type,))
    
    rows = cursor.fetchall()
    connection.close()
    
    for row in rows:
        trigger_value = row[4]
        
        if trigger_value == 'any' or trigger_value == device_id or trigger_value == '':
            scenario = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'trigger_type': row[3],
                'trigger_value': trigger_value,
                'action_type': row[5],
                'action_value': row[6],
                'enabled': row[7],
                'created_at': row[8]
            }
            
            execute_scenario_action(scenario, {
                'device_id': device_id, 
                'event_type': event_type,
                'timestamp': datetime.now().isoformat()
            })
    
    return len(rows) > 0