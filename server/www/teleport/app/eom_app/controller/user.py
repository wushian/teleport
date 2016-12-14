# -*- coding: utf-8 -*-
import ctypes
import json
import os
import platform

from eom_app.app.configs import app_cfg
from eom_app.module import host
from eom_app.module import record
from eom_app.module import user
from .base import SwxAuthJsonHandler, SwxAdminHandler, SwxAdminJsonHandler

cfg = app_cfg()


def get_free_space_mb(folder):
    """ Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(None, None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes))
        return total_bytes.value / 1024 / 1024 / 1024, free_bytes.value / 1024 / 1024 / 1024
    else:
        st = os.statvfs(folder)
        return st.f_blocks * st.f_frsize / 1024 / 1024 / 1024, st.f_bavail * st.f_frsize / 1024 / 1024 / 1024


class IndexHandler(SwxAdminHandler):
    def get(self):
        self.render('user/index.mako')


class LogHandler(SwxAdminHandler):
    def get(self):
        #
        user_list = user.get_user_list()
        total_size, free_size = get_free_space_mb(cfg.data_path)

        config_list = host.get_config_list()
        ts_server = dict()
        ts_server['ip'] = config_list['ts_server_ip']
        ts_server['port'] = cfg.server_port

        self.render('log/index.mako', user_list=user_list, total_size=int(total_size), free_size=int(free_size), ts_server=ts_server)


class RecordHandler(SwxAdminHandler):
    def get(self, protocol, record_id):
        protocol = int(protocol)
        if protocol == 1:
            return
        elif protocol == 2:
            self.render('log/record.mako', record_id=record_id)
            return
        pass

class PlayRdpHandler(SwxAdminHandler):
    def get(self, ip, record_id):
        # protocol = int(protocol)
        # if protocol == 1:
        #     return
        # elif protocol == 2:
        #     self.render('log/record.mako', record_id=record_id)
        #     return
        # pass
        filename = os.path.join(cfg.data_path, 'replay', 'rdp', '{}'.format(record_id), 'tp-rdp.tpr')


class ComandLogHandler(SwxAdminHandler):
    def get(self, protocol, record_id):
        protocol = int(protocol)
        if protocol == 1:
            return
        elif protocol == 2:
            record_path = os.path.join(cfg.data_path, 'replay', 'ssh', '{}'.format(record_id))
            file_info = os.path.join(record_path, 'command_list.log')
            # file_info = r"E:\GitWork\teleport\share\data\replay\ssh\108\0.ts"
            try:
                file = open(file_info, 'r')
                data = file.read()
            except:
                self.write('open file error {}'.format(file_info))
                return
            # "Content-Type": "text/html; charset=UTF-8",
            self.set_header('Content-Type', 'text/plain; charset=UTF-8')
            if len(data) == 0:
                self.write('该用户没有操作')
            else:
                self.write(data)
            return


class RecordGetHeader(SwxAdminJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
        record_id = args['id']
        header = record.read_record_head(record_id)
        if header is None:
            return self.write_json(-1)
        term = record.read_record_term(record_id)
        if term is None:
            return self.write_json(-1)
        ret = dict()
        ret['header'] = header
        ret['term'] = term
        self.write_json(0, data=ret)


class RecordGetInfo(SwxAdminJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
        record_id = args['id']
        file_id = args['file_id']
        data = record.read_record_info(record_id, file_id)
        if data is None:
            return self.write_json(-1)
        self.write_json(0, data=data)


class DeleteLog(SwxAdminJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            log_list = args['log_list']
        data = record.delete_log(log_list)
        if data is None:
            return self.write_json(-1)
        self.write_json(0, data=data)


class LogList(SwxAdminJsonHandler):
    def post(self):
        filter = dict()
        order = dict()
        order['name'] = 'host_id'
        order['asc'] = True
        limit = dict()
        limit['page_index'] = 0
        limit['per_page'] = 25

        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)

            tmp = list()
            _filter = args['filter']
            if _filter is not None:
                for i in _filter:
                    if i == 'user_name':
                        _x = _filter[i].strip()
                        if _x == '全部':
                            tmp.append(i)

                    if i == 'search':
                        _x = _filter[i].strip()
                        if len(_x) == 0:
                            tmp.append(i)
                        continue

                for i in tmp:
                    del _filter[i]

                filter.update(_filter)

        _limit = args['limit']
        if _limit['page_index'] < 0:
            _limit['page_index'] = 0
        if _limit['per_page'] < 10:
            _limit['per_page'] = 10
        if _limit['per_page'] > 100:
            _limit['per_page'] = 100

        limit.update(_limit)

        _order = args['order']
        if _order is not None:
            order['name'] = _order['k']
            order['asc'] = _order['v']

        total, log_list = user.get_log_list(filter, _limit)
        ret = dict()
        ret['page_index'] = limit['page_index']
        ret['total'] = total
        ret['data'] = log_list

        self.write_json(0, data=ret)


class AuthHandler(SwxAdminHandler):
    def get(self, user_name):
        group_list = host.get_group_list()
        cert_list = host.get_cert_list()
        self.render('user/auth.mako',
                    group_list=group_list,
                    cert_list=cert_list, user_name=user_name)


class GetListHandler(SwxAdminJsonHandler):
    def post(self):
        user_list = user.get_user_list()
        ret = dict()
        ret['page_index'] = 10
        ret['total'] = len(user_list)
        ret['data'] = user_list
        self.write_json(0, data=ret)


class DeleteUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_id = args['user_id']
        try:
            ret = user.delete_user(user_id)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
            return
        except:
            self.write_json(-1)
            return


class ModifyUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return

        user_id = args['user_id']
        user_desc = args['user_desc']

        try:
            ret = user.modify_user(user_id, user_desc)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
            return
        except:
            self.write_json(-1)
            return


class AddUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_name = args['user_name']
        user_pwd = '123456'
        user_desc = args['user_desc']
        if user_desc is None:
            user_desc = ''
        try:
            ret = user.add_user(user_name, user_pwd, user_desc)
            self.write_json(ret)
            return
        except:
            self.write_json(-1)
            return


class LockUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_id = args['user_id']
        lock_status = args['lock_status']

        try:
            ret = user.lock_user(user_id, lock_status)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
            return
        except:
            self.write_json(-1)
            return

class ResetUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_id = args['user_id']
        # lock_status = args['lock_status']

        try:
            ret = user.reset_user(user_id)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
            return
        except:
            self.write_json(-1)
            return

class HostList(SwxAuthJsonHandler):
    def post(self):
        filter = dict()
        # user = self.get_current_user()
        order = dict()
        order['name'] = 'host_id'
        order['asc'] = True
        limit = dict()
        limit['page_index'] = 0
        limit['per_page'] = 25

        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)

            tmp = list()
            _filter = args['filter']
            for i in _filter:
                if i == 'host_sys_type' and _filter[i] == 0:
                    tmp.append(i)
                    continue
                if i == 'host_group' and _filter[i] == 0:
                    tmp.append(i)
                    continue
                if i == 'search':
                    _x = _filter[i].strip()
                    if len(_x) == 0:
                        tmp.append(i)
                    continue

            for i in tmp:
                del _filter[i]

            filter.update(_filter)
            # print('filter', filter)

            _limit = args['limit']
            if _limit['page_index'] < 0:
                _limit['page_index'] = 0
            if _limit['per_page'] < 10:
                _limit['per_page'] = 10
            if _limit['per_page'] > 100:
                _limit['per_page'] = 100

            limit.update(_limit)

            _order = args['order']
            if _order is not None:
                order['name'] = _order['k']
                order['asc'] = _order['v']
        # filter['account_name'] = user['name']
        _total, _hosts = host.get_host_info_list_by_user(filter, order, limit)

        ret = dict()
        ret['page_index'] = limit['page_index']
        ret['total'] = _total
        ret['data'] = _hosts
        self.write_json(0, data=ret)


class AllocHost(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_name = args['user_name']
        host_list = args['host_list']
        try:
            ret = user.alloc_host(user_name, host_list)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
        except:
            self.write_json(-2)


class AllocHostUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_name = args['user_name']
        host_auth_id_list = args['host_list']
        try:
            ret = user.alloc_host_user(user_name, host_auth_id_list)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
        except:
            self.write_json(-2)


class DeleteHost(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
            # print('args', args)
        else:
            # ret = {'code':-1}
            self.write_json(-1)
            return
        user_name = args['user_name']
        host_list = args['host_list']
        try:
            ret = user.delete_host(user_name, host_list)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
        except:
            self.write_json(-2)


class DeleteHostUser(SwxAuthJsonHandler):
    def post(self):
        args = self.get_argument('args', None)
        if args is not None:
            args = json.loads(args)
        else:
            self.write_json(-1)
            return
        user_name = args['user_name']
        auth_id_list = args['auth_id_list']
        try:
            ret = user.delete_host_user(user_name, auth_id_list)
            if ret:
                self.write_json(0)
            else:
                self.write_json(-1)
        except:
            self.write_json(-2)

