import sqlite3
import time
from datetime import datetime

def setupLogger():
    connection = sqlite3.connect('log.db')
    cursor = connection.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Event (
    num INTEGER PRIMARY KEY AUTOINCREMENT,
    device TEXT NOT NULL,
    id TEXT NOT NULL,
    levent TEXT NOT NULL,  
    time REAL NOT NULL
    )
    ''')

    connection.commit()
    connection.close()

def newLog(msg, device, id):
    connection = sqlite3.connect('log.db')
    cursor = connection.cursor()

    tim = time.time()

    cursor.execute('INSERT INTO Event (levent, device, id, time) VALUES (?, ?, ?, ?)', (msg, device, id, tim))

    connection.commit()
    connection.close()

def get_events_filtered(id_filter=None, levent_filter=None, time_filter=None):
    connection = sqlite3.connect('log.db')
    cursor = connection.cursor()
    
    query = 'SELECT * FROM Event WHERE 1=1'
    params = []
    
    if id_filter:
        query += ' AND id LIKE ?'
        params.append(f'%{id_filter}%')
    
    if levent_filter:
        query += ' AND levent LIKE ?'
        params.append(f'%{levent_filter}%')
    
    if time_filter:
        now = time.time()
        if time_filter == 'hour':
            hour_ago = now - 3600
            query += ' AND time >= ?'
            params.append(hour_ago)
        elif time_filter == 'today':
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            query += ' AND time >= ?'
            params.append(today_start)
        elif time_filter == 'week':
            week_ago = now - (7 * 24 * 3600)
            query += ' AND time >= ?'
            params.append(week_ago)
        elif time_filter == 'month':
            month_ago = now - (30 * 24 * 3600)
            query += ' AND time >= ?'
            params.append(month_ago)
    
    query += ' ORDER BY time DESC'
    
    cursor.execute(query, params)
    events_data = cursor.fetchall()
    
    events = []
    for event in events_data:
        events.append({
            'num': event[0],
            'device': event[1],
            'id': event[2],
            'levent': event[3],
            'time': event[4],
            'human_time': time.ctime(event[4])
        })
    
    connection.close()
    return events

def get_events():
    return get_events_filtered()