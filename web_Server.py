from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
import ologger
from login_db import Database
from mqtt_client import init_mqtt, get_mqtt_handler
import json
from datetime import datetime
import time
from datetime import datetime
import pytz
import sqlite3
from pathlib import Path

current_file = Path(__file__)
parent_dir = current_file.parent.parent
target_file = parent_dir / 'firo_access.db'
DB_NAME = target_file

from users_db import (
    setupUserDB, get_users, get_groups, add_user, delete_user, 
    update_user, get_user_by_id, get_user_by_card, get_user_by_pin,
    add_group, delete_group, update_group, get_group_by_id, 
    add_user_to_group, remove_user_from_group, check_user_access
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

socketio = SocketIO(app, cors_allowed_origins="*")

db = Database()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'info'

try:
    mqtt = init_mqtt()
    print("MQTT обработчик инициализирован")
except Exception as e:
    print(f"Ошибка инициализации MQTT: {e}")
    mqtt = None

emergency_states = {
    'evacuation': False,
    'lockdown': False,
    'normal': True
}

@login_manager.user_loader
def load_user(user_id):
    return db.get_user_by_id(user_id)

@socketio.on('connect')
def handle_connect():
    print(f"Клиент подключен: {request.sid}")
    emit('connected', {'message': 'Подключено к серверу', 'timestamp': datetime.now().isoformat()})
    
    if mqtt:
        devices = mqtt.get_connected_devices()
        emit('devices_update', {
            'devices': devices,
            'timestamp': datetime.now().isoformat()
        })
    
    emit('emergency_status', {
        'status': emergency_states,
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Клиент отключен: {request.sid}")

@socketio.on('open_door_request')
def handle_open_door_request(data):
    device_id = data.get('device_id')
    if device_id and mqtt:
        if emergency_states['lockdown']:
            emit('error', {
                'message': 'Отказ: режим ЛОКДАУН активирован',
                'timestamp': datetime.now().isoformat()
            })
            return
        
        mqtt.open_door(device_id)
        emit('door_command_sent', {
            'device_id': device_id,
            'command': 'open_door',
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)

def log_event(msg, device="WebInterface"):
    ologger.newLog(msg, device, "FiroAccess")

@app.route('/door_schedules')
@login_required
def door_schedules():
    return render_template('door_schedules.html')

@app.route('/api/door/schedule', methods=['POST'])
@login_required
def api_add_door_schedule():
    try:
        data = request.get_json()
        
        door_id = data.get('door_id')
        schedule_name = data.get('schedule_name')
        start_utc = data.get('start_time_utc')
        end_utc = data.get('end_time_utc')
        
        if not all([door_id, schedule_name, start_utc, end_utc]):
            return jsonify({
                'success': False,
                'message': 'Все поля обязательны для заполнения'
            }), 400
        
        import re
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        
        if not re.match(time_pattern, start_utc) or not re.match(time_pattern, end_utc):
            return jsonify({
                'success': False,
                'message': 'Время должно быть в формате HH:MM (24-часовой формат)'
            }), 400
        
        from users_db import add_door_schedule
        
        add_door_schedule(door_id, schedule_name, start_utc, end_utc)
        
        return jsonify({
            'success': True,
            'message': f'Расписание "{schedule_name}" добавлено'
        })
        
    except Exception as e:
        app.logger.error(f'Error adding door schedule: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/schedule/<sh_id>', methods=['DELETE'])
@login_required
def delete_door_schedule(sh_id):
    try:
        from users_db import delete_door_schedule
        
        delete_door_schedule(sh_id)
        return jsonify({
            'success': True,
            'message': f'Расписание удалено'
        })
        
    except Exception as e:
        app.logger.error(f'Error deleting door schedule: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/<door_id>/schedules')
@login_required
def api_get_door_schedules(door_id):
    try:
        connection = sqlite3.connect(DB_NAME)
        cursor = connection.cursor()
        
        cursor.execute('''
        SELECT * FROM DoorAccessSchedules 
        WHERE door_id = ? 
        ORDER BY start_time_utc
        ''', (door_id,))
        
        schedules = []
        for row in cursor.fetchall():
            schedules.append({
                'id': row[0],
                'door_id': row[1],
                'name': row[2],
                'is_active': bool(row[3]),
                'start': row[4],
                'end': row[5],
                'weekdays': row[6],
                'type': row[7],
                'created': row[8]
            })
        
        connection.close()
        return jsonify({'success': True, 'schedules': schedules})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/convert_to_utc', methods=['POST'])
@login_required
def api_convert_to_utc():
    try:
        data = request.get_json()
        time_str = data.get('time')
        timezone_str = data.get('timezone')
        
        if not time_str or not timezone_str:
            return jsonify({'success': False, 'message': 'Не указано время или часовой пояс'}), 400
        
        today = datetime.now().date()
        time_parts = list(map(int, time_str.split(':')))
        
        if len(time_parts) < 2:
            return jsonify({'success': False, 'message': 'Неверный формат времени'}), 400
        
        user_tz = pytz.timezone(timezone_str)
        user_dt = user_tz.localize(
            datetime(today.year, today.month, today.day, time_parts[0], time_parts[1], 0)
        )
        
        utc_dt = user_dt.astimezone(pytz.UTC)
        
        return jsonify({
            'success': True,
            'user_time': time_str,
            'user_timezone': timezone_str,
            'utc_time': utc_dt.strftime('%H:%M'),
            'utc_full': utc_dt.isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('inPC.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.get_user_by_username(username)
        
        if user and user.check_password(password):
            login_user(user)
            log_event(f"{username} успешно вошел в систему.")
            flash('Вы успешно вошли в систему!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            log_event(f"Неудачная попытка входа в аккаунт {username}")
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    devices = mqtt.get_connected_devices() if mqtt else {}
    return render_template('inPC.html', devices=devices, emergency_states=emergency_states)

@app.route('/events')
@login_required
def events():
    id_filter = request.args.get('id_filter')
    levent_filter = request.args.get('levent_filter')
    time_filter = request.args.get('time_filter')
    
    events = ologger.get_events_filtered(
        id_filter=id_filter,
        levent_filter=levent_filter,
        time_filter=time_filter
    )

    return render_template('events.html', events=events)

@app.route('/people_groups')
@login_required
def people_groups():
    users = get_users()
    groups = get_groups()
    return render_template('poeples.html', users=users, groups=groups)

@app.route('/update_user/<string:user_id>', methods=['POST'])
@login_required
def update_user_route(user_id):
    try:
        print(f"Обновление пользователя: {user_id}")
        
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Content-Type должен быть application/json'}), 400
            
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        update_data = {}
        fields = ['name', 'groups', 'role', 'status', 'pin', 'cardcode', 'liplate', 'creds']
        
        for field in fields:
            if field in data and data[field] is not None:
                if field == 'pin':
                    try:
                        update_data[field] = int(data[field]) if data[field] != '' else 0
                    except:
                        update_data[field] = 0
                else:
                    update_data[field] = data[field]
        
        if update_data:
            update_user(user_id, **update_data)
            log_event(f"Обновлен пользователь: {user_id}")
            
            return jsonify({'success': True, 'message': 'Пользователь обновлен'})
        else:
            return jsonify({'success': False, 'message': 'Нет данных для обновления'}), 400
            
    except Exception as e:
        print(f"Ошибка в update_user_route: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/door_management')
@login_required
def door_management():
    return render_template('door_management.html')

@app.route('/api/doors', methods=['GET'])
@login_required
def api_get_doors():
    try:
        from users_db import get_all_doors
        doors = get_all_doors()
        return jsonify({
            'success': True,
            'doors': doors,
            'count': len(doors)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door', methods=['POST'])
@login_required
def api_add_door():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        device_id = data.get('device_id')
        name = data.get('name')
        
        if not device_id or not name:
            return jsonify({'success': False, 'message': 'device_id и name обязательны'}), 400
        
        from users_db import add_door
        add_door(
            device_id=device_id,
            name=name,
            location=data.get('location', ''),
            description=data.get('description', ''),
            status=data.get('status', 'active')
        )
        
        log_event(f"Добавлена новая дверь: {name} ({device_id})", "DoorManagement")
        
        return jsonify({
            'success': True,
            'message': f'Дверь {name} добавлена'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/<string:device_id>', methods=['GET'])
@login_required
def api_get_door(device_id):
    try:
        from users_db import get_door_by_device_id
        door = get_door_by_device_id(device_id)
        
        if door:
            return jsonify({
                'success': True,
                'door': door
            })
        return jsonify({
            'success': False,
            'message': 'Дверь не найдена'
        }), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/<string:device_id>', methods=['PUT'])
@login_required
def api_update_door(device_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        from users_db import update_door
        update_data = {}
        
        fields = ['name', 'location', 'description', 'status']
        for field in fields:
            if field in data:
                update_data[field] = data[field]
        
        if update_data:
            update_door(device_id, **update_data)
            log_event(f"Обновлена дверь: {device_id}", "DoorManagement")
            
            return jsonify({
                'success': True,
                'message': 'Дверь обновлена'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Нет данных для обновления'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/scenarios')
@login_required
def scenarios():

    
    return "На данный момент не сделано"






@app.route('/api/door/permissions', methods=['GET'])
@login_required
def api_get_door_permissions():
    try:
        from users_db import get_door_permissions
        permissions = get_door_permissions()
        
        return jsonify({
            'success': True,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/permission', methods=['POST'])
@login_required
def api_add_door_permission():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        group_id = data.get('group_id')
        device_id = data.get('device_id')
        
        if not group_id or not device_id:
            return jsonify({'success': False, 'message': 'group_id и device_id обязательны'}), 400
        
        from users_db import set_door_permission
        set_door_permission(
            group_id=group_id,
            device_id=device_id,
            permission_type=data.get('permission_type', 'allow'),
            schedule=data.get('schedule', '{}')
        )
        
        log_event(f"Добавлено разрешение для группы {group_id} на дверь {device_id}", "DoorManagement")
        
        return jsonify({
            'success': True,
            'message': 'Разрешение добавлено'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/permission/<int:permission_id>', methods=['DELETE'])
@login_required
def api_delete_door_permission(permission_id):
    try:
        from users_db import delete_door_permission
        delete_door_permission(permission_id)
        
        log_event(f"Удалено разрешение {permission_id}", "DoorManagement")
        
        return jsonify({
            'success': True,
            'message': 'Разрешение удалено'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/test/door/access', methods=['POST'])
@login_required
def api_test_door_access():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        user_id = data.get('user_id')
        device_id = data.get('device_id')
        access_type = data.get('access_type', 'card')
        
        if not user_id or not device_id:
            return jsonify({'success': False, 'message': 'user_id и device_id обязательны'}), 400
        
        from users_db import get_user_by_id, check_user_access
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Пользователь не найден'
            })
        
        has_access, message = check_user_access(user, device_id, access_type)
        
        response = {
            'success': has_access,
            'message': message
        }
        
        if has_access:
            response['user'] = {
                'id': user.get('id'),
                'name': user.get('name')
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/list', methods=['GET'])
@login_required
def api_get_users_list():
    try:
        from users_db import get_users
        users = get_users()
        
        return jsonify({
            'success': True,
            'users': users
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/groups', methods=['GET'])
@login_required
def api_get_groups():
    try:
        from users_db import get_groups
        groups = get_groups()
        
        return jsonify({
            'success': True,
            'groups': groups
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/add_user', methods=['POST'])
@login_required
def add_user_route():
    try:
        name = request.form.get('name')
        user_id = request.form.get('id')
        groups = request.form.get('groups', '')
        creds = request.form.get('creds', '')
        pin = request.form.get('pin', 0)
        cardcode = request.form.get('cardcode', '')
        liplate = request.form.get('liplate', '')
        role = request.form.get('role', 'user')
        status = request.form.get('status', 'active')
        
        if not name or not user_id:
            flash('Имя и ID пользователя обязательны', 'error')
            return redirect(url_for('people_groups'))
        
        add_user(name, user_id, groups, creds, int(pin) if pin else 0, 
                cardcode, liplate, role, status)
        
        log_event(f"Добавлен новый пользователь: {name} ({user_id})")
        
        flash(f'Пользователь {name} успешно добавлен', 'success')
        
    except Exception as e:
        flash(f'Ошибка при добавлении пользователя: {str(e)}', 'error')
    
    return redirect(url_for('people_groups'))

@app.route('/delete_user/<string:user_id>')
@login_required
def delete_user_route(user_id):
    try:
        delete_user(user_id)
        log_event(f"Удален пользователь с ID: {user_id}")
        
        flash(f'Пользователь успешно удален', 'success')
    except Exception as e:
        flash(f'Ошибка при удаления пользователя: {str(e)}', 'error')
    
    return redirect(url_for('people_groups'))

@app.route('/control_panel')
@login_required
def control_panel():
    devices = mqtt.get_connected_devices() if mqtt else {}
    return render_template('control_panel.html', 
                          devices=devices, 
                          emergency_states=emergency_states)

@app.route('/add_group', methods=['POST'])
@login_required
def add_group_route():
    try:
        name = request.form.get('name')
        group_id = request.form.get('id')
        status = request.form.get('status', 'active')
        peo = request.form.get('peo', '')
        
        if not name or not group_id:
            flash('Название и ID группы обязательны', 'error')
            return redirect(url_for('people_groups'))
        
        add_group(name, group_id, status, peo)
        
        log_event(f"Добавлена новая группа: {name} ({group_id})")
        flash(f'Группа {name} успешно добавлена', 'success')
        
    except Exception as e:
        flash(f'Ошибка при добавлении группы: {str(e)}', 'error')
    
    return redirect(url_for('people_groups'))

@app.route('/delete_group/<string:group_id>')
@login_required
def delete_group_route(group_id):
    try:
        delete_group(group_id)
        log_event(f"Удалена группа с ID: {group_id}")
        flash(f'Группа успешно удалена', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении группы: {str(e)}', 'error')
    
    return redirect(url_for('people_groups'))

@app.route('/api/user/<string:user_id>')
@login_required
def api_get_user(user_id):
    try:
        user = get_user_by_id(user_id)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            })
        return jsonify({
            'success': False,
            'message': 'Пользователь не найден'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/open_door', methods=['POST'])
@login_required
def api_open_door():
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if emergency_states['lockdown']:
            return jsonify({'success': False, 'message': 'Отказ: режим ЛОКДАУН активирован'}), 403
        
        if mqtt:
            mqtt.open_door(device_id)
            

            
            log_event(f"Дверь открыта через интерфейс на устройстве {device_id}")
            
            return jsonify({'success': True, 'message': f'Команда отправлена на устройство {device_id}'})
        else:
            return jsonify({'success': False, 'message': 'MQTT не инициализирован'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/close_door', methods=['POST'])
@login_required
def api_close_door():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        device_id = data.get('device_id')
        if not device_id:
            return jsonify({'success': False, 'message': 'Не указан ID устройства'}), 400
        
        if emergency_states['evacuation']:
            return jsonify({
                'success': False,
                'message': 'Отказ: режим ЭВАКУАЦИИ активирован'
            }), 403
        
        if mqtt:

            mqtt.close_door(device_id)
            
            log_event(f"Дверь закрыта через интерфейс на устройстве {device_id}")
            
            return jsonify({
                'success': True, 
                'message': f'Команда закрытия отправлена на устройство {device_id}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'MQTT не инициализирован'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency/evacuation', methods=['POST'])
@login_required
def api_evacuation():
    try:
        data = request.get_json()
        if not data or not data.get('confirm'):
            return jsonify({
                'success': False,
                'message': 'Требуется подтверждение'
            }), 400
        
        password = data.get('password')
        if password and not current_user.check_password(password):
            return jsonify({
                'success': False,
                'message': 'Неверный пароль'
            }), 403
        
        emergency_states['evacuation'] = True
        emergency_states['lockdown'] = False
        emergency_states['normal'] = False
        
        if mqtt:
            devices = mqtt.get_connected_devices()
            for device_id in devices.keys():
                mqtt.open_door(device_id)
                log_event(f"Эвакуация: дверь {device_id} открыта", "Emergency-System")
        
        log_event(f"АКТИВИРОВАН РЕЖИМ ЭВАКУАЦИИ - инициатор: {current_user.username}", "Emergency-System")
        
        socketio.emit('emergency_evacuation', {
            'message': 'АКТИВИРОВАН РЕЖИМ ЭВАКУАЦИИ',
            'timestamp': datetime.now().isoformat(),
            'initiated_by': current_user.username
        }, broadcast=True)
        
        socketio.emit('emergency_status', {
            'status': emergency_states,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message': 'Режим эвакуации активирован - все двери открыты'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency/lockdown', methods=['POST'])
@login_required
def api_lockdown():
    try:
        data = request.get_json()
        if not data or not data.get('confirm'):
            return jsonify({
                'success': False,
                'message': 'Требуется подтверждение'
            }), 400
        
        password = data.get('password')
        if password and not current_user.check_password(password):
            return jsonify({
                'success': False,
                'message': 'Неверный пароль'
            }), 403
        
        emergency_states['lockdown'] = True
        emergency_states['evacuation'] = False
        emergency_states['normal'] = False
        
        if mqtt:
            devices = mqtt.get_connected_devices()
            for device_id in devices.keys():
                mqtt.close_door(device_id)
                log_event(f"Локдаун: дверь {device_id} закрыта", "Emergency-System")
        
        log_event(f"АКТИВИРОВАН РЕЖИМ ЛОКДАУНА - инициатор: {current_user.username}", "Emergency-System")
        
        socketio.emit('emergency_lockdown', {
            'message': 'АКТИВИРОВАН РЕЖИМ ЛОКДАУНА',
            'timestamp': datetime.now().isoformat(),
            'initiated_by': current_user.username
        }, broadcast=True)
        
        socketio.emit('emergency_status', {
            'status': emergency_states,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message': 'Режим локдауна активирован - все двери закрыты'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency/normal', methods=['POST'])
@login_required
def api_normal_mode():
    try:
        emergency_states['normal'] = True
        emergency_states['evacuation'] = False
        emergency_states['lockdown'] = False
        
        log_event(f"Восстановлен нормальный режим - инициатор: {current_user.username}", "Emergency-System")
        
        socketio.emit('emergency_normal', {
            'message': 'Восстановлен нормальный режим работы',
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        socketio.emit('emergency_status', {
            'status': emergency_states,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({
            'success': True,
            'message': 'Нормальный режим восстановлен'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency/status', methods=['GET'])
@login_required
def api_emergency_status():
    return jsonify({
        'success': True,
        'status': emergency_states,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/devices')
@login_required
def api_get_devices():
    try:
        devices = mqtt.get_connected_devices() if mqtt else {}
        return jsonify({
            'success': True,
            'devices': devices,
            'count': len(devices),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/<door_id>/open_sh', methods=['POST'])
@login_required
def api_open_door_schedule_mode(door_id):
    try:
        if mqtt:
            mqtt.open_door_sh(door_id)
            log_event(f"Дверь {door_id} открыта в режиме расписания через веб", door_id)
            
            return jsonify({
                'success': True,
                'message': f'Дверь {door_id} открыта в режиме расписания'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'MQTT не инициализирован'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/door/<door_id>/close_sh', methods=['POST'])
@login_required
def api_close_door_schedule_mode(door_id):
    try:
        if mqtt:
            mqtt.close_door_sh(door_id)
            log_event(f"Дверь {door_id} закрыта в режиме расписания через веб", door_id)
            
            return jsonify({
                'success': True,
                'message': f'Дверь {door_id} закрыта в режиме расписания'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'MQTT не инициализирован'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/check_access', methods=['POST'])
@login_required
def api_check_access():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        card_number = data.get('card_number')
        pin_code = data.get('pin_code')
        device_id = data.get('device_id', 'test_device')
        
        if emergency_states['lockdown']:
            return jsonify({
                'success': False,
                'message': 'Доступ запрещен: активирован режим ЛОКДАУН'
            })
        
        user = None
        if card_number:
            user = get_user_by_card(card_number)
        elif pin_code:
            user = get_user_by_pin(pin_code)
        
        if user and user.get('status') == 'active':
            response = {
                'success': True,
                'message': f'Доступ разрешен для {user.get("name")}',
                'user': {
                    'id': user.get('id'),
                    'name': user.get('name')
                },
                'device_id': device_id,
                'timestamp': datetime.now().isoformat()
            }
            
            

            log_event(f"Тестовый доступ: {user.get('name')} - разрешен")
            
            return jsonify(response)
        else:
            return jsonify({
                'success': False,
                'message': 'Доступ запрещен - пользователь не найден или неактивен'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



from users_db import (
    setupUserDB, get_users, get_groups, add_user, delete_user, 
    update_user, get_user_by_id, get_user_by_card, get_user_by_pin,
    add_group, delete_group, update_group, get_group_by_id, 
    add_user_to_group, remove_user_from_group, check_user_access,
    get_all_doors, add_door, update_door, delete_door, get_door_by_device_id,
    get_door_permissions, set_door_permission, delete_door_permission,
    register_device, update_device_last_seen, migrate_data
)

def start():
    setupUserDB()
    ologger.setupLogger()
    
    try:
        from schedule_scheduler import start_schedule_scheduler
        schedule_scheduler = start_schedule_scheduler()
        print("Планировщик расписаний запущен")
    except Exception as e:
        print(f"Ошибка запуска планировщика расписаний: {e}")
    
    if __name__ == '__main__':
        print("Запуск сервера FiroAccess...")
        print("Планировщик расписаний активен")
        
        socketio.run(app, 
                    host='0.0.0.0', 
                    port=80, 
                    debug=True, 
                    allow_unsafe_werkzeug=True,
                    use_reloader=False)

if __name__ == '__main__':
    start()
