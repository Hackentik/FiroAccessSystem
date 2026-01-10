import paho.mqtt.client as mqtt
import json
import time
import random
import sys
from datetime import datetime

class ESP32Simulator:
    def __init__(self, device_id="esp32_door_1", broker="localhost", port=1883):
        self.device_id = device_id
        self.broker = broker
        self.port = port
        
        self.client = mqtt.Client(client_id=device_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.door_open = False
        self.door_open_time = 0
        self.door_open_duration = 5000  # 5 секунд
        
        print(f"Виртуальный ESP32: {device_id}")
        print(f"Подключение к MQTT брокеру: {broker}:{port}")
    
    def connect(self):
        """Подключение к MQTT брокеру"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """Обработчик подключения"""
        if rc == 0:
            print("✓ Подключено к MQTT брокеру")
            
            # Подписываемся на команды
            client.subscribe("access/commands")
            client.subscribe("access/responses")
            
            # Отправляем статус онлайн
            self.send_status("online")
            
        else:
            print(f"✗ Ошибка подключения: {rc}")
    
    def on_message(self, client, userdata, msg):
        """Обработчик входящих сообщений"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"Получено [{topic}]: {payload[:100]}")
        
        try:
            data = json.loads(payload)
            
            if topic == "access/commands":
                self.handle_command(data)
            elif topic == "access/responses":
                self.handle_response(data)
                
        except json.JSONDecodeError:
            print("Невалидный JSON")
    
    def handle_command(self, data):
        """Обработка команд от сервера"""
        command = data.get('command', '')
        target_device = data.get('device_id', '')
        
        # Проверяем, предназначена ли команда этому устройству
        if target_device != self.device_id:
            return
        
        if command == "open_door":
            print("⚡ Команда: ОТКРЫТЬ ДВЕРЬ")
            self.open_door()
            self.send_event("door_manual_open", "Дверь открыта через интерфейс")
        
        elif command == "open_door_sh":
            print("⚡ Команда: ОТКРЫТЬ ДВЕРЬ ПО РАСПИСАНИЮ")
            self.open_door_sh()
            self.send_event("door_shed_open", "Дверь открыта по расписанию")

        elif command == "close_door_sh":
            print("⚡ Команда: ЗАКРЫТЬ ДВЕРЬ ПО РАСПИСАНИЮ")
            self.close_door_sh()
            self.send_event("door_shed_close", "Дверь закрыта по расписанию")

        elif command == "close_door":
            print("⚡ Команда: ЗАКРЫТЬ ДВЕРЬ")
            self.close_door()
            
        elif command == "reboot":
            print("⚡ Команда: ПЕРЕЗАГРУЗКА")
            self.send_event("reboot", "Устройство перезагружается")
            time.sleep(2)
            self.send_status("online")
            
        elif command == "beep":
            count = data.get('count', 1)
            print(f"⚡ Команда: СИГНАЛ ({count} раз)")
            self.send_event("beep", f"Сигнал {count} раз")
    
    def handle_response(self, data):
        """Обработка ответов от сервера"""
        success = data.get('success', False)
        message = data.get('message', '')
        
        if success:
            print(f"✓ Доступ разрешен: {message}")
            self.open_door()
        else:
            print(f"✗ Доступ запрещен: {message}")
            self.send_event("access_denied", message)
    
    def open_door(self):
        """Открыть дверь"""
        if not self.door_open:
            print("🚪 Дверь открыта")
            self.door_open = True
            self.door_open_time = time.time() * 1000
            self.send_event("door_opened", "Дверь открыта")
            
            # Автоматическое закрытие через 5 секунд
            print("(автоматическое закрытие через 5 секунд)")

    def open_door_sh(self):
        """Открыть дверь"""
        if not self.door_open:
            print("🚪 Дверь открыта пока не придет сигнал закрыть по расписанию")
            self.door_open = True
            self.send_event("door_opened_sh", "Дверь открыта")

    def close_door_sh(self):
        """Открыть дверь"""
        if not self.door_open:
            print("🚪 Дверь закрыта")
            self.door_open = False
            self.send_event("door_closed_sh", "Дверь закрыта")

    def close_door(self):
        """Закрыть дверь"""
        if self.door_open:
            print("🚪 Дверь закрыта")
            self.door_open = False
            self.send_event("door_closed", "Дверь закрыта")
    
    def simulate_card_read(self, card_number, facility_code=""):
        """Имитация считывания карты"""
        print(f"🎫 Карта считана: {card_number}")
        
        # Отправляем запрос на сервер
        request_data = {
            "request_id": f"req_{int(time.time() * 1000)}",
            "device_id": self.device_id,
            "card_number": str(card_number),
            "facility_code": str(facility_code),
            "timestamp": int(time.time() * 1000)
        }
        
        self.client.publish("access/requests", json.dumps(request_data))
        print(f"📤 Запрос доступа отправлен для карты {card_number}")
    
    def simulate_exit_button(self):
        """Имитация нажатия кнопки выхода"""
        print("🔘 Кнопка выхода нажата")
        self.open_door()
        self.send_event("exit_button", "Кнопка выхода нажата")
    
    def send_event(self, event_type, message=""):
        """Отправка события на сервер"""
        event_data = {
            "event_type": event_type,
            "device_id": self.device_id,
            "timestamp": int(time.time() * 1000),
            "message": message
        }
        
        self.client.publish("access/events", json.dumps(event_data))
    
    def send_status(self, status):
        """Отправка статуса устройства"""
        status_data = {
            "device_id": self.device_id,
            "status": status,
            "ip": "192.168.1.100",
            "timestamp": int(time.time() * 1000)
        }
        
        self.client.publish("access/status", json.dumps(status_data))
        print(f"📡 Статус отправлен: {status}")
    
    def run(self):
        """Запуск симулятора"""
        print("\n" + "="*50)
        print("ВИРТУАЛЬНЫЙ ESP32 - СИМУЛЯТОР СЧИТЫВАТЕЛЯ")
        print("="*50)
        print("\nКоманды:")
        print("  [номер] - ввести код карты")
        print("  exit    - нажать кнопку выхода")
        print("  status  - отправить статус")
        print("  reboot  - имитация перезагрузки")
        print("  quit    - выход")
        print("\nПример: 12345678 - отправит запрос для карты 12345678")
        print("="*50)
        
        try:
            while True:
                # Проверяем, нужно ли закрыть дверь по таймеру
                if self.door_open and (time.time() * 1000 - self.door_open_time > self.door_open_duration):
                    self.close_door()
                
                # Ждем ввод пользователя
                user_input = input("\nВведите команду или номер карты: ").strip()
                
                if user_input.lower() == 'quit':
                    print("Выход из симулятора...")
                    break
                    
                elif user_input.lower() == 'exit':
                    self.simulate_exit_button()
                    
                elif user_input.lower() == 'status':
                    self.send_status("online")
                    
                elif user_input.lower() == 'reboot':
                    print("⚡ Имитация перезагрузки устройства...")
                    self.send_status("offline")
                    time.sleep(1)
                    self.send_status("online")
                    print("✓ Устройство перезагружено")
                    
                elif user_input.isdigit():
                    # Ввод номера карты
                    card_number = user_input
                    facility_code = input("Введите Facility Code (или Enter для пропуска): ").strip()
                    if not facility_code:
                        facility_code = "0"
                    
                    self.simulate_card_read(card_number, facility_code)
                    
                else:
                    print("❌ Неизвестная команда")
                    
        except KeyboardInterrupt:
            print("\n\nПрограмма завершена")
        finally:
            self.client.disconnect()
            self.client.loop_stop()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Виртуальный ESP32 симулятор')
    parser.add_argument('--device', default='esp32_door_1', help='ID устройства')
    parser.add_argument('--broker', default='localhost', help='MQTT брокер')
    parser.add_argument('--port', type=int, default=1883, help='MQTT порт')
    
    args = parser.parse_args()
    
    # Создаем симулятор
    esp32 = ESP32Simulator(
        device_id=args.device,
        broker=args.broker,
        port=args.port
    )
    
    # Подключаемся к брокеру
    if esp32.connect():
        esp32.run()
    else:
        print("Не удалось подключиться к MQTT брокеру")
        print("Проверьте:")
        print("1. Запущен ли MQTT брокер? (mosquitto -v)")
        print("2. Правильный ли хост/порт?")
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
