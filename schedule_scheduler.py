import threading
import time
from datetime import datetime, timedelta
import sqlite3
from mqtt_client import get_mqtt_handler
import logging

from pathlib import Path

logger = logging.getLogger(__name__)
current_file = Path(__file__)
parent_dir = current_file.parent.parent
target_file = parent_dir / 'firo_access.db'
DB_NAME = target_file
class DoorScheduleScheduler:
    def __init__(self):
        self.mqtt = get_mqtt_handler()
        self.active_schedules = {}
        self.running = True
        self.check_interval = 60
        
    def check_and_apply_schedules(self):
        try:
            connection = sqlite3.connect(DB_NAME)
            cursor = connection.cursor()
            
            current_utc = datetime.utcnow()
            current_time = current_utc.strftime('%H:%M')
            current_weekday = current_utc.weekday()
            
            cursor.execute('SELECT DISTINCT door_id FROM DoorAccessSchedules WHERE is_active = 1')
            doors = cursor.fetchall()
            
            for (door_id,) in doors:
                cursor.execute('''
                SELECT id, schedule_name, start_time_utc, end_time_utc, weekdays
                FROM DoorAccessSchedules 
                WHERE door_id = ? 
                AND is_active = 1
                AND ? BETWEEN start_time_utc AND end_time_utc
                AND substr(weekdays, ?, 1) = '1'
                ''', (door_id, current_time, current_weekday + 1))
                
                active_schedule = cursor.fetchone()
                
                if active_schedule:
                    if door_id not in self.active_schedules:
                        logger.info(f"Расписание активировано для {door_id}")
                        self.activate_schedule_for_door(door_id, active_schedule)
                else:
                    if door_id in self.active_schedules:
                        logger.info(f"Расписание деактивировано для {door_id}")
                        self.deactivate_schedule_for_door(door_id)
            
            connection.close()
            
        except Exception as e:
            logger.error(f"Ошибка проверки расписаний: {str(e)}")
    
    def activate_schedule_for_door(self, door_id, schedule):
        try:
            if self.mqtt:
                self.mqtt.open_door_sh(door_id)
                logger.info(f"open_door_sh для {door_id}")
            
            end_time_str = schedule[3]
            current_date = datetime.utcnow().date()
            
            end_hour, end_minute = map(int, end_time_str.split(':'))
            end_datetime = datetime(current_date.year, current_date.month, current_date.day,
                                   end_hour, end_minute)
            
            if end_datetime < datetime.utcnow():
                end_datetime += timedelta(days=1)
            
            thread = threading.Timer(
                (end_datetime - datetime.utcnow()).total_seconds(),
                self.schedule_end_callback,
                args=[door_id]
            )
            thread.daemon = True
            thread.start()
            
            self.active_schedules[door_id] = {
                'thread': thread,
                'end_time': end_datetime,
                'schedule_name': schedule[1]
            }
            
        except Exception as e:
            logger.error(f"Ошибка активации расписания {door_id}: {str(e)}")
    
    def deactivate_schedule_for_door(self, door_id):
        try:
            if door_id in self.active_schedules:
                if self.mqtt:
                    self.mqtt.close_door_sh(door_id)
                    logger.info(f"close_door_sh для {door_id}")
                
                if self.active_schedules[door_id]['thread'].is_alive():
                    self.active_schedules[door_id]['thread'].cancel()
                
                del self.active_schedules[door_id]
                
        except Exception as e:
            logger.error(f"Ошибка деактивации расписания {door_id}: {str(e)}")
    
    def schedule_end_callback(self, door_id):
        logger.info(f"Время расписания истекло для {door_id}")
        self.deactivate_schedule_for_door(door_id)
    
    def start(self):
        def scheduler_loop():
            while self.running:
                try:
                    self.check_and_apply_schedules()
                except Exception as e:
                    logger.error(f"Ошибка цикла планировщика: {str(e)}")
                
                time.sleep(self.check_interval)
        
        scheduler_thread = threading.Thread(target=scheduler_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        logger.info("Планировщик запущен")
    
    def stop(self):
        self.running = False
        for door_id in list(self.active_schedules.keys()):
            self.deactivate_schedule_for_door(door_id)
        logger.info("Планировщик остановлен")

schedule_scheduler = None

def start_schedule_scheduler():
    global schedule_scheduler
    if schedule_scheduler is None:
        schedule_scheduler = DoorScheduleScheduler()
        schedule_scheduler.start()
    return schedule_scheduler

def stop_schedule_scheduler():
    global schedule_scheduler
    if schedule_scheduler:
        schedule_scheduler.stop()
        schedule_scheduler = None