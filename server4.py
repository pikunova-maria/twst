import socket
import json
import threading
import signal
import sys
from typing import Set
tasks = []
tasks_counter = 1
active_clients: Set[socket.socket] = set()
shutdown_event = threading.Event()
tasks_lock = threading.Lock()
clients_lock = threading.Lock()
def handle_client(client_socket: socket.socket, address):
    with clients_lock:
        active_clients.add(client_socket)
    try:
        while not shutdown_event.is_set():
            client_socket.settimeout(1.0)
            try:
                request_data = client_socket.recv(1024).decode('utf-8')
                if not request_data:
                    break
                print(f"Получен запрос от {address}: {request_data}")
                try:
                    request = json.loads(request_data)
                except json.JSONDecodeError:
                    error_response = {'error': 'Invalid JSON format'}
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
                    continue
                action = request.get('action')
                print(f"Обрабатываю действие {action} для клиента {address}")
                response = {}
                if action == 'add':
                    task = request.get('task')
                    print(f"Добавляю задачу: {task}")
                    if task:
                        global tasks_counter
                        with tasks_lock:
                            tasks.append({
                                'id': tasks_counter,
                                'task': task,
                                'completed': False
                            })
                            current_id = tasks_counter
                            tasks_counter += 1
                        response = {'status': 'Задача добавлена', 'id': current_id}
                    else:
                        response = {'error': 'Нет задачи'}
                elif action == 'list':
                    with tasks_lock:
                        response = {'tasks': tasks.copy()}
                elif action == 'toggle':
                    if 'id' not in request:
                        response = {'error': 'Отсутствует идентификатор задачи (id) в запросе'}
                    else:
                        task_id = request['id']
                        if not isinstance(task_id, int):
                            response = {'error': 'Идентификатор задачи должен быть целым числом'}
                        else:
                            with tasks_lock:
                                task = next((t for t in tasks if t['id'] == task_id), None)
                                if task:
                                    task['completed'] = not task['completed']
                                    response = {'status': 'Статус задачи изменён'}
                                else:
                                    response = {'error': 'Задача не найдена'}
                else:
                    response = {'error': 'Неизвестное действие'}
                print(f"Отправляю ответ клиенту {address}: {response}")
                client_socket.send(json.dumps(response).encode('utf-8'))
            except socket.timeout:
                continue
            except Exception as e:
                if not shutdown_event.is_set():
                    print(f"Ошибка при обработке клиента {address}: {e}")
                break
    finally:
        with clients_lock:
            active_clients.discard(client_socket)
        try:
            client_socket.close()
        except:
            pass
        print(f"Соединение с клиентом {address} закрыто")
def graceful_shutdown(signum, frame):
    print(f"\nПолучен сигнал {signum} — инициируем graceful shutdown...")
    shutdown_event.set()
    print("Отключаем активных клиентов...")
    with clients_lock:
        clients_to_close = list(active_clients)
    for client_socket in clients_to_close:
        try:
            client_socket.send(json.dumps({'error': 'Сервер завершает работу'}).encode('utf-8'))
        except:
            pass
        try:
            client_socket.close()
        except:
            pass
    print("Ожидание завершения активных потоков...")
    main_thread = threading.current_thread()
    for t in threading.enumerate():
        if t is not main_thread:
            t.join(timeout=2.0)
    print("Сервер остановлен корректно.")
    sys.exit(0)
def start_server(host='localhost', port=50000):
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"Сервер запущен на {host}:{port}")
    print("Ожидание подключений... (Ctrl+C для завершения)")
    try:
        while not shutdown_event.is_set():
            try:
                server.settimeout(1.0)
                client_socket, address = server.accept()
                if shutdown_event.is_set():
                    client_socket.close()
                    break
                print(f"Новое подключение от: {address}")
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                print(f"Запущен поток для клиента {address}. Активных потоков: {threading.active_count()}")
            except socket.timeout:
                continue
            except OSError:
                break
    except KeyboardInterrupt:
        print("\nПерехват KeyboardInterrupt — инициируем shutdown...")
        graceful_shutdown(signal.SIGINT, None)
    finally:
        server.close()
        print("Главный сокет сервера закрыт.")
if __name__ == "__main__":
    start_server()