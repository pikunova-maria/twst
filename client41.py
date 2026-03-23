import socket
import json
import sys
SERVER_HOST = 'localhost'
SERVER_PORT = 50000
TIMEOUT = 10
def send_request(request):
    client = None
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(TIMEOUT)
        client.connect((SERVER_HOST, SERVER_PORT))
        request_json = json.dumps(request).encode('utf-8')
        client.send(request_json)
        response_data = client.recv(4096)
        if not response_data:
            print("Ошибка: Сервер вернул пустой ответ")
            return None
        response_str = response_data.decode('utf-8')
        try:
            response = json.loads(response_str)
            return response
        except json.JSONDecodeError:
            print(f"Ошибка: Невалидный JSON от сервера: {response_str}")
            return None
    except socket.timeout:
        print(f"Ошибка: Таймаут соединения ({TIMEOUT} сек)")
        return None
    except ConnectionRefusedError:
        print("Ошибка: Не удалось подключиться. Проверьте, запущен ли сервер.")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None
    finally:
        if client:
            try:
                client.close()
            except:
                pass
def print_tasks(tasks):
    if not tasks:
        print("Список задач пуст")
        return
    print("\n Ваши задачи:")
    for task in tasks:
        status_icon = "✅" if task.get('completed', False) else "⬜"
        task_id = task.get('id', '?')
        task_name = task.get('task', 'Без названия')
        print(f"{task_id}. {status_icon} {task_name}")
def main():
    print("🚀 Клиент для управления задачами")
    print("Команды:")
    print("  add <текст задачи>  — Добавить новую задачу")
    print("  list                — Показать все задачи")
    print("  toggle <ID>         — Изменить статус задачи")
    print("  exit                — Выход из программы")
    while True:
        try:
            command_input = input("\nВведите команду: ").strip()
            if not command_input:
                continue
            parts = command_input.split(maxsplit=1)
            action = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            if action == 'exit':
                print("Завершение работы клиента...")
                break
            elif action == 'add':
                if not args:
                    print("Ошибка: Укажите текст задачи. Пример: add Купить хлеб")
                    continue
                request = {'action': 'add', 'task': args}
                response = send_request(request)
                if response:
                    if 'status' in response:
                        print(f"{response['status']} (ID: {response.get('id', '?')})")
                    elif 'error' in response:
                        print(f"{response['error']}")
                    else:
                        print(f"Ответ: {response}")
            elif action == 'list':
                request = {'action': 'list'}
                response = send_request(request)
                if response:
                    if 'tasks' in response:
                        print_tasks(response['tasks'])
                    elif 'error' in response:
                        print(f"{response['error']}")
                    else:
                        print(f"Ответ: {response}")
            elif action == 'toggle':
                if not args:
                    print("Ошибка: Укажите ID задачи. Пример: toggle 1")
                    continue
                try:
                    task_id = int(args)
                    request = {'action': 'toggle', 'id': task_id}
                    response = send_request(request)
                    if response:
                        if 'status' in response:
                            print(f"{response['status']}")
                        elif 'error' in response:
                            print(f"{response['error']}")
                        else:
                            print(f"Ответ: {response}")
                except ValueError:
                    print("Ошибка: ID задачи должен быть целым числом")
            else:
                print(f"Неизвестная команда: {action}")
                print("Доступные: add, list, toggle, exit")
        except KeyboardInterrupt:
            print("\n\n Прервано пользователем. Выход...")
            break
        except EOFError:
            print("\n\n Ввод завершен. Выход...")
            break
if __name__ == "__main__":
    main()