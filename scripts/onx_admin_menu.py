#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import onx_nodes as nodes_cli


DEFAULT_ENV_FILE = "/etc/onx/onx.env"
DEFAULT_ADMIN_AUTH_FILE = "/etc/onx/admin-auth.txt"
DEFAULT_CLIENT_AUTH_FILE = "/etc/onx/client-auth.txt"
DEFAULT_BASE_URL = "http://127.0.0.1:8081/api/v1"
DEFAULT_SERVICE_NAME = "onx-api.service"


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _pause(message: str = "Нажми Enter, чтобы продолжить...") -> None:
    try:
        input(message)
    except EOFError:
        pass


def _read_primary_token(path: Path) -> str | None:
    return nodes_cli._read_primary_token(path)


def _load_env(path: Path) -> None:
    nodes_cli._load_env_file(path)


def _derive_base_url(value: str | None) -> str:
    return nodes_cli._derive_base_url(value)


def _run_command(command: list[str], *, cwd: Path | None = None) -> int:
    completed = subprocess.run(command, cwd=str(cwd) if cwd else None, check=False)
    return completed.returncode


def _health_summary(base_url: str) -> str:
    try:
        payload = nodes_cli._request_json(base_url, "GET", "/health", token=None)
    except Exception as exc:  # pragma: no cover - operational path
        return f"health=down ({exc})"
    if isinstance(payload, dict):
        status = payload.get("status") or "ok"
        version = payload.get("version") or "-"
        return f"health={status} version={version}"
    return "health=unknown"


def _service_summary(service_name: str) -> str:
    result = subprocess.run(
        ["systemctl", "is-active", service_name],
        check=False,
        capture_output=True,
        text=True,
    )
    status = (result.stdout or result.stderr).strip() or "unknown"
    return f"daemon={status}"


def _status_screen(base_url: str, service_name: str) -> None:
    _clear_screen()
    print("ONX")
    print()
    print(_service_summary(service_name))
    print(_health_summary(base_url))
    print()
    _run_command(["systemctl", "status", service_name, "--no-pager"])
    _pause()


def _list_nodes(base_url: str, admin_token: str | None) -> None:
    _clear_screen()
    print("ONX / Nodes")
    print()
    try:
        nodes = nodes_cli._request_json(base_url, "GET", "/nodes", token=admin_token)
    except Exception as exc:
        print(f"Ошибка: {exc}")
        _pause()
        return

    if not isinstance(nodes, list) or not nodes:
        print("Нод пока нет.")
        _pause()
        return

    header = f"{'NAME':<24} {'ROLE':<10} {'STATUS':<12} {'SSH':<24} {'MGMT':<24}"
    print(header)
    print("-" * len(header))
    for node in nodes:
        print(
            f"{str(node.get('name') or '-'):<24} "
            f"{str(node.get('role') or '-'):<10} "
            f"{str(node.get('status') or '-'):<12} "
            f"{str(node.get('ssh_host') or '-'):<24} "
            f"{str(node.get('management_address') or '-'):<24}"
        )
    print()
    _pause()


def _build_nodes_args(
    *,
    base_url: str,
    admin_token: str | None,
    node_ref: str | None = None,
    wait: bool = True,
    yes: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        env_file=DEFAULT_ENV_FILE,
        base_url=base_url,
        admin_auth_file=DEFAULT_ADMIN_AUTH_FILE,
        admin_token=admin_token,
        node_ref=node_ref,
        wait=wait,
        poll_interval=2,
        yes=yes,
        name=None,
        role=None,
        management_address=None,
        ssh_host=None,
        ssh_port=None,
        ssh_user=None,
        auth_type=None,
        private_key_file=None,
        secret_value=None,
    )


def _create_node(base_url: str, admin_token: str | None) -> None:
    _clear_screen()
    print("ONX / Create Node")
    print()
    try:
        nodes_cli._add_node(_build_nodes_args(base_url=base_url, admin_token=admin_token))
    except Exception as exc:
        print(f"Ошибка: {exc}")
    print()
    _pause()


def _edit_node(base_url: str, admin_token: str | None) -> None:
    _clear_screen()
    print("ONX / Edit Node")
    print()
    node_ref = input("Имя ноды: ").strip()
    if not node_ref:
        return
    try:
        nodes_cli._edit_node(_build_nodes_args(base_url=base_url, admin_token=admin_token, node_ref=node_ref))
    except Exception as exc:
        print(f"Ошибка: {exc}")
    print()
    _pause()


def _delete_node(base_url: str, admin_token: str | None) -> None:
    _clear_screen()
    print("ONX / Delete Node")
    print()
    node_ref = input("Имя ноды: ").strip()
    if not node_ref:
        return
    try:
        nodes_cli._delete_node(
            _build_nodes_args(
                base_url=base_url,
                admin_token=admin_token,
                node_ref=node_ref,
                yes=False,
            )
        )
    except Exception as exc:
        print(f"Ошибка: {exc}")
    print()
    _pause()


def _nodes_menu(base_url: str, admin_token: str | None) -> None:
    while True:
        _clear_screen()
        print("ONX / Nodes")
        print()
        print("1. Создать ноду")
        print("2. Вывести список нод")
        print("3. Редактировать существующую ноду")
        print("4. Удалить ноду")
        print("5. Назад")
        print()
        choice = input("Выбор: ").strip()
        if choice == "1":
            _create_node(base_url, admin_token)
        elif choice == "2":
            _list_nodes(base_url, admin_token)
        elif choice == "3":
            _edit_node(base_url, admin_token)
        elif choice == "4":
            _delete_node(base_url, admin_token)
        elif choice == "5":
            return


def _restart_daemon(service_name: str) -> None:
    _clear_screen()
    print("ONX / Restart Daemon")
    print()
    rc = _run_command(["systemctl", "restart", service_name])
    if rc == 0:
        print("Демон перезапущен.")
    else:
        print(f"Перезапуск завершился с кодом {rc}.")
    print()
    _run_command(["systemctl", "status", service_name, "--no-pager"])
    _pause()


def _run_smoke(base_url: str, install_dir: Path, client_auth_file: Path, admin_auth_file: Path) -> None:
    _clear_screen()
    print("ONX / Smoke Test")
    print()

    client_token = _read_primary_token(client_auth_file)
    admin_token = _read_primary_token(admin_auth_file)
    venv_python = install_dir / ".venv-onx" / "bin" / "python3"
    smoke_script = install_dir / "scripts" / "onx_alpha_smoke.py"
    if not venv_python.exists():
        print(f"Не найден python venv: {venv_python}")
        _pause()
        return
    if not smoke_script.exists():
        print(f"Не найден smoke script: {smoke_script}")
        _pause()
        return

    command = [
        str(venv_python),
        str(smoke_script),
        "--base-url",
        base_url,
        "--expect-auth",
        "--check-rate-limit",
    ]
    if client_token:
        command.extend(["--client-bearer-token", client_token])
    if admin_token:
        command.extend(["--admin-bearer-token", admin_token])

    rc = _run_command(command, cwd=install_dir)
    print()
    if rc == 0:
        print("Smoke-test прошёл.")
    else:
        print(f"Smoke-test завершился с кодом {rc}.")
    _pause()


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive ONX admin menu.")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Path to ONX env file")
    parser.add_argument("--admin-auth-file", default=DEFAULT_ADMIN_AUTH_FILE, help="Path to ONX admin auth file")
    parser.add_argument("--client-auth-file", default=DEFAULT_CLIENT_AUTH_FILE, help="Path to ONX client auth file")
    parser.add_argument("--base-url", default=None, help=f"ONX admin API base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--service-name", default=DEFAULT_SERVICE_NAME, help="Systemd service name")
    parser.add_argument("--install-dir", default=str(Path(__file__).resolve().parents[1]), help="ONX install dir")
    args = parser.parse_args()

    _load_env(Path(args.env_file).resolve())
    admin_token = _read_primary_token(Path(args.admin_auth_file).resolve())
    base_url = _derive_base_url(args.base_url)
    install_dir = Path(args.install_dir).resolve()
    client_auth_file = Path(args.client_auth_file).resolve()
    admin_auth_file = Path(args.admin_auth_file).resolve()

    while True:
        _clear_screen()
        print("ONX")
        print()
        print(_service_summary(args.service_name))
        print(_health_summary(base_url))
        print()
        print("1. Статус демона")
        print("2. Работа с нодами")
        print("3. Перезапустить демон")
        print("4. Smoke-test")
        print("5. Выход")
        print()
        choice = input("Выбор: ").strip()
        if choice == "1":
            _status_screen(base_url, args.service_name)
        elif choice == "2":
            _nodes_menu(base_url, admin_token)
        elif choice == "3":
            _restart_daemon(args.service_name)
        elif choice == "4":
            _run_smoke(base_url, install_dir, client_auth_file, admin_auth_file)
        elif choice == "5":
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
