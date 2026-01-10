import sqlite3
import time
import json
from datetime import datetime
from pathlib import Path

current_file = Path(__file__)
parent_dir = current_file.parent.parent
target_file = parent_dir / 'firo_access.db'
DB_NAME = target_file

def setupUserDB():
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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS DoorAccessSchedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        door_id TEXT NOT NULL,
        schedule_name TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        start_time_utc TIME NOT NULL,
        end_time_utc TIME NOT NULL,
        weekdays TEXT DEFAULT '1111111',
        access_type TEXT DEFAULT 'allow_all',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(door_id, schedule_name)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        name TEXT NOT NULL,
        id TEXT NOT NULL PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'active',
        groups TEXT NOT NULL DEFAULT '',
        creds TEXT NOT NULL DEFAULT '',
        pin INTEGER NOT NULL DEFAULT 0,
        cardcode TEXT NOT NULL DEFAULT '',
        liplate TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Groups (
        name TEXT NOT NULL,
        id TEXT NOT NULL PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'active',
        peo TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Doors (
        device_id TEXT NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'active',
        auto_created BOOLEAN DEFAULT 1,
        last_seen TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS DoorPermissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        permission_type TEXT NOT NULL DEFAULT 'allow',
        schedule TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(group_id, device_id),
        FOREIGN KEY (group_id) REFERENCES Groups(id),
        FOREIGN KEY (device_id) REFERENCES Doors(device_id)
    )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_id ON Users(id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_cardcode ON Users(cardcode)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_pin ON Users(pin)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_groups_id ON Groups(id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_doors_device ON Doors(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_group_device ON DoorPermissions(group_id, device_id)')

    connection.commit()
    connection.close()

    print(f"База данных '{DB_NAME}' успешно инициализирована")
    print("Созданы таблицы: Users, Groups, Doors, DoorPermissions")

def get_users():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users ORDER BY name')
    users_data = cursor.fetchall()

    Users = []
    for user in users_data:
        Users.append({
            'name': user[0],
            'id': user[1],
            'status': user[2],
            'groups': user[3],
            'creds': user[4],
            'pin': user[5],
            'cardcode': user[6],
            'liplate': user[7],
            'role': user[8],
            'created_at': user[9],
            'updated_at': user[10]
        })

    connection.close()
    return Users

def add_user(name, id, groups="", creds="", pin=0, cardcode="", liplate="", role="user", status="active"):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    INSERT INTO Users (name, id, status, groups, creds, pin, cardcode, liplate, role)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, id, status, groups, creds, pin, cardcode, liplate, role))

    connection.commit()
    connection.close()

def delete_user(user_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM Users WHERE id = ?', (user_id,))
    connection.commit()
    connection.close()

def update_user(user_id, **kwargs):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    if not kwargs:
        connection.close()
        return

    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(user_id)

    cursor.execute(f'UPDATE Users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
    connection.commit()
    connection.close()

def get_user_by_id(user_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users WHERE id = ? COLLATE NOCASE', (user_id,))
    user_data = cursor.fetchone()

    connection.close()

    if user_data:
        return {
            'name': user_data[0],
            'id': user_data[1],
            'status': user_data[2],
            'groups': user_data[3],
            'creds': user_data[4],
            'pin': user_data[5],
            'cardcode': user_data[6],
            'liplate': user_data[7],
            'role': user_data[8],
            'created_at': user_data[9],
            'updated_at': user_data[10]
        }
    return None

def get_user_by_card(card_number):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Users WHERE cardcode = ?', (card_number,))
    user_data = cursor.fetchone()

    connection.close()

    if user_data:
        return {
            'name': user_data[0],
            'id': user_data[1],
            'status': user_data[2],
            'groups': user_data[3],
            'creds': user_data[4],
            'pin': user_data[5],
            'cardcode': user_data[6],
            'liplate': user_data[7],
            'role': user_data[8],
            'created_at': user_data[9],
            'updated_at': user_data[10]
        }
    return None

def get_user_by_pin(pin_code):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    try:
        pin_int = int(pin_code)
    except ValueError:
        pin_int = 0

    cursor.execute('SELECT * FROM Users WHERE pin = ?', (pin_int,))
    user_data = cursor.fetchone()

    connection.close()

    if user_data:
        return {
            'name': user_data[0],
            'id': user_data[1],
            'status': user_data[2],
            'groups': user_data[3],
            'creds': user_data[4],
            'pin': user_data[5],
            'cardcode': user_data[6],
            'liplate': user_data[7],
            'role': user_data[8],
            'created_at': user_data[9],
            'updated_at': user_data[10]
        }
    return None

def add_door_schedule(door_id, schedule_name, start_time, end_time,
                     weekdays='1111111', access_type='allow_all'):
    start_time = start_time.strip()
    end_time = end_time.strip()

    import re
    time_pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'

    if not re.match(time_pattern, start_time) or not re.match(time_pattern, end_time):
        raise ValueError(f"Неверный формат времени. Должно быть HH:MM, получено: {start_time}, {end_time}")

    start_utc = start_time
    end_utc = end_time

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO DoorAccessSchedules
    (door_id, schedule_name, start_time_utc, end_time_utc, weekdays, access_type)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (door_id, schedule_name, start_utc, end_utc, weekdays, access_type))

    connection.commit()
    connection.close()
    print(f"Расписание '{schedule_name}' для {door_id}: {start_utc}-{end_utc} UTC")

def is_door_in_open_hours(door_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    current_utc = datetime.utcnow()
    current_time = current_utc.strftime('%H:%M')
    current_weekday = current_utc.weekday()
    query = '''
    SELECT access_type
    FROM DoorAccessSchedules
    WHERE door_id = ?
    AND is_active = 1
    AND ? BETWEEN start_time_utc AND end_time_utc
    AND substr(weekdays, ?, 1) = '1'
    LIMIT 1
    '''

    cursor.execute(query, (door_id, current_time, current_weekday + 1))
    result = cursor.fetchone()
    connection.close()

    return result[0] if result else None

def delete_door_schedule(schedule_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM DoorAccessSchedules WHERE id = ?', (schedule_id,))

    connection.commit()
    connection.close()
    print(f"Удалено расписание с ID: {schedule_id}")

def get_groups():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Groups ORDER BY name')
    groups_data = cursor.fetchall()

    Groups = []
    for group in groups_data:
        Groups.append({
            'name': group[0],
            'id': group[1],
            'status': group[2],
            'peo': group[3],
            'description': group[4],
            'created_at': group[5],
            'updated_at': group[6]
        })

    connection.close()
    return Groups

def add_group(name, id, status="active", peo="", description=""):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    INSERT INTO Groups (name, id, status, peo, description)
    VALUES (?, ?, ?, ?, ?)
    ''', (name, id, status, peo, description))

    connection.commit()
    connection.close()

def delete_group(group_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM Groups WHERE id = ?', (group_id,))
    connection.commit()
    connection.close()

def update_group(group_id, **kwargs):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    if not kwargs:
        connection.close()
        return

    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(group_id)

    cursor.execute(f'UPDATE Groups SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
    connection.commit()
    connection.close()

def get_group_by_id(group_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Groups WHERE id = ?', (group_id,))
    group_data = cursor.fetchone()

    connection.close()

    if group_data:
        return {
            'name': group_data[0],
            'id': group_data[1],
            'status': group_data[2],
            'peo': group_data[3],
            'description': group_data[4],
            'created_at': group_data[5],
            'updated_at': group_data[6]
        }
    return None

def add_user_to_group(user_id, group_id):
    user = get_user_by_id(user_id)
    if not user:
        return

    current_groups = user.get('groups', '')
    if group_id not in current_groups.split(','):
        new_groups = current_groups + f",{group_id}" if current_groups else group_id
        update_user(user_id, groups=new_groups)

def remove_user_from_group(user_id, group_id):
    user = get_user_by_id(user_id)
    if not user:
        return

    current_groups = user.get('groups', '')
    group_list = [g.strip() for g in current_groups.split(',') if g.strip()]
    if group_id in group_list:
        group_list.remove(group_id)
        new_groups = ','.join(group_list)
        update_user(user_id, groups=new_groups)

def register_device(device_id, name=None, ip_address=None):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT device_id FROM Doors WHERE device_id = ?', (device_id,))
    existing = cursor.fetchone()

    if not existing:
        if not name:
            name = f"Дверь {device_id}"

        description = f"Автоматически зарегистрирована"
        if ip_address:
            description += f" с IP {ip_address}"

        cursor.execute('''
        INSERT INTO Doors (device_id, name, description, auto_created, last_seen)
        VALUES (?, ?, ?, 1, ?)
        ''', (device_id, name, description, datetime.now().isoformat()))

        print(f"Автоматически зарегистрирована новая дверь: {device_id}")

    connection.commit()
    connection.close()

def update_device_last_seen(device_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    UPDATE Doors SET last_seen = ?, updated_at = CURRENT_TIMESTAMP WHERE device_id = ?
    ''', (datetime.now().isoformat(), device_id))

    connection.commit()
    connection.close()

def get_all_doors():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Doors ORDER BY name')
    doors_data = cursor.fetchall()

    doors = []
    for door in doors_data:
        doors.append({
            'device_id': door[0],
            'name': door[1],
            'location': door[2],
            'description': door[3],
            'status': door[4],
            'auto_created': bool(door[5]),
            'last_seen': door[6],
            'created_at': door[7],
            'updated_at': door[8]
        })

    connection.close()
    return doors

def get_door_by_device_id(device_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM Doors WHERE device_id = ?', (device_id,))
    door_data = cursor.fetchone()

    connection.close()

    if door_data:
        return {
            'device_id': door_data[0],
            'name': door_data[1],
            'location': door_data[2],
            'description': door_data[3],
            'status': door_data[4],
            'auto_created': bool(door_data[5]),
            'last_seen': door_data[6],
            'created_at': door_data[7],
            'updated_at': door_data[8]
        }
    return None

def add_door(device_id, name, location="", description="", status="active", auto_created=False):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    INSERT INTO Doors (device_id, name, location, description, status, auto_created)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (device_id, name, location, description, status, 1 if auto_created else 0))

    connection.commit()
    connection.close()

def update_door(device_id, **kwargs):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    if not kwargs:
        connection.close()
        return

    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values())
    values.append(device_id)

    cursor.execute(f'UPDATE Doors SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE device_id = ?', values)
    connection.commit()
    connection.close()

def delete_door(device_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM DoorPermissions WHERE device_id = ?', (device_id,))
    cursor.execute('DELETE FROM Doors WHERE device_id = ?', (device_id,))

    connection.commit()
    connection.close()

def set_door_permission(group_id, device_id, permission_type="allow", schedule="{}"):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    SELECT id FROM DoorPermissions
    WHERE group_id = ? AND device_id = ?
    ''', (group_id, device_id))

    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
        UPDATE DoorPermissions
        SET permission_type = ?, schedule = ?
        WHERE id = ?
        ''', (permission_type, schedule, existing[0]))
    else:
        cursor.execute('''
        INSERT INTO DoorPermissions (group_id, device_id, permission_type, schedule)
        VALUES (?, ?, ?, ?)
        ''', (group_id, device_id, permission_type, schedule))

    connection.commit()
    connection.close()

def delete_door_permission(permission_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM DoorPermissions WHERE id = ?', (permission_id,))
    connection.commit()
    connection.close()

def delete_door_permission_by_ids(group_id, device_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM DoorPermissions WHERE group_id = ? AND device_id = ?', (group_id, device_id))
    connection.commit()
    connection.close()

def get_door_permissions(device_id=None, group_id=None):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    query = '''
    SELECT dp.*, g.name as group_name, d.name as door_name
    FROM DoorPermissions dp
    LEFT JOIN Groups g ON dp.group_id = g.id
    LEFT JOIN Doors d ON dp.device_id = d.device_id
    WHERE 1=1
    '''

    params = []

    if device_id:
        query += ' AND dp.device_id = ?'
        params.append(device_id)

    if group_id:
        query += ' AND dp.group_id = ?'
        params.append(group_id)

    query += ' ORDER BY g.name, d.name'

    cursor.execute(query, params)
    permissions_data = cursor.fetchall()
    connection.close()

    permissions = []
    for perm in permissions_data:
        try:
            schedule_data = json.loads(perm[4]) if perm[4] else {}
        except:
            schedule_data = {}

        permissions.append({
            'id': perm[0],
            'group_id': perm[1],
            'device_id': perm[2],
            'permission_type': perm[3],
            'schedule': schedule_data,
            'created_at': perm[5],
            'updated_at': perm[6],
            'group_name': perm[7],
            'door_name': perm[8]
        })

    return permissions

def check_user_access(user, device_id, access_type='card'):
    door_schedule = is_door_in_open_hours(device_id)
    if door_schedule == 'allow_all':
        door = get_door_by_device_id(device_id)
        if door and door.get('status') == 'active':
            return True, "Свободный доступ (рабочие часы)"

    if not user:
        return False, "Пользователь не найден"

    if user.get('status', '').lower() != 'active':
        return False, "Пользователь не активен"

    if access_type == 'card':
        from scenarios_db import check_card_scenario
        check_card_scenario(user.get('cardcode'), user.get('name'))
        if not user.get('cardcode'):
            return False, "Карта не привязана"
    elif access_type == 'pin':
        if not user.get('pin') or user.get('pin') == 0:
            return False, "PIN не установлен"

    door = get_door_by_device_id(device_id)
    if not door:
        register_device(device_id)
        door = get_door_by_device_id(device_id)

        if not door:
            return False, "Дверь не найдена"

    if door.get('status', '').lower() != 'active':
        return False, "Дверь не активна"

    user_groups = user.get('groups', '')
    if not user_groups:
        return False, "Пользователь не состоит в группах"

    group_list = [g.strip() for g in user_groups.split(',') if g.strip()]
    if not group_list:
        return False, "Пользователь не состоит в группах"

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    placeholders = ','.join(['?'] * len(group_list))

    query = f'''
    SELECT permission_type, schedule
    FROM DoorPermissions
    WHERE group_id IN ({placeholders}) AND device_id = ?
    ORDER BY CASE WHEN permission_type = 'deny' THEN 1 ELSE 2 END
    LIMIT 1
    '''

    params = group_list + [device_id]
    cursor.execute(query, params)
    result = cursor.fetchone()

    connection.close()

    if result:
        permission_type = result[0]
        schedule_json = result[1]

        try:
            schedule = json.loads(schedule_json) if schedule_json else {}
        except:
            schedule = {}

        has_access_now = check_schedule_access(schedule)

        if permission_type == 'allow' and has_access_now:
            return True, "Доступ разрешен"
        else:
            return False, "Доступ запрещен"

    return False, "Нет разрешений для доступа"

def check_schedule_access(schedule):
    if not schedule:
        if 'always' in schedule and schedule['always']:
            return True

    current_utc = datetime.utcnow()
    current_hour = current_utc.hour
    current_minute = current_utc.minute
    current_time_str = f"{current_hour:02d}:{current_minute:02d}"

    if 'time_range' in schedule:
        start = schedule['time_range'].get('start', '00:00')
        end = schedule['time_range'].get('end', '23:59')

        return start <= current_time_str <= end

    return False

def get_accessible_doors_for_user(user_id):
    user = get_user_by_id(user_id)
    if not user or user.get('status', '').lower() != 'active':
        return []

    user_groups = user.get('groups', '')
    if not user_groups:
        return []

    group_list = [g.strip() for g in user_groups.split(',') if g.strip()]

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    placeholders = ','.join(['?'] * len(group_list))

    query = f'''
    SELECT DISTINCT d.*
    FROM Doors d
    JOIN DoorPermissions dp ON d.device_id = dp.device_id
    WHERE dp.group_id IN ({placeholders})
    AND dp.permission_type = 'allow'
    AND d.status = 'active'
    ORDER BY d.name
    '''

    cursor.execute(query, group_list)
    doors_data = cursor.fetchall()

    doors = []
    for door in doors_data:
        doors.append({
            'device_id': door[0],
            'name': door[1],
            'location': door[2],
            'description': door[3],
            'status': door[4],
            'auto_created': bool(door[5]),
            'last_seen': door[6],
            'created_at': door[7],
            'updated_at': door[8]
        })

    connection.close()
    return doors

def get_groups_for_door(device_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('''
    SELECT g.*, dp.permission_type, dp.schedule
    FROM Groups g
    JOIN DoorPermissions dp ON g.id = dp.group_id
    WHERE dp.device_id = ?
    ORDER BY g.name
    ''', (device_id,))

    groups_data = cursor.fetchall()
    connection.close()

    groups = []
    for group in groups_data:
        try:
            schedule_data = json.loads(group[7]) if group[7] else {}
        except:
            schedule_data = {}

        groups.append({
            'name': group[0],
            'id': group[1],
            'status': group[2],
            'peo': group[3],
            'description': group[4],
            'created_at': group[5],
            'updated_at': group[6],
            'permission_type': group[7],
            'schedule': schedule_data
        })

    return groups

def get_user_access_logs(user_id, limit=100):
    return []

def delete_door_schedule(schedule_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute('DELETE FROM DoorAccessSchedules WHERE id = ?', (schedule_id,))

    connection.commit()
    connection.close()

def migrate_data():
    print("Начинаем миграцию данных в firo_access.db...")

    import os

    if os.path.exists('UsersAc.db'):
        print("Перенос пользователей из UsersAc.db...")
        old_conn = sqlite3.connect('UsersAc.db')
        old_cursor = old_conn.cursor()
        old_cursor.execute('SELECT * FROM Users')
        old_users = old_cursor.fetchall()

        new_conn = sqlite3.connect(DB_NAME)
        new_cursor = new_conn.cursor()

        for user in old_users:
            try:
                new_cursor.execute('''
                INSERT OR REPLACE INTO Users (name, id, status, groups, creds, pin, cardcode, liplate, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', user)
            except Exception as e:
                print(f"Ошибка при переносе пользователя {user[1]}: {e}")

        new_conn.commit()
        new_conn.close()
        old_conn.close()
        print(f"Перенесено {len(old_users)} пользователей")

    if os.path.exists('GroupAc.db'):
        print("Перенос групп из GroupAc.db...")
        old_conn = sqlite3.connect('GroupAc.db')
        old_cursor = old_conn.cursor()
        old_cursor.execute('SELECT * FROM Groups')
        old_groups = old_cursor.fetchall()

        new_conn = sqlite3.connect(DB_NAME)
        new_cursor = new_conn.cursor()

        for group in old_groups:
            try:
                new_cursor.execute('''
                INSERT OR REPLACE INTO Groups (name, id, status, peo)
                VALUES (?, ?, ?, ?)
                ''', group)
            except Exception as e:
                print(f"Ошибка при переносе группы {group[1]}: {e}")

        new_conn.commit()
        new_conn.close()
        old_conn.close()
        print(f"Перенесено {len(old_groups)} групп")

    print("Миграция данных завершена!")

if __name__ == "__main__":
    setupUserDB()
    migrate_data()