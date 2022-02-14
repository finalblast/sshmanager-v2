import configparser
from dataclasses import dataclass
from typing import Any

CONFIG_FILE = 'config.ini'


@dataclass
class ConfigItem:
    section: str
    name: str
    full_name: str
    value: Any
    description: str
    need_restart: bool = False


DEFAULT_CONFIG = [
    ConfigItem(
        'SSH', 'tasks_count', 'ssh_tasks_count', 20,
        "Số thread check SSH live/die"),
    ConfigItem(
        'SSH', 'connection_timeout', 'connection_timeout', 20,
        "Thời gian kết nối tối đa SSH trước khi đánh dấu Die"),
    ConfigItem(
        'PORT', 'tasks_count', 'port_tasks_count', 20,
        "Số thread quản lý Port và kết nối SSH đến Port"),
    ConfigItem(
        'PORT', 'use_unique_ssh', 'use_unique_ssh', True,
        "Không dùng lại các SSH đã dùng ở mỗi Port"
    ),
    ConfigItem(
        'PORT', 'auto_reset_ports', 'auto_reset_ports', True,
        "Tự động đổi IP mỗi Port sau một thời gian nhất định"),
    ConfigItem(
        'PORT', 'reset_interval', 'port_reset_interval', 60,
        "Thời gian reset IP từng port (đổi IP mỗi x giây)"),
    ConfigItem(
        'WEB', 'workers', 'web_workers_count', 5,
        "Số workers chạy web (tăng tốc độ truy cập giao diện web)",
        need_restart=True),
    ConfigItem(
        'WEB', 'port', 'web_port', 6080,
        "Port chạy web (truy cập web bằng link http://<ip>:<port>)",
        need_restart=True),
]

PYDANTIC_ARGS = {}
for i in DEFAULT_CONFIG:
    PYDANTIC_ARGS[i.full_name] = (type(i.value), i.value)


def get_default_config():
    config = configparser.ConfigParser()
    for item in DEFAULT_CONFIG:
        if item.section not in config.sections():
            config.add_section(item.section)
        config[item.section][item.name] = str(item.value)
    return config


def get_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    if not config.sections():
        config = get_default_config()
        write_config(config)
    return config


def get_config_value(item: ConfigItem):
    config = get_config()
    t = type(item.value)
    value = config.get(item.section, item.name)
    return t(value)


def write_config(config):
    with open(CONFIG_FILE, 'w+') as file:
        config.write(file)


def reset_config():
    write_config(get_default_config())
