#!/usr/bin/env python3
# Databse Interface
#
# Copyright (c) 2020 Ivan , Dicom R&D
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
import uuid
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime
from .const import (LIST_TYPE_CHANNEL_BRAND,
                   LIST_MODEL_DEVICE_BRAND, NAME_TYPE_CHANNEL, TYPE_DEVICE)
from .config import DATABASE

LOGGER = logging.getLogger("Database")
DB_VERSION = 0x0001


class DbInterface(object):
    """docstring fs DbInterface."""

    def __init__(self, app=None):
        self._db = sqlite3.connect(DATABASE, check_same_thread=False)
        self._cursor = self._db.cursor()
        self._lock = threading.Lock()
        self.clear_notifi()
        self._alarm_on = self.get_rule_alarm(1)
        self._alarm_off = self.get_rule_alarm(2)
        self._athome = self.get_rule_alarm(3)
        self._sos = self.get_rule_alarm(4)
        self._door_reminder = {}
        self._door_sensor = {}
        self.data_init()
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        '''Always remember to close properly for changes to be saved.'''
        if self._db:
            self._db.commit()
            self._cursor.close()
            self._db.close()

    def execute(self, *args, **kwargs):
        try:
            self._lock_acquire()
            return self._cursor.execute(*args, **kwargs)
        except Exception as e:
            print(e)
        finally:
            self._lock_release()

    def executemany(self, *args, **kwargs):
        try:
            self._lock_acquire()
            return self._cursor.executemany(*args, **kwargs)
        except Exception as e:
            print(e)
        finally:
            self._lock_release()

    def _lock_acquire(self):
        LOGGER.debug('Acquire Lock on device %s', self)
        r = self._lock.acquire(True)
        if not r:
            print('Failed to acquire Lock on device %s', self)

    def _lock_release(self):
        LOGGER.debug('Release Lock on device %s', self)
        if not self._lock.locked():
            print('Device Lock not locked for device %s !', self)
        else:
            self._lock.release()

    def _fetchall(self, table):
        '''Gets and returns an entire row (in a list) of data from the DB given:
        table = Name of the table
        column = Name of the column in the row
        value = The number of the row (Primary Key ID)'''
        try:
            # self._db.row_factory = lambda c, r: dict([(column[0], r[idx]) for idx, column in enumerate(c.description)])
            return self.execute("SELECT * FROM {};".format(table)).fetchall()
        except Exception as e:
               LOGGER.error('Fetchall error %s', e)

    def _fetchall_col(self, table, column=None):
        '''Gets and returns an entire row (in a list) of data from the DB given:
        table = Name of the table
        column = Name of the column in the row
        value = The number of the row (Primary Key ID)'''
        try:
            # self._db.row_factory = lambda c, r: dict([(column[0], r[idx]) for idx, column in enumerate(c.description)])
            return self.execute("SELECT {} FROM {};".format(column, table)).fetchall()
        except Exception as e:
               LOGGER.error('Fetchall col %s', e)

    def _fetchone(self, table, column=None, value=None):
        '''Gets and returns a single piece of data from the DB given:
        table = Name of the table
        column = Name of the column being read
        id = The number of the row (Primary Key ID)
        '''
        # self._db.row_factory = lambda c, r: dict([(column[0], r[idx]) for idx, column in enumerate(c.description)])
        try:
            return self.execute("SELECT * FROM {} WHERE {}='{}';".format(table, column, value)).fetchone()
        except Exception as e:
               LOGGER.error('Fetchone error %s', e)

    def _fetch_by_col(self, table, column=None, value=None):
        '''Gets and returns a single piece of data from the DB given:
        table = Name of the table
        column = Name of the column being read
        id = The number of the row (Primary Key ID)
        '''
        # self._db.row_factory = lambda c, r: dict([(column[0], r[idx]) for idx, column in enumerate(c.description)])
        try:
            return self.execute("SELECT * FROM {} WHERE {}='{}';".format(table, column, value)).fetchall()
        except Exception as e:
               LOGGER.error('Fetchone col error %s', e)

    def _fetch_multi(self, table, column1, column2, condi1, condi2):
        try:
            # self._db.row_factory = lambda c, r: dict([(column[0], r[idx]) for idx, column in enumerate(c.description)])
            return self.execute("SELECT * FROM {} WHERE {}='{}' and {}={};".format(table, column1, condi1, column2, condi2)).fetchall()
        except Exception as e:
               LOGGER.error('Fetch multi col %s', e)
    def _add_new(self, table, column, value, save=True):
        query = "INSERT OR IGNORE INTO {} ({}) VALUES {};".format(
                table, column, value)
        try:
            LOGGER.debug('ADD NEW DATA: %s', query)
            ex = self.execute(query)
            if save and ex:
                self._db.commit()
                return ex.lastrowid
        except Exception as e:
               LOGGER.error('Insert error: %s', e)
        # finally:
        #     # self._cursor.close()

    def _update_one(self, table, column, value, id):
        '''Update a single piece of data from the DB given:
        table = Name of the table
        column = Name of the column being read
        id = The number of the row (Primary Key ID)
        value = The data to be written to this space'''
        try:
            query = "UPDATE {} SET {}='{}' WHERE id='{}';".format(
                    table, column, value, id)
            # LOGGER.debug('Update one: %s', query)
            self.execute(query)
            self._db.commit()
        except Exception as e:
               LOGGER.error('UPDATE one error: %s', e)

    def _update_all(self, table, columns, value, id):
        '''Overwrites a whole row of data from the DB given:
        table = Name of the table
        columns = A list of the names of the columns in the row
        values = A list of the new values to be written
        id = The number of the row (Primary Key ID)'''
        try:
            query = "UPDATE %s SET " % table
            for x in range(0, len(columns)):
                query += ("%s='%s', " % (columns[x], values[x]))
            query = query[:-2] + (" WHERE id = %s" % (id))
            # LOGGER.debug('Update one: %s', query)
            self.execute(query)
            self._db.commit()
        except Exception as e:
            LOGGER.error('UPDATE all error: %s', e)

    def _update_one_col(self, table, column, value, col_condition, value_condition):
        '''Update a single piece of data from the DB given:
        table = Name of the table
        column = Name of the column being read
        id = The number of the row (Primary Key ID)
        value = The data to be written to this space
        condition = Where column in db
        '''
        try:
            query = "UPDATE {} SET {}='{}' WHERE {}='{}';".format(
                    table, column, value, col_condition, value_condition)
            # LOGGER.debug('Update one col: %s', query)
            if self.execute(query):
                self._db.commit()
        except Exception as e:
               LOGGER.error('UPDATE one col error: %s', e)

    def _get_id(self, table, value):
        return self._fetchone(table, 'id', value)[0]

    def _remove(self, table, column, value):
        try:
            query = "DELETE FROM {} WHERE {}='{}';".format(
                    table, column, value)
            if self.execute(query):
                self._db.commit()
                return True
        except Exception as e:
               LOGGER.error("REMOVE row in table error : %s", e)
               return False
    def _remove_muti(self, table, column1, column2, value1, value2):
        try:
            query = "DELETE FROM {} WHERE {}='{}' AND {}='{}';".format(
                    table, column1, value1, column2, value2)
            if self.execute(query):
                self._db.commit()
                return True
        except Exception as e:
               LOGGER.error("REMOVE muti row in table error : %s", e)
               return False

    def _to_dict(self, value):
        if value:
            return json.loads(value)
        else:
            return None

    def data_init(self):
        id = self._fetchone("rules","type",5)[0]
        self._door_reminder = self.get_rule(id=id)
    ##### ADD_NEW DEVICE #######

    def _save_device(self, device):
        try:
           id = []
           id.append(str(uuid.uuid4()))
           id.append(str(uuid.uuid4()))
           addr = device['addr']
           detail = device['info']
           ieee = detail.get("ieee", ' ')
           device_id = self._fetchone("devices", "ieee", ieee)
           channel_id = self._fetchone("channels", "ieee", ieee)

           if device_id and channel_id:
               LOGGER.debug('Dumplicate devices no need to do')
               query_update_channel = "UPDATE channels SET name=?,type=?,room_id=? WHERE id=?;"
               return self.get_device_channel(id=device_id[0])
           elif device_id and channel_id is None:
               LOGGER.debug('Update channel info :%',device_id)
               self._add_new_channels(
                   device_id[0], id[1], ieee, device.get('endpoints', []))
               self._db.commit()
               return self.get_device_channel(id=device_id[0])
           else:
               LOGGER.debug('Create new device')
               self._add_new("devices", """id, ieee, addr, discovery, generictype, ids, bit_field, descriptor_capability,
   						 lqi, mac_capability, manufacturer_code, power_type, server_mask, rejoin_status, created, updated ,last_seen""", (id[0], ieee, addr,
                                                                                                                           device.get("discovery", "no"), device.get(
                   "generictype", "no"), detail.get("id", 0), detail.get("bit_field", 0),
                   detail.get("descriptor_capability", 0), detail.get("lqi", 0), detail.get(
                   "mac_capability", 0), detail.get("manufacturer_code", 0),
                   detail.get("power_type", 0), detail.get("server_mask", 0), int(detail.get("rejoin_status", 0)), int(time.time()), int(time.time()), int(time.time())))

               self._add_new_channels(id[0], id[1], ieee, device['endpoints'])
               self._db.commit()
               return self.get_device_channel(id=id[0])
        except Exception as e:
             LOGGER.debug('Add new device error : %s',exc_info=True)
    def _add_new_channels(self, device_id, channel_id, ieee, enpoints):
        config = ""
        zone_id = self.generate_zone_id()
        for endpoint in enpoints:
            self._add_new("channels", "id, ieee, endpoint_id, type, config, profile_id, device_type, in_clusters, out_clusters,zone_id,zone_status, created, updated, favorite,notification,device_id", (channel_id, ieee,
                                                                                                                                                                                                         endpoint['endpoint'], 0, config, endpoint['profile'], endpoint['device'], json.dumps(endpoint['in_clusters']), json.dumps(endpoint['out_clusters']), zone_id, 1, int(time.time()), int(time.time()), 0, 0, device_id))
            for cluster in endpoint['in_clusters']:
                self._add_new("clusters", "ieee, endpoint_id, cluster",
                                          (ieee, endpoint['endpoint'], cluster))
            list_status = {}
            type_channel = None
            for cluster in list(endpoint['clusters']):
                for attribute in cluster['attributes']:
                    if int(cluster['cluster']) == 0 and int(attribute['attribute']) == 5:
                        model = attribute.get('value', None)
                        if model:
                            self.set_device_type(model, device_id)
                            type_channel = self.set_type_channels(model, channel_id)
                            self._db.commit()
                            self._add_new("attributes", "ieee,endpoint_id,cluster,attribute,expire,data,name,type,value", (ieee, endpoint['endpoint'], cluster['cluster'], attribute['attribute'],
                                                                                                                           attribute.get('expire', 0), attribute.get('data', None), attribute.get('name', None), attribute.get('type', None), attribute.get('value', None)))
                        else:
                            self.remove_device(device_id)
                            break
                    # IAS ZONE
                    elif int(cluster['cluster']) == 1280 and attribute.get('name', None) == "zone_status":
                        value = attribute.get('value', None)
                        alarm_status = {"alarm1": int(value['alarm1']), "alarm2": int(value['alarm2']), "tamper": int(value['tamper']), "low_battery": int(value['low_battery']), "supervision": int(value['supervision']),
                                        "restore": int(value['restore']), "trouble": int(value['trouble']), "ac_fault": int(value['ac_fault']), "test_mode": int(value['test_mode']),
                                        "battery_defect": int(value['battery_defect']), "armed": int(value['armed']), "disarmed": int(value['disarmed']), "athome": int(value['athome'])}
                        self._add_new("attributes", "ieee, endpoint_id, cluster, attribute, zone_status,name, type", (
                            ieee, endpoint['endpoint'], cluster['cluster'], attribute['attribute'], json.dumps(alarm_status), attribute['name'], attribute['type']))
                        # channel_info = self.execute("SELECT type,ieee,zone_id FROM channels WHERE id='{}';".format(channel_id)).fetchone()
                        self.set_status_channel(alarm_status, channel_id, type_channel)
                        self.add_device_to_rule_secure(channel_id, type_channel, ieee)
                    else:
                        if int(cluster['cluster']) == 1026:
                            list_status["temperature"] = attribute.get(
                                'value', None)
                        elif int(cluster['cluster']) == 1029:
                            list_status["humidity"] = attribute.get(
                                'value', None)
                        elif int(cluster['cluster']) == 6:
                            list_status["onoff"] = attribute.get('value', None)
                        else:
                            pass
                    # OTHER DEVICE
                        self._add_new("attributes", "ieee,endpoint_id,cluster,attribute,expire,data,name,type,value", (ieee, endpoint['endpoint'], cluster['cluster'], attribute['attribute'],
                                                                                                                       attribute.get('expire', 0), attribute.get('data', None), attribute.get('name', None), attribute.get('type', None), attribute.get('value', None)))

            if not list_status:
                 pass
            else:
                self.set_status_channel(list_status, channel_id, type_channel)

    ##### LOAD DEVICE ##########

    def _load_device(self):
        try:
            devices = []
            for ieee in self._fetchall("devices"):
                device = {}
                device["addr"] = ieee[2]
                device["discovery"] = ieee[4]
                device["generictype"] = ieee[11]
                device["info"] = {"addr": ieee[2], "id": ieee[12], "bit_field": ieee[13], "descriptor_capability": ieee[14],
                                  "ieee": ieee[3], "last_seen": ieee[24], "lqi": ieee[15], "mac_capability": ieee[16], "manufacturer_code": ieee[17],
                                  "power_type": ieee[18], "server_mask": ieee[20], "rejoin_status": ieee[21]}
                enpoints = []
                for endt in self._fetch_by_col("channels", 'ieee', ieee[3]):
                    enpoint = {}
                    enpoint["device"] = endt[8]
                    enpoint["endpoint"] = endt[3]
                    enpoint["in_clusters"] = json.loads(endt[9])
                    enpoint["out_clusters"] = json.loads(endt[10])
                    enpoint["profile"] = endt[7]
                    clusters = []
                    for clu in json.loads(endt[9]):
                        cluster = {}
                        cluster["cluster"] = clu
                        attributes = []
                        for cl in self._fetch_multi("attributes", "ieee", "cluster", ieee[3], clu):
                            attribute = {}
                            attribute["attribute"] = cl[3]
                            attribute["expire"] = cl[4]
                            attribute["name"] = cl[7]
                            attribute["type"] = cl[8]
                            if cl[7] == "zone_status":
                                res = json.loads(cl[5])
                                attribute["value"] = res
                                attribute["data"] = res
                            else:
                                attribute["data"] = cl[6]
                                attribute["value"] = cl[9]
                            # print(attribute)
                            attributes.append(attribute)
                        cluster["attributes"] = attributes
                        clusters.append(cluster)
                        enpoint["clusters"] = clusters
                enpoints.append(enpoint)
                device["endpoints"] = enpoints
                devices.append(device)
            return devices
        except Exception as e:
               LOGGER.debug('Load device to zigate error:',exc_info=True)

    ######   HOMEGATE ##########
    def get_homegate_info(self):
        self._db.row_factory = lambda c, r: dict(
            [(column[0], r[idx]) for idx, column in enumerate(c.description)])
        query = "SELECT id,name,model,serial, ip_local, ip_public, zig_version, sw_version, config, updated, last_update FROM homegate"
        hg = self.execute(query)
        data = {"id": hg[0], "name": hg[1], "model": hg[2], "serial_number": hg[3], "ip_local": hg[4], "ip_public": hg[5],
                "zig_version": hg[6], "sw_version": hg[7], "config": self._to_dict(hg[8]), "updated": hg[9], "last_update": hg[10]}
        return data

    def set_homegate_entity(self):
        return self._fetchall("homegate")[0]

    def get_homegate_info_all(self):
        try:
            hg = self._fetchall("homegate")[0]
            data = {"id": hg[0], "site": hg[1], "name": hg[2], "token": hg[3], "wan_mac": hg[4], "wwan_mac": hg[5], "ip_local": hg[6], "ip_public": hg[7], "model": hg[8], "serial": hg[9],
                    "zig_version": hg[12], "sw_version": hg[13], "hw_version": hg[14], "state": hg[10], "config": self._to_dict(hg[11]), "created": hg[15], "updated": hg[16], "last_update": hg[17], "last_seen": hg[18]}
            return data
        except Exception as e:
            print(e)

    def add_homegate_info(self, data):
        try:
            query = """DELETE * from homegate;
                       INSERT OR IGNORE INTO homegate(id,name,site,wan_mac,wwan_mac,ip_local,
                       ip_public,model,serial,state,config,zig_version,hw_version,sw_version,
                       updated,last_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       """
            self.execute(query, (data.id, data.name, data.site, data.wan_mac, data.wwan_mac, data.ip_local, data.ip_public, data.model,
                                 data.serial, data.state, json.dumps(data.config), data.zig_version, data.hw_version, data.sw_version,int(time.time()), int(time.time())))
            self._db.commit()
            return True
        except Exception as e:
            print(e)
            return e

    def update_homegate_info(self, colum, value, id):
        try:
            query = "UPDATE homegate SET {}='{}' WHERE id='{}'".format(
                    colum, value, id)
            self.execute(query)
            self._db.commit()
            return True
        except Exception as e:
            return e
            print(e)

    def update_total_homegate_db(self):
        list = {}
        hg = self.get_homegate_info_all()
        list['id'] = hg['id']
        list['devices'] = self.get_device_channel(all=True)
        list['rules'] = self.get_rule(all=True)
        list['homegate'] = hg
        list['rooms'] = self.get_room(all=True)
        list['camera'] = self.get_camera(all=True)
        list['groups'] = None
        return list
    ###### USER ##########

    def get_user(self, id):
        return self._fetchone("users", "id", id)

    def udpate_user(self, data, id):
        pass

    def add_channel_to_user(self, user_id, channel_id):
        return self._add_new("user_access", "user_id,channel_id,created", (user_id, channel_id, int(time.time())))

    def add_user(self, user_id, name, permission_type, access_token):
        user = self._fetchone("users", "id", user_id)
        if user:
            return user
        else:
            return self._add_new("users", "id,name,permission_type,status,access_token,created,last_seen", (user_id, name, permission_type, 1, access_token, int(time.time()), int(time.time())))

    def remove_user(self, user_id):
        return self._remove("users", "id", user_id)

    def remove_user_accsess(self, channel_id):
        pass

    def check_user_access_channle(self, user_id, channel_id):
        return self._fetch_multi("user_access", "user_id", "channel_id", user_id, channel_id)

    def get_all_user(self):
        return self._fetchall("users")

    def get_all_user_token(self):
        return self._fetchall_col("users", "id,access_token")

    def get_all_user_id(self):
        return self._fetchall_col("users", "id")

    def get_all_user_id(self):
        return self.execute("SELECT id from users;").fetchall()[0]
    ###### ROOM ##########

    def get_default_room(self):
        return self._fetchone("rooms", "name", "Mặc định")[0]

    def get_room(self, all=False, id=False):
        list_room = []
        if all:
            for r in self._fetchall("rooms"):
                obj = {"id": r[0], "name": r[1], "icon": r[2], "channels": self._to_dict(r[3]), "floor_id": str(r[4]), "created": r[5], "updated": r[6]}
                list_room.append(obj)
            return list_room
        if id:
            for r in self._fetchone("rooms", "id", id):
                obj = {"id": r[0], "name": r[1], "icon": r[2], "channels": self._to_dict([3]), "floor_id": r[4], "created": r[5], "updated": r[6]}
                list_room.append(obj)
            return list_room[0]

    def add_room(self,data):
        return self._add_new("rooms", "id,name,channels,icon,floor_id,created,updated", (str(uuid.uuid4()),data['name'],jsont.dumps(data['channels']),
                                                                                         data['icon'],data['floor_id'], int(time.time()), int(time.time())))

    def update_room(self,data):
        try:
            query = """update rooms set name='{}',channels='{}',icon='{}',
                       floor_id='{}',updated='{}' where id='{}';""".format(data['name'],jsont.dumps(data['channels']),
                                                                           data['icon'],data['floor_id'],data['id'])
            self.execute(query)
            self._db.commit()
            return self.get_room(id=data['id'])
        except Exception as e:
               LOGGER.error("Update room error : ",exc_info=True)
               return False
    def remove_room(self,id):
        if self._fetchone("rooms", "id", id):
           self._remove("rooms","id",id)
        else:
           return False
###### RULE ##########
    def check_rule_timer(self):
        list_actions = []
        for t in self.execute("select id,timer from conditions;").fetchall():
            condi = json.loads(t)
            print(condi)
            if currentDay in condi['repeat']:
               if condi['type']== 0 and condi['type']== 1: # 0 is moment , 1 is period
                  if condi['value']['start_time'] == currentTime:
                     rule = self.execute("select id,stauts,type from rules where id='{}';".format(condi['id'])).fetchone()
                     print("Rule",rule)
                     action = self.execute("select * from actions where id='{}'".format(condi['id'])).fetchone()
                     print("Action rule",action)
                     if action:
                         list_actions['channels'] = json.loads(action[2])
                         list_actions['notification'] = action[3]
                     action_channels = self._fetch_by_col("action_channels", "id",condi['id'])
                     if action_channels:
                        for c in action_channels:
                              list_actions['channels'] = {"id":c[1],"ieee":c[3],"type":c[4],"status":c[5]}
        return list_actions
    def compare_date_time(self,type,repeat,start_time,end_time):
        currentTime = datetime.now().strftime("%H:%M")
        currentDay  = datetime.today().weekday() + 2
        if currentDay in repeat and repeat is not None:
           if type:
               if currentTime == start_time:
                   return True
               else:
                   return False
           else:
               now = datetime.now()
               st_time = datetime.strptime(start_time, '%H:%M')
               st_time = now.replace(hour=st_time.hour,minute=st_time.minute)
               e_time = datetime.strptime(end_time, '%H:%M')
               e_time = now.replace(hour=e_time.hour,minute=e_time.minute)
               if st_time <= now <= e_time:
                  return True
               else:
                   return False

    def check_door_open(self):
        if self._door_reminder:
           for d in self._door_reminder['conditions']['alarm_mode']:
               print("check door timer",d)
               if d['channel_id'] in self._door_sensor:
                   door = self._door_sensor[d['channel_id']]
                   check_time = int(time.time())-int(door['updated'])  # cout time , 180 is 180 second
                   if check_time > 160:
                       timer = self._door_reminder['conditions']['timer']
                       print(timer)
                       if timer is not None:
                          if self.compare_date_time(1,timer['repeat'],timer['value']['start_time'],timer['value']['end_time']):
                             return self.notifi_rule_door_reminder(door['id'],door['name'],d['channel_id'])
                          else:
                               break
                       else:
                           return self.notifi_rule_door_reminder(door['id'],door['name'],d['channel_id'])

    def notifi_rule_door_reminder(self,rule_id,rule_name,channel):
        room_name = self._fetchone("rooms", "id",self._door_sensor[channel]['room_id'])
        notifi = self.add_notifi("", rule_id,4,5,rule_name,self._door_sensor[channel], room_name[1])
        return notifi
    def add_device_to_rule_secure(self, channel_id, type, ieee):
        zone_status = 1
        # Check type channel
        if type == 8 or type == 9 or type == 10 or type == 13 or type == 25:
            ''' Add device channel normal eg: motion,smoke,door sensor to alarm mode
                            "alarm_mode":[{
                                                            "channel_id":"{string}",
                                                                     "status":{}, // don't use
                                                            "ieee":{string}, // ieee device
                                                            "zone_status":{integer}
                                                                     }]
            '''
            if type == 9:
                zone_status = 0
            self._add_new("condition_alarm_mode", "id,channel_id,ieee,zone_status",
                          (self._alarm_on[0], channel_id, ieee, zone_status))
            self._add_new("condition_alarm_mode", "id,channel_id,ieee,zone_status",
                          (self._athome[0], channel_id, ieee, zone_status))
        elif type == 15:
            ''' Add remote control to alarm mode
                       "access_control":{
                                                                              "virtual":{integer},
                                                                            "bind_channel_ids":[{"channel_id":"{string}","channel_type":{integer}}]
                                                                            }
            '''
            self._add_new("conditions_bind_channel", "id,channel_id,channel_type",
                          (self._alarm_on[0], channel_id, type))
            self._add_new("conditions_bind_channel", "id,channel_id,channel_type",
                          (self._athome[0], channel_id, type))
            self._add_new("conditions_bind_channel",
                          "id,channel_id,channel_type", (self._sos[0], channel_id, type))
        elif type == 21:
            '''' Add siren to Alarm mode
                              "channels":[   { "channel_id":"{string}",
                             "channel_icon":"{string}",
                             "channel_type":{integer},
                            "channel_status":{ "type":"{string}","value":"{string}" }
                                                                             }]
            '''
            siren = [{"type": "volume", "value": 1},
                     {"type": "duration", "value": 180}]
            self._add_new("action_channels", "id,channel_id,channel_ieee,channel_type,channel_status",
                          (self._alarm_on[0], channel_id, ieee, type, json.dumps(siren)))
            self._add_new("action_channels", "id,channel_id,channel_ieee,channel_type,channel_status",
                          (self._athome[0], channel_id, ieee, type, json.dumps(siren)))
            self._add_new("action_channels", "id,channel_id,channel_ieee,channel_type,channel_status",
                          (self._sos[0], channel_id, ieee, type, json.dumps(siren)))
        else:
            pass

    def get_rule(self, all=False, id=False):
        try:
           list_rules = []
           if all:

               for r in self._fetchall("rules"):
                   list = {"id": r[0], "name": r[1], "status": r[2], "created": r[3], "updated": r[4],
                           "user_id": r[5], "homegate_id": r[6], "type": r[7], "favorite": bool(r[8])}
                   conditions = {}
                   for c in self._fetch_by_col("conditions", "id", r[0]):
                       alarm_mode = []
                       for a in self._fetch_by_col("condition_alarm_mode", "id", r[0]):
                           if a:
                               alarm_mode.append({"channel_id": a[1], "ieee": a[2], "zone_status": a[3]})
                       access_control = json.loads(c[3])

                       for b in self._fetch_by_col("conditions_bind_channel", "id", r[0]):
                           if access_control['bind_channel_ids'] is None:
                               access_control['bind_channel_ids'] = [{"channel_id": b[1], "channel_ieee": b[2], "channel_type": b[3], "channel_status": b[4]}]
                           else:
                               access_control['bind_channel_ids'].append({"channel_id": b[1], "channel_ieee": b[2], "channel_type": b[3], "channel_status": b[4]})
                       list["conditions"] = {"alarm_mode": alarm_mode, "auto_mode": self._to_dict(c[1]), "timer": self._to_dict(c[2]), "access_control": access_control}
                   for a in self._fetch_by_col("actions", "id", r[0]):
                       action_channels = []
                       for ac in self._fetch_by_col("action_channels", "id", r[0]):
                           if ac:
                               action_channels.append({"channel_id": ac[1], "channel_ieee": ac[3], "channel_icon": ac[2], "channel_type": ac[4], "channel_status": json.loads(ac[5])})
                       list["actions"] = {"delay": a[1], "channels": action_channels, "rules": self._to_dict(a[2]), "activate_notification": a[3]}

                   list_rules.append(list)
               return list_rules
           if id:
               for r in self.execute("select * from rules where id='{}';".format(id)).fetchall():
                   list = {"id": r[0], "name": r[1], "status": r[2], "created": r[3], "updated": r[4],
                           "user_id": r[5], "homegate_id": r[6], "type": r[7], "favorite": bool(r[8])}
                   conditions = {}
                   for c in self._fetch_by_col("conditions", "id", r[0]):
                       alarm_mode = []
                       for a in self._fetch_by_col("condition_alarm_mode", "id", r[0]):
                           if a:
                               alarm_mode.append({"channel_id": a[1], "ieee": a[2], "zone_status": a[3]})
                       access_control = json.loads(c[3])
                       for b in self._fetch_by_col("conditions_bind_channel", "id", r[0]):
                           if access_control['bind_channel_ids'] is None:
                               access_control['bind_channel_ids'] = [{"channel_id": b[1], "channel_ieee": b[2], "channel_type": b[3], "channel_status": b[4]}]
                           else:
                               access_control['bind_channel_ids'].append({"channel_id": b[1], "channel_ieee": b[2], "channel_type": b[3], "channel_status": b[4]})
                       list["conditions"] = {"alarm_mode": alarm_mode, "auto_mode": self._to_dict(c[1]), "timer": self._to_dict(c[2]), "access_control": access_control}
                   for a in self._fetch_by_col("actions", "id", r[0]):
                       action_channels = []
                       for ac in self._fetch_by_col("action_channels", "id", r[0]):
                           if ac:
                               action_channels.append({"channel_id": ac[1], "channel_ieee": ac[3], "channel_icon": ac[2], "channel_type": ac[4], "channel_status": json.loads(ac[5])})
                       list["actions"] = {"delay": a[1], "channels": action_channels, "rules": self._to_dict(a[2]), "activate_notification": a[3]}
                   list_rules.append(list)
               return list_rules[0]
        except Exception as e:
        	 LOGGER.debug('Get rule Error : %s',e)

    def get_rule_secure(self):
        list_rules = []
        query = "SELECT * from rules where type >0 and type <6;"
        rules = self.execute(query).fetchall()
        for r in rules:
            list = {"id": r[0], "name": r[1], "status": r[2], "created": r[3], "updated": r[4],
                    "user_id": r[5], "homegate_id": r[6], "type": r[7], "favorite": bool(r[8])}
            conditions = {}
            for c in self._fetch_by_col("conditions", "id", r[0]):
                alarm_mode = []
                for a in self._fetch_by_col("condition_alarm_mode", "id", r[0]):
                    if a:
                        alarm_mode.append(
                            {"channel_id": a[1], "ieee": a[2], "zone_status": a[3]})
                access_control = json.loads(c[3])

                for b in self._fetch_by_col("conditions_bind_channel", "id", r[0]):
                    if access_control['bind_channel_ids'] is None:
                        access_control['bind_channel_ids'] = [
                            {"channel_id": b[1], "channel_ieee": b[2], "channel_type": b[3], "channel_status": b[4]}]
                    else:
                        access_control['bind_channel_ids'].append(
                            {"channel_id": b[1], "channel_ieee": b[2], "channel_type": b[3], "channel_status": b[4]})
                list["conditions"] = {"alarm_mode": alarm_mode, "auto_mode": self._to_dict(c[1]), "timer": self._to_dict(c[2]), "access_control": access_control}
            for a in self._fetch_by_col("actions", "id", r[0]):
                action_channels = []
                for ac in self._fetch_by_col("action_channels", "id", r[0]):
                    if ac:
                        action_channels.append(
                            {"channel_id": ac[1], "channel_ieee": ac[3], "channel_icon": ac[2], "channel_type": ac[4], "channel_status": json.loads(ac[5])})
                list["actions"] = {"delay": a[1], "channels": action_channels, "rules": self._to_dict(a[2]), "activate_notification": a[3]}
            list_rules.append(list)
        return list_rules

    def remove_rule(self, id):
        self._remove("conditions", "id", id)
        self._remove("actions", "id", id)
        self._remove("rules", "id", id)

    def remove_channel_in_rule(self, channel_id):
        self._remove("conditions_bind_channel", "channel_id", channel_id)
        self._remove("condition_alarm_mode", "channel_id", channel_id)
        self._remove("action_channels", "channel_id", channel_id)

    def update_rule_status(self, status, id):
        if self._update_one("rules", "status", status, id):
            return {"id": id, "status": status}
        else:
            return None

    def update_rule_secure(self, status, channel_id):
        channel = self._fetchone("channels", "id", channel_id)
        type_rules = channel[4]
        id_alarm = self._fetchone("rules", "type", type_rules)[0]
        condi_alarm = self._fetchone("conditions", "id", id_alarm)
        list_channel = []
        if condi_alarm[1]:
            for c in json.loads(condi_alarm[1]):
                if c['zone_status'] == 0:
                    list_channel.append(
                        {"channel_id": c['channel_id'], "zone_status": c['zone_status']})
        if list_channel:
            self._update_one_col("rules", "status", status, id)
            return None
        else:
            return list_channel

    def update_rule_alarm(self, type, status):
        ''' Update rule alarm mode
                        AlarmOn get list channel have zone_status in alarm_mode entity of condition table
                        type: 1 :AlarmOn , 2: AlarmOff , 3:  athome , 4 sos , 5 DoorReminder
        '''
        if type == 2 and status == 1:
            query1 = "UPDATE rules SET status=0 WHERE type=1 OR type=3;"
            self.execute(query1)
            query3 = "UPDATE rules SET status=1 WHERE type=2;"
            self.execute(query3)
            self._db.commit()
            return self._alarm_off
        elif type == 1 and status == 1:
            query1 = "UPDATE rules SET status=0 WHERE type=2 OR type=3;"
            self.execute(query1)
            query2 = "UPDATE rules SET status=1 WHERE type=1;"
            self.execute(query2)
            self._db.commit()
            return self.change_zone_status(type)
        elif type == 3 and status == 1:
            query1 = "UPDATE rules SET status=0 WHERE type=1 OR type=2;"
            self.execute(query1)
            query2 = "UPDATE rules SET status=1 WHERE type=3;"
            self.execute(query2)
            self._db.commit()
            return self.change_zone_status(type)
        elif type == 4 and status == 1:
            id_sos = self.execute(
                "SELECT id FROM rules WHERE type='{}';".format(4)).fetchone()[0]
            action_alarm = self.execute(
                "SELECT channels FROM action WHERE id='{}';".format(id_sos)).fetchone()[0]
            list_channel = []
            if action_alarm:
                for c in json.loads(action_alarm):
                    list_channel.append(
                        {"ieee": c['ieee'], "status": c['channel_status'], "type": c['channel_type']})
                return list_channel
        else:
            pass

    def change_zone_status(self, type):
        ''' Change zone status in alarm mode
        '''
        self._db.row_factory = lambda c, r: dict(
            [(column[0], r[idx]) for idx, column in enumerate(c.description)])
        condi_alarm = self.execute(
            "SELECT ieee,zone_status FROM condition_alarm_mode WHERE id='{}';".format(self._athome[0])).fetchall()
        list_channel = []
        if condi_alarm:
            for c in condi_alarm:
                if type == 1 and c['zone_status'] == 0:
                    list_channel.append({"ieee": c['ieee'], "zone_status": 1})
                else:
                    list_channel.append(
                        {"ieee": c['ieee'], "zone_status": c['zone_status']})
        if type == 1:
            return {"id": self._alarm_on[0], "channels": list_channel}
        else:
            return {"id": self._athome[0], "channels": list_channel}

    def get_rule_alarm_status(self):
        status = self.execute("SELECT status from rules where type<3;").fetchall()
        if status[0][0] == 1 or status[2][0] == 1:
           return 1
        else:
           return 0
    def get_rule_alarm(self, type):
        return self.execute("SELECT id,type,status FROM rules WHERE type='{}';".format(type)).fetchone()
    ###### DEVICE ##########

    def get_device(self, all=None, id=None):
        self._db.row_factory = lambda c, r: dict(
            [(column[0], r[idx]) for idx, column in enumerate(c.description)])
        try:
            if all is not None:
                query_all = """SELECT id, ieee, addr, type, model, manufacturer, serial_number, sw_version, hw_version,
							   lqi,low_battery, created, updated from devices;"""
                return self.execute(query_all)
            elif id is not None:
                query_id = """SELECT id, ieee, addr, type, model, manufacturer, serial_number, sw_version, hw_version, zone_id, zone_status,
								lqi,low_battery, created, updated from devices where id=? ;"""
                return self.execute(query_all, id)
            else:
                return "No param selected"
        except Exception as e:
               LOGGER.error(" Get Device error :", exc_info=True)

    def get_device_channel(self, all=False, id=False):
        try:
            devices = []
            if all:
                query_all = """SELECT id, ieee, addr, type, model, manufacturer, serial_number, sw_version, hw_version,
							   lqi,low_battery, created, updated , name from devices;"""
                for d in self.execute(query_all).fetchall():
                    device = {"id": d[0], "ieee": d[1], "addr": d[2], "type": d[3], "model": d[4], "manufacturer": d[5], "serial_number": d[6], "sw_version": d[7], "hw_version": d[8],
                              "signal": round(100 * int(d[9]) / 255), "low_battery": d[10], "created": d[11], "updated": d[12], "name": d[13]}
                    channels = []
                    query_channel = "SELECT id, name, endpoint_id, type, status, config ,zone_id, zone_status, created, updated, favorite,notification,room_id, device_id from channels where device_id='{}';".format(
                        d[0])
                    for c in self.execute(query_channel).fetchall():
                        channel = {"id": c[0], "name": c[1], "endpoint": c[2], "type": c[3], "status": json.loads(c[4]), "config": c[5], "zone_id": c[6], "zone_status": c[7],
                                   "created": c[8], "updated": c[9], "favorite": bool(c[10]), "notification": c[11], "room_id": c[12], "device_id": c[13]}
                        channels.append(channel)
                    device['channels'] = channels
                    devices.append(device)
                return devices
            if id:
                query_device = """SELECT id, ieee, addr, type, model, manufacturer, serial_number, sw_version, hw_version,
								 lqi, low_battery, created, updated, name from devices where id='{}';""".format(id)
                d = self.execute(query_device).fetchone()
                device = {"id": d[0], "ieee": d[1], "addr": d[2], "type": d[3], "model": d[4], "manufacturer": d[5], "serial_number": d[6], "sw_version": d[7],
                          "hw_version": d[8], "signal": round(100 * int(d[9]) / 255), "low_battery": d[10], "created": d[11], "updated": d[12], "name": d[13]}

                channels = []
                query_channel = "SELECT id, name, endpoint_id, type, status, config, zone_id, zone_status, created, updated, favorite,notification,room_id, device_id from channels where device_id='{}';".format(
                    id)
                for c in self.execute(query_channel).fetchall():
                    channel = {"id": c[0], "name": c[1], "endpoint": c[2], "type": c[3], "status": json.loads(c[4]), "config": c[5], "zone_id": c[6], "zone_status": c[7],
                               "created": c[8], "updated": c[9], "favorite": bool(c[10]), "notification": c[11], "room_id": c[12], "device_id": c[13]}
                    channels.append(channel)
                device['channels'] = channels
                return device
        except Exception as e:
               LOGGER.error("Get all device error :",exc_info=True)
               return None

    def update_device(self, name, value, id):
        pass
        device = self._update_one("devices", name, value, id)
        if device:
            return True
        else:
            return device

    def set_device_type(self, model, device_id):
        try:
            name = LIST_TYPE_CHANNEL_BRAND[model]
            query_update_device = "UPDATE devices SET name=?, type=?, model=?, manufacturer=?, sw_version=?, hw_version=?,serial_number=? WHERE id=?;"
            self.execute(query_update_device, (
                NAME_TYPE_CHANNEL[name], 1, LIST_MODEL_DEVICE_BRAND[model], "DICOM", "1.0", "1.0", "", device_id))
        except Exception as e:
             LOGGER.error("Set device type error : ",exc_info=True)

    def generate_zone_id(self):
        query = "SELECT zone_id from channels;"
        list_zone_id = self.execute(query).fetchall()
        i = 0
        if list_zone_id:
            for z in list_zone_id:
                i += 1
                if i != z[0]:
                    return i
                    break
                elif i == int(max(list_zone_id)[0]):
                    return i+1
                    break
        else:
            return 1

    def remove_device(self, id):
        device = self._fetchone("devices", "id", id)
        if device:
            channel = self._fetchone("channels", "device_id", id)
            if device and channel:
                self._remove("attributes", "ieee", device[3])
                self._remove("clusters", "ieee", device[3])
                self._remove("group_members", "channel_id", channel[0])
                self._remove("user_access", "channel_id", channel[0])
                self._remove("channels", "device_id", id)
                self._remove("devices", "id", id)
            return device[3]
        else:
            return False

    def remove_channel(self, id):
        channel = self._fetchone("channels", "id", id)
        if channel:
            self._remove_muti("attributes", "ieee",
                              "endpoint_id", channel[2], channel[3])
            self._remove_muti("clusters", "ieee",
                              "endpoint_id", channel[2], channel[3])
            self._remove("group_members", "channel_id", channel[0])
            self._remove("user_access", "channel_id", channel[0])
            self.remove_channel_in_rule(channel[0])
            number_enpoint = self.execute(
                "select count(id) from channels where device_id='{}';".format(channel[18])).fetchone()
            if number_enpoint[0] == 1:
                self._remove("channels", "id", channel[0])
                self._remove("devices", "id", channel[18])
                return channel[2]
            else:
                return True
        else:
            return False

    ####### CHANNEL ##########

    def get_channel(self, all=False, id=False):
        self._db.row_factory = lambda c, r: dict([(column[0], r[idx]) for idx, column in enumerate(c.description)])
        try:
            if all:
               query_all = """SELECT id, name, enpoint_id, type, status,config ,zone_id,zone_status, created, updated, favorite, device_id from channels;"""
               return self.execute(query_all)
            if id:
               query_all = """SELECT id, name, enpoint_id, type, status , config, zone_id, zone_status created, updated, favorite, device_id from channels where id=?;"""
               return self.execute(query_all, id)
        except Exception as e:
              LOGGER.error("Get channel error : %s", e)

    def get_channel_by_ieee(self, ieee, endpoint_id):
        return self.execute("SELECT id,type,status,name,notification,room_id,zone_status FROM channels where ieee='{}' and endpoint_id='{}';".format(ieee, endpoint_id)).fetchone()

    def update_channel_mqtt(self, channel_id, status):
        try:
            query_update_channel = "UPDATE channels SET status='{}',updated='{}' WHERE id='{}';".format(
                json.dumps(status_old), timer, channel_id)
            self.execute(query_update_channel)
            self._db.commit()
        except Exception as e:
               LOGGER.error("UPDATE channel mqtt % ",e)
               return False

    def update_channel_info(self,channel_id,data):
        channel = self._fetchone("channels", "id", channel_id)
        if channel:
           try:
               self.execute("""update channels set name='{}',status='{}',zone_status='{}',favorite='{}',notification='{}',
                            room_id='{}' where id='{}';""".format(data['name'],json.dumps(data['status']),data['zone_status'],int(data['favorite']),
                                                                 data['notification'],data['room_id'],channel_id))
               self._db.commit()
               return
           except Exception as e:
                  LOGGER.error("UPDATE channel info : %s", e)
                  return False
    def update_channel_alarm(self, channel, status):
        ''' Update channel
                        Check type channel and notification
                        Check Enviroment sensor type 28 : combine temperature and humidity to status
        '''
        rule_state = self.get_rule_alarm_status()
        try:
            data = {}
            channel_status = self.generate_channel_value(channel[1], status)
            timer = int(time.time())
            query_update_channel = "UPDATE channels SET status='{}',updated='{}' WHERE id='{}';".format(json.dumps(channel_status), timer, channel[0])
            self.execute(query_update_channel)
            self._db.commit()
            data["notifi"] = False
            if rule_state == 1 and channel[6] == 1:
                room_name = self._fetchone("rooms", "id", channel[5])
                # self,user_id,id,type_noti,type,name,status,room_name
                notifi = self.add_notifi("", channel[0], 1, channel[1], channel[3], channel_status, room_name[1])
                data["notifi"] = notifi
                LOGGER.debug("Notifi rule alarm")
            elif channel[4] == 1:
                room_name = self._fetchone("rooms", "id", channel[5])
                # self,user_id,id,type_noti,type,name,status,room_name
                notifi = self.add_notifi("", channel[0], 0, channel[1], channel[3], channel_status, room_name[1])
                data["notifi"] = notifi
            else:
                pass

            data["channel"] = {"id": channel[0],'status': channel_status, 'updated': timer}
            #door_reminder add sensor
            if channel[1] == 8:
                if channel_status[0]['value'] == 1:
                   self._door_sensor[str(channel[0])]={'id':channel[0],'name':channel[3],'status': channel_status[0]['value'], 'updated': timer,'room_id':channel[5]}
                else:
                    del self._door_sensor[str(channel[0])]
                print("Door sensor ",self._door_sensor)
            return data
        except Exception as e:
            LOGGER.error("Update channel alarm status: %s", e)

    def update_channel_normal(self, ieee, endpoint_id, status):
        try:
           channel = self._fetch_multi(
               "channels", "ieee", "endpoint_id", ieee, endpoint_id)
           for c in channel:
               channel_status = self.generate_channel_value(c[4], status)
               status_old = json.loads(c[5])
               if c[4] == 28:
                   if not status_old:
                       status_old = [{"type": "temperature", "value": int(status.get('temperature', 25))}, {"type": "humidity", "value": int(status.get('humidity', 50))}]
                   elif status.get('name', None) == 'temperature':
                       status_old[0]['value'] = int(status.get('value', 25))
                   else:
                       status_old[1]['value'] = int(status.get('value', 25))
                   channel_status = status_old
               timer = int(time.time())
               query_update_channel = "UPDATE channels SET status='{}',updated='{}' WHERE id='{}';".format(
                   json.dumps(channel_status), timer, c[0])
               self.execute(query_update_channel)
               self._db.commit()
               return {"id": c[0], 'status': channel_status, 'updated': timer}
        except Exception as e:
               LOGGER.error("Update channel error: %s", e)

    def generate_channel_value(self, channel_type, status):
        list_status = []
        if channel_type == 21:
            list_status.append({"type": "volume", "value": "1"})
            list_status.append({"type": "duration", "value": 180})
            list_status.append({"type": "tamper", "value": int(status.get('tamper', 0))})
        elif channel_type == 13 or channel_type == 0:
            list_status.append(
                {"type": "onoff", "value": int(status.get('alarm1', 0))})
        elif channel_type == 8:
            list_status.append(
                {"type": "closeopen", "value": int(status.get('alarm1', 0))})
        elif channel_type == 9:
            list_status.append(
                {"type": "present", "value": int(status.get('alarm1', 0))})
        elif channel_type == 10:
            list_status.append(
                {"type": "smoke", "value": int(status.get('alarm1', 0))})
        elif channel_type == 15:
            list_status.append(
                {"type": "sos", "value": int(status.get('alarm1', 0))})
            list_status.append(
                {"type": "athome", "value": int(status.get('athome', 0))})
            list_status.append(
                {"type": "armed", "value": int(status.get('armed', 0))})
            list_status.append(
                {"type": "disarmed", "value": int(status.get('disarmed', 0))})
        elif channel_type == 28:
            if status.get('temperature', True) and status.get('humidity', True):
                if status.get('name', None) == 'temperature':
                    list_status.append(
                        {"type": "temperature", "value": int(status.get('value', 25))})
                if status.get('name', None) == 'humidity':
                    list_status.append(
                        {"type": "humidity", "value": int(status.get('value', 50))})
            else:
                list_status.append(
                    {"type": "temperature", "value": status.get('temperature', 25)})
                list_status.append(
                    {"type": "humidity", "value": status.get('humidity', 50)})
        elif channel_type == 25:
            list_status.append(
                {"type": "present", "value": int(status.get('alarm1', 1))})
            list_status.append(
                {"type": "tamper", "value": int(status.get('tamper', 0))})
        else:
            pass
        return list_status

    def set_status_channel(self, status, channel_id, type):
        '''
        Table type status value
          21: Indoor Siren
                                        "0x<volume/duration>"
                                        "volume": 1-4
                                        "duration" : seconds
                                        siren = {"0x210":"Volume is medium and duration alarm 60s"}
           8: Door Sensor
           13: Waterleak
           25: Pir pet
           9 : Pir sensor
           28: Enviroment Sensor -> Temperature andf Humidity
           10: Smoke sensor
           15: Alarm Remote control
           16: S0S button
        '''
        notifi = 0
        if type == 10:
            notifi = 1
        try:
            list_status = self.generate_channel_value(type, status)
            query_update_channel = "UPDATE channels SET status='{}',notification='{}' WHERE id='{}';".format(
                json.dumps(list_status), notifi, channel_id)
            self.execute(query_update_channel)
            self._db.commit()
        except Exception as e:
               LOGGER.error("UPDATE status channel error: %s",e)

    def set_type_channels(self, model, channel_id):
        """"
        Set model , type devices
        """
        try:
            room_id = self.get_default_room()

            query_update_channel = "UPDATE channels SET name=?,type=?,room_id=? WHERE id=?;"
            name = LIST_TYPE_CHANNEL_BRAND[model]
            self.execute(query_update_channel,
                         (NAME_TYPE_CHANNEL[name], LIST_TYPE_CHANNEL_BRAND[model], room_id, channel_id))
            return LIST_TYPE_CHANNEL_BRAND[model]
        except Exception as e:
               LOGGER.error("UPDATE status channel error: %s",e)

    ######  GROUPS ##########

    def get_group(self, all=None, id=None):
        try:
            if all is not None:
                groups = {}
                for group in self._fetchall("groups"):
                    groups["id"] = group[0]
                    groups["group_idx"] = group[1]
                    groups["name"] = group[2]
                    group["type"] = group[3]
                    group_member = []
                    for member in self._fetchone("group_members", 'group_id', group[0]):
                        channels = {}
                        channels["channel_id"] = member[1]
                        channels["status"] = member[2]
                        group_member.append(channels)
                    groups["group_members"] = group_member
                return groups

            elif id is not None:
                groups = {}
                for group in self._fetchone("groups", 'id', id):
                    groups["id"] = group[0]
                    groups["group_idx"] = group[1]
                    groups["name"] = group[2]
                    group["type"] = group[3]
                    group_member = []
                    for member in self._fetch_by_col("group_members", 'group_id', group[0]):
                        channels = {}
                        channels["channel_id"] = member[1]
                        channels["status"] = member[2]
                        group_member.append(channels)
                    groups["group_members"] = group_member
                return groups
            else:
                return "No select param"
        except Exception as e:
              LOGGER.debug('Error get group %s', e)

    def update_group(self, data):
        pass

    def group_member_removed(self, group, ep):
        q = """DELETE FROM group_members WHERE group_id=?AND addr=?AND endpoint_id=?"""
        self.execute(q, (group.group_id, *ep.unique_id))
        self._db.commit()

    ####### NOTIFICATION ##########
    def get_all_notifi(self):
        list = []
        for n in self._fetchall("notification"):
            list.append({"id": n[0], "user_id": n[1], "type": n[2],
                                     "title": n[3], "body": n[4], "created": n[5]})
        return list

    def delete_notifi(self, id):
        self._remove("notification", id)

    def clear_notifi(self):
        query = "DELETE from notification where id not in ( SELECT id FROM notification ORDER BY created DESC LIMIT 200);"
        self.execute(query)

    def add_notifi(self, user_id, id, type_noti, type, name, status, room_name):
        ''' Create notification format
                        Type 0 : Notify channel
                        Type 1 : Notify alarm
                        Type 3 : Notify rule alarm
                        Type 5 : Notify door reminder
                        Type 5 : Notify rule normal


        '''
        data = {}
        if type_noti == 0 or type_noti == 1:
            data = {"channel_id": id, "type": type,
                    "status": status, "room_name": room_name}
        elif type_noti == 2:
            data = {"rule_id": id, "type": type,
                    "status": status, "room_name": room_name}
        elif type_noti == 3:
            pass
        elif type_noti == 4:
              data = {"rule_id": id, "type": type,"channel":status,"room_name": room_name}
        else:
            pass
        id = str(uuid.uuid4())
        timer = int(time.time())
        noti_id = self._add_new("notification", "id,user_id,type,title,body,created", (
            id, user_id, type_noti, name, json.dumps(data), timer))
        if noti_id:
            noti = {"id": id, "user_id": user_id, "type": type_noti,
                    "title": name, "body": data, "created": timer}
            return noti
    def add_door_bell_noti(self):
        d = str(uuid.uuid4())
        timer = int(time.time())
        noti_id = self._add_new("notification", "id,user_id,type,title,body,created", (id, " ",4,"Chuông cửa", "Chuông cửa đang gọi", timer))
        if noti_id:
            noti = {"id": id, "user_id": "", "type": 4,"title": "Chuông cửa", "body": "Chuông cửa đang gọi", "created": timer}
            return noti
    ##### Camera #####

    def get_camera(self, id=False, all=False):
        if id:
            c = self._fetchone("cameras", "id", id)
            if c:
                return {"id": c[0], "name": c[1], "roomId": c[2], "cameraIp": json.load(c[3]), "cameraInfo": json.load(c[4]), "streamUri": json.load(c[5]),"snapshotUri": json.load(c[6]), "created": c[7], "updated": c[8]}
        if all:
            camera = self._fetchall("cameras")
            if camera:
                data = []
                for c in camera:
                    data.append({"id": c[0], "name": c[1], "roomId": c[2], "cameraIp": json.load(c[3]), "cameraInfo": json.load(c[4]), "streamUri": json.load(c[5]),"snapshotUri": json.load(c[6]), "created": c[7], "updated": c[8]})
                return data

    def update_camera(self, id, data):
        try:
            query = """UPDATE cameras SET name='{}',roomId='{}',cameraIp='{}',cameraInfo='{}',
                       streamUri='{}',snapshotUri='{}',update='{}' WHERE id='{}';""".format(name, room_id, camera_ip, camera_info, camera_uri)
            self.execute(query)
            self._db.commit()
            return self.get_camera(id=data['id'])
        except Exception as e:
               LOGGER.debug('UPDATE camera error : %s',e)
               return False
    def remove_camera(self, id):
        if self._fetchone("cameras", "id", id)[0]:
            self._remove("cameras","id",id)
        else:
            return False


# if __name__ == '__main__':
#     d = DbInterface()
#     # print(json.dumps(d._fetchone("rules", "id",'5a2d8b58-5bfb-4998-b6da-8ff4ecf0cebe')))
#     print(d.get_rule(id='5a2d8b58-5bfb-4998-b6da-8ff4ecf0cebe'))
    # print(d.remove_channel("0d3fe41c-229f-4797-8bcf-54f657c7af34"))
# #     d.remove_device("3edae810-5b68-421a-8ef3-ff69d80926e0")
#     print(d._init_homegate("e731f132-b313-420e-b6c2-2257854f5149","CPIQGFvD13bS]ur2dGmT@5AI)","dicomiot","Dhome","DHG-A1","23:24:234","25:24:234","DH-A1-A05B2000011","1.0","1.2"))
