import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import threading
import time
import sys
import os
import ologger

# Добавляем путь к проекту для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTHandler:
    def __init__(self, host='127.0.0.1', port=1883):
        self.host = host
        self.port = port
        self.client = None
        self.is_connected = False
        self.connected_devices = {}
        
        # Пытаемся импортировать функции БД
# В классе MQTTHandler в __init__:
        try:
            from users_db import get_user_by_card, get_user_by_pin, register_device, update_device_last_seen
            self.get_user_by_card = get_user_by_card
            self.get_user_by_pin = get_user_by_pin
            self.register_device = register_device
            self.update_device_last_seen = update_device_last_seen
            self.db_available = True
            logger.info("Функции БД успешно импортированы")
            ologger.newLog("Функции БД успешно импортированы", "FiroAccessServer", "FiroAccessServer")
        except ImportError as e:
            logger.error(f"Не удалось импортировать функции БД: {e}")
            ologger.newLog(f"Не удалось импортировать функции БД: {e}", "FiroAccessServer", "FiroAccessServer")
            self.db_available = False
    
    def connect(self):
        try:
            self.client = mqtt.Client(client_id="firoaccess_server")
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            
            logger.info(f"Подключение к MQTT {self.host}:{self.port}")
            ologger.newLog(f"Подключение к MQTT {self.host}:{self.port}", "FiroAccessServer", "FiroAccessServer")
            
            self.client.connect(self.host, self.port, 60)
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(target=self._mqtt_loop, daemon=True)
            thread.start()
            
            # Ждем подключения
            for i in range(5):
                if self.is_connected:
                    return True
                time.sleep(0.5)
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            ologger.newLog(f"Ошибка подключения к MQTT: {e}", "FiroAccessServer", "FiroAccessServer")
            return False
    
    def _mqtt_loop(self):
        try:
            self.client.loop_forever()
        except Exception as e:
            ologger.newLog(f"Ошибка в MQTT цикле: {e}", "FiroAccessServer", "FiroAccessServer")
            pass
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            logger.info("✓ Подключено к MQTT")
            ologger.newLog("✓ Подключено к MQTT", "FiroAccessServer", "FiroAccessServer")
            
            # Подписываемся на топики
            topics = [
                ("access/events", 0),
                ("access/requests", 0),
                ("access/status", 0),
                ("access/commands", 0),
                ("access/responses", 0)
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos=qos)
                logger.debug(f"Подписан на топик: {topic}")
            
        else:
            error_msg = f"Ошибка подключения MQTT: {rc}"
            logger.error(error_msg)
            ologger.newLog(error_msg, "FiroAccessServer", "FiroAccessServer")
    
    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"MQTT [{topic}]: {payload[:100]}")
            
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                error_msg = f"Невалидный JSON в топике {topic}: {payload[:100]}"
                logger.warning(error_msg)
                ologger.newLog(error_msg, "FiroAccessServer", "FiroAccessServer")
                return
            
            if topic == "access/events":
                self._handle_event(data)
            elif topic == "access/requests":
                self._handle_access_request(data)
            elif topic == "access/status":
                self._handle_status(data)
            elif topic == "access/responses":
                self._handle_client_response(data)
                
        except Exception as e:
            error_msg = f"Ошибка обработки сообщения MQTT: {e}"
            logger.error(error_msg)
            ologger.newLog(error_msg, "FiroAccessServer", "FiroAccessServer")
    
    def _handle_event(self, data):
        device_id = data.get('device_id')
        event_type = data.get('event_type')
        description = data.get('description', '')
        
        logger.info(f"Событие от {device_id}: {event_type}")
        ologger.newLog(f"Событие: {event_type} - {description}", device_id, device_id)
        
        if device_id not in self.connected_devices:
            self.connected_devices[device_id] = {}
        
        self.connected_devices[device_id].update({
            'last_event': event_type,
            'last_seen': datetime.now().isoformat(),
            'status': 'online'
        })
        
        # Обновляем время последнего контакта в базе данных
        if self.db_available:
            try:
                self.update_device_last_seen(device_id)
            except Exception as e:
                logger.error(f"Ошибка обновления времени устройства {device_id}: {e}")
    
    def _handle_access_request(self, data):
        """Обработка запросов доступа с проверкой в базе данных"""
        request_id = data.get('request_id')
        device_id = data.get('device_id')
        card_number = data.get('card_number')
        pin_code = data.get('pin_code')
        
        logger.info(f"Запрос доступа на {device_id}: карта={card_number}, PIN={pin_code}")
        
        response = {
            'request_id': request_id,
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if not self.db_available:
                logger.error("База данных недоступна")
                response['success'] = False
                response['message'] = "Ошибка сервера: база данных недоступна"
                ologger.newLog("База данных недоступна", device_id, device_id)
            else:
                # Регистрируем устройство, если оно ещё не зарегистрировано
                try:
                    self.register_device(device_id)
                except Exception as e:
                    logger.warning(f"Не удалось зарегистрировать устройство {device_id}: {e}")
                
                # Ищем пользователя
                user = None
                
                if card_number:
                    user = self.get_user_by_card(card_number)
                    logger.info(f"Поиск по карте {card_number}: {'найден' if user else 'не найден'}")
                elif pin_code:
                    user = self.get_user_by_pin(pin_code)
                    logger.info(f"Поиск по PIN {pin_code}: {'найден' if user else 'не найден'}")
                
                if user:
                    # Проверяем статус пользователя
                    user_status = user.get('status', '').lower()
                    user_name = user.get('name', 'Неизвестно')
                    
                    if user_status == 'active':
                        # Проверяем доступ к конкретной двери
                        from users_db import check_user_access
                        has_access, access_message = check_user_access(user, device_id, 'card' if card_number else 'pin')
                        
                        if has_access:
                            response['success'] = True
                            response['message'] = f"Доступ разрешен для {user_name}"
                            response['user'] = {
                                'id': user.get('id'),
                                'name': user_name
                            }
                            logger.info(f"✓ Доступ разрешен: {user_name}")
                        else:
                            response['success'] = False
                            response['message'] = access_message
                            logger.warning(f"✗ Доступ запрещен: {access_message}")
                    else:
                        response['success'] = False
                        response['message'] = f"Пользователь {user_name} не активен"
                        logger.warning(f"✗ Пользователь не активен: {user_name}")
                else:
                    response['success'] = False
                    response['message'] = "Пользователь не найден"
                    logger.warning(f"✗ Пользователь не найден: карта={card_number}")
                
        except Exception as e:
            logger.error(f"Ошибка проверки доступа: {e}")
            response['success'] = False
            response['message'] = f"Ошибка сервера: {str(e)}"
            ologger.newLog(f"Ошибка проверки доступа: {e}", device_id, device_id)
        
        # Отправляем ответ устройству
        self.publish('access/responses', response)


        # Логируем результат
        log_msg = f"Доступ {'РАЗРЕШЕН' if response['success'] else 'ЗАПРЕЩЕН'}: "
        log_msg += f"устройство={device_id}, "
        if card_number:
            log_msg += f"карта={card_number}, "
        if pin_code:
            log_msg += f"PIN={pin_code}, "
        log_msg += f"результат={response['message']}"
        from scenarios_db import check_card_scenario
        check_card_scenario(card_number, user_name)
        ologger.newLog(f"Доступ {'РАЗРЕШЕН' if response['success'] else 'ЗАПРЕЩЕН'}: устройство: {device_id}, карта={card_number}, PIN={pin_code}, результат={response['message']}", device_id, device_id)
        logger.info(log_msg)
    
    def _handle_status(self, data):
        device_id = data.get('device_id')
        status = data.get('status')
        ip_address = data.get('ip')
        
        if device_id:
            if device_id not in self.connected_devices:
                self.connected_devices[device_id] = {}
                # Регистрируем новое устройство в базе данных
                if self.db_available:
                    try:
                        self.register_device(device_id, ip_address=ip_address)
                        ologger.newLog(f"Новое устройство подключено: {device_id} ({ip_address})", "FiroAccessServer", "FiroAccessServer")
                    except Exception as e:
                        logger.error(f"Не удалось зарегистрировать устройство {device_id}: {e}")
            
            self.connected_devices[device_id].update({
                'status': status,
                'ip': ip_address,
                'last_seen': datetime.now().isoformat()
            })
            
            logger.info(f"Статус {device_id}: {status}")
            
            # Логируем изменение статуса устройства
            if status == 'online':
                ologger.newLog(f"Устройство {device_id} онлайн ({ip_address})", "FiroAccessServer", "FiroAccessServer")
            elif status == 'offline':
                ologger.newLog(f"Устройство {device_id} оффлайн", "FiroAccessServer", "FiroAccessServer")
    
    def _handle_client_response(self, data):
        """Обработка ответов от клиентов на команды"""
        device_id = data.get('device_id')
        command = data.get('command')
        result = data.get('result')
        message = data.get('message', '')
        
        logger.info(f"Ответ от {device_id} на команду {command}: {result}")
        ologger.newLog(f"Ответ на команду {command}: {result} - {message}", device_id, device_id)
    
    def publish(self, topic, data):
        if not self.is_connected:
            logger.warning(f"Не могу опубликовать: клиент не подключен")
            ologger.newLog(f"Не могу опубликовать в {topic}: клиент не подключен", "FiroAccessServer", "FiroAccessServer")
            return False
        
        try:
            payload = json.dumps(data, ensure_ascii=False)
            result = self.client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Опубликовано в {topic}")
                return True
            else:
                error_msg = f"Ошибка публикации в {topic}: код {result.rc}"
                logger.error(error_msg)
                ologger.newLog(error_msg, "FiroAccessServer", "FiroAccessServer")
                return False
                
        except Exception as e:
            error_msg = f"Ошибка публикации в {topic}: {e}"
            logger.error(error_msg)
            ologger.newLog(error_msg, "FiroAccessServer", "FiroAccessServer")
            return False
    
    def open_door(self, device_id):
        """Открыть дверь на устройстве"""
        data = {
            'command': 'open_door',
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Отправка команды открытия двери на {device_id}")
        ologger.newLog(f"Отправка команды открытия двери", device_id, device_id)
        return self.publish('access/commands', data)
    
    def close_door(self, device_id):
        """Закрыть дверь на устройстве"""
        data = {
            'command': 'close_door',
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Отправка команды закрытия двери на {device_id}")
        ologger.newLog(f"Отправка команды закрытия двери", device_id, device_id)
        return self.publish('access/commands', data)
    
    def open_door_sh(self, device_id):
        data = {
            'command': 'open_door_sh',
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Начало расписания для {device_id}")
        ologger.newLog(f"Начало расписания", device_id, device_id)
        return self.publish('access/commands', data)

    def close_door_sh(self, device_id):
        data = {
            'command': 'close_door_sh',
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Конец расписания для {device_id}")
        ologger.newLog(f"Конец расписания", device_id, device_id)
        return self.publish('access/commands', data)

    def reboot_device(self, device_id):
        """Перезагрузить устройство"""
        data = {
            'command': 'reboot',
            'device_id': device_id,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Отправка команды перезагрузки на {device_id}")
        ologger.newLog(f"Отправка команды перезагрузки", device_id, device_id)
        return self.publish('access/commands', data)
    
    def get_connected_devices(self):
        """Получить список подключенных устройств"""
        return self.connected_devices
    
    def disconnect(self):
        """Отключиться от MQTT брокера"""
        if self.client:
            self.client.disconnect()
            self.is_connected = False
            logger.info("Отключено от MQTT")
            ologger.newLog("Отключено от MQTT", "FiroAccessServer", "FiroAccessServer")


# Глобальный экземпляр
mqtt_handler = None

def init_mqtt(host='127.0.0.1', port=1883):
    global mqtt_handler
    
    if mqtt_handler is None:
        mqtt_handler = MQTTHandler(host, port)
        if mqtt_handler.connect():
            logger.info("MQTT обработчик запущен")
            ologger.newLog("MQTT обработчик запущен", "FiroAccessServer", "FiroAccessServer")
        else:
            logger.warning("Не удалось подключиться к MQTT")
            ologger.newLog("Не удалось подключиться к MQTT", "FiroAccessServer", "FiroAccessServer")
    
    return mqtt_handler

def get_mqtt_handler():
    return mqtt_handler