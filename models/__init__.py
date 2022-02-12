from datetime import datetime

from pony.orm import *

import utils
from .database import db


class CheckingSupported(db.Entity):
    """
    Support for checking parameters and selecting.
    """
    is_checking = Required(bool, default=False)
    last_checked = Optional(datetime)

    @property
    def need_checking(self):
        return (not self.is_checking and
                (self.last_checked is None or
                 self.last_checked == type(self).min(lambda o: o.last_checked)))

    # noinspection PyTypeChecker
    @classmethod
    def get_need_checking(cls, begin=True):
        """
        Get a new object that need checking. Will call begin_checking() if
        begin=True.

        :param begin: If it is True, call begin_checking() on received object
        :return: Object that need checking if any, None otherwise
        """
        obj = (cls
               .select(lambda o: o.need_checking)
               .order_by(cls.last_checked)
               .first())
        if begin and obj is not None:
            cls.begin_checking(obj)
        return obj

    @classmethod
    def begin_checking(cls, obj):
        """
        Start the checking process (set checking-related flags in database).

        :param obj: Object
        """
        with db_session:
            cls[obj.id].is_checking = True

    @classmethod
    def end_checking(cls, obj, **kwargs):
        """
        Stop checking and update object's values into database using the keyword
        arguments.

        :param obj: Object
        :param kwargs: Updating values
        """
        with db_session(retry=3):
            try:
                obj_by_id: 'CheckingSupported' = cls[obj.id]
            except ObjectNotFound:
                return

            for key, value in kwargs.items():
                obj_by_id.__setattr__(key, value)
            obj_by_id.is_checking = False
            obj_by_id.last_checked = datetime.now()

    def reset_status(self):
        """
        Reset all object's status.
        """
        self.is_checking = False
        self.last_checked = None


class SSH(CheckingSupported):
    """
    Store SSH information.
    """
    ip = Required(str)
    username = Optional(str)
    password = Optional(str)
    is_live = Required(bool, default=False)
    port = Optional('Port')

    @property
    def is_usable(self):
        return self.is_live and self.port is None

    @classmethod
    def get_ssh_for_port(cls, port: 'Port', unique=True):
        """
        Get a usable SSH for provided Port. Will not get one that was used by
        that Port before if unique=True.

        :param port: Port
        :param unique: True if the SSH cannot be used before by Port
        :return: Usable SSH for Port
        """
        # TODO test this
        query = cls.select(lambda s: s.is_usable)
        if unique:
            query = query.filter(lambda s: s not in port.used_ssh_list)
        return query.first()

    def reset_status(self):
        super().reset_status()
        self.port = None


class Port(CheckingSupported):
    """
    Store port information.
    """
    port_number = Required(int)
    ssh = Optional(SSH)
    external_ip = Optional(str)  # External IP after proxying through port
    used_ssh_list = Set(SSH)
    time_connected = Optional(datetime)

    @property
    def proxy_address(self):
        return f"socks5://{utils.get_ipv4_address()}:{self.port_number}"

    @classmethod
    def get_need_reset(cls, time_expired: datetime):
        # noinspection PyTypeChecker
        return (cls.select(lambda p: (p.ssh is not None
                                      and p.time_connected < time_expired))[:])

    @property
    def need_ssh(self):
        return self.ssh is None

    @classmethod
    def get_need_ssh(cls):
        return cls.select(lambda s: s.need_ssh).first()

    def connect_to_ssh(self, ssh: SSH):
        self.ssh = ssh
        self.time_connected = datetime.now()
        self.used_ssh_list.append(ssh)

    def disconnect_ssh(self, ssh: SSH, remove_from_used=False):
        self.ssh = None
        if remove_from_used:
            self.used_ssh_list.remove(ssh)

    def reset_status(self):
        super().reset_status()
        self.external_ip = ''
        self.ssh = None
        self.time_connected = None
        self.used_ssh_list = []
