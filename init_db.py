#!/usr/bin/env python3
# Databse Init
#
# Copyright (c) 2020 Ivan , Dicom R&D
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
import time
import sqlite3
from datetime import datetime
from config import DATABASE
import json
import uuid
DB_VERSION = 0x0001
import argparse
class Init_database(object):
      def __init__(self):
          '''Initializes the sqlite database using a schema '''
          self._db = sqlite3.connect(DATABASE,check_same_thread=False)
          self._enable_foreign_keys()
          self._create_table_devices()
          self._create_table_channels()
          self._create_table_clusters()
          self._create_table_attributes()
          self._create_table_groups()
          self._create_table_group_members()
          self._create_table_rooms()
          self._create_table_floors()
          self._create_table_homegate()
          self._create_table_users()
          self._create_table_user_access()
          self._create_table_neighbours()
          self._create_table_rules()
          self._create_table_conditions()
          self._create_table_condition_alarm_mode()
          self._create_table_conditions_bind_channel()
          self._create_table_actions()
          self._create_table_action_channels()
          self._create_table_notification()
          self._create_table_camera()
          self._create_table_rule_execute()
      def execute(self, *args, **kwargs):
          return self._db.cursor().execute(*args, **kwargs)
      def executemany(self, *args, **kwargs):
          return self._db.cursor().executemany(*args, **kwargs)
      def _create_table(self, table_name, spec):
          print("CREATE TABLE IF NOT EXISTS %s %s" % (table_name, spec))
          self.execute("CREATE TABLE IF NOT EXISTS %s %s" % (table_name, spec))
          self.execute("PRAGMA user_version = %s" % (DB_VERSION,))
      def _create_index(self, index_name, table, columnumns):
          self.execute(
              "CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s(%s)"
              % (index_name, table, columnumns)
          )
      def _enable_foreign_keys(self):
          self.execute("PRAGMA foreign_keys = ON")
      def _create_table_users(self):
          self._create_table(
              "users",
              """(
                    "id" varchar primary key ,
                    "name" varchar,
                    "password" varchar,
                    "email" varchar,
                    "status" integer,
                    "permission_type" integer not null ,
                    "access_token" varchar,
                    "last_seen" varchar,
                    "created" varchar,
                    "updated" varchar
              );"""
          )
          self._create_index("users_idx", "users", "id")
      def _create_table_user_access(self):
          self._create_table(
              "user_access",
              """(
                    "user_id" varchar,
                    "channel_id" varchar,
                    "created" varchar,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("user_access_idx", "user_access", "user_id,channel_id")
      def _create_table_homegate(self):
          self._create_table(
               "homegate",
               """(
                    "id" varchar ,
                    "site" varchar not null,
                    "name" varchar not null,
                    "token" varchar not null,
                    "wan_mac" varchar not null,
                    "wwan_mac" varchar not null,
                    "ip_local" varchar,
                    "ip_public" varchar,
                    "model" varchar not null,
                    "serial" varchar not null,
                    "state" integer,
                    "config"  TEXT,
                    "zig_version" varchar,
                    "hw_version"  varchar,
                    "sw_version"  varchar,
                    "created" varchar,
                    "updated" varchar ,
                    "last_update" varchar ,
                    "last_seen" varchar
                );"""
           )
          self._create_index("homegate_idx", "homegate", "id")
      def _create_table_rooms(self):
         self._create_table(
             "rooms",
             """(
              "id" varchar,
              "name" varchar,
              "icon" varchar,
              "channels" TEXT,
              "floor_id" varchar,
              "created" varchar,
              "updated" varchar
             );"""
         )
         self._create_index("room_idx", "rooms", "id")
      def _create_table_floors(self):
         self._create_table(
               "floors",
               """(
                "id" varchar,
                "name" varchar
               );"""
           )
         self._create_index("floor_idx", "floors", "id")
      def _create_table_devices(self):
          self._create_table(
              "devices",
              """(
                  "id" varchar primary key,
                  "name" varchar,
                  "addr" varchar,
                  "ieee" varchar not null,
                  "discovery" varchar,
                  "type" integer,
                  "model" varchar,
                  "manufacturer" vachar,
                  "serial_number" varchar,
                  "sw_version" varchar,
                  "hw_version" varchar,
                  "generictype" varchar,
                  "ids" integer,
                  "bit_field" varchar,
                  "descriptor_capability" varchar,
                  "lqi" integer,
                  "mac_capability" varchar,
                  "manufacturer_code" varchar,
                  "power_type"  integer,
                  "low_battery" integer default 0,
                  "server_mask" integer,
                  "rejoin_status" integer,
                  "created" varchar,
                  "updated" varchar,
                  "last_seen" varchar
              );"""
          )
          self._create_index("device_idx", "devices", "id")
      def _create_table_channels(self):
          self._create_table(
              "channels",
              """(
                  "id" varchar,
                  "name" varchar,
                  "ieee" varchar,
                  "endpoint_id" integer not null,
                  "type" integer,
                  "status" text,
                  "config" text,
                  "profile_id" integer,
                  "device_type" integer,
                  "in_clusters" text,
                  "out_clusters" text,
                  "zone_id" integer,
                  "zone_status" integer,
                  "created" varchar ,
                  "updated" varchar ,
                  "favorite" integer,
                  "notification" integer,
                  "room_id" varchar,
                  "device_id" varchar,
                  FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("channels_idx", "channels", "ieee, endpoint_id")
      def _create_table_clusters(self):
          self._create_table(
              "clusters",
              """(
                  "ieee" varchar ,
                  "endpoint_id" integer not null,
                  "cluster" integer,
                  FOREIGN KEY(ieee,endpoint_id) REFERENCES channels(ieee,endpoint_id) ON DELETE CASCADE
              );"""
          )
          self._create_index("cluster_idx", "clusters", "ieee, endpoint_id, cluster")
      def _create_table_attributes(self):
          self._create_table(
              "attributes",
              """(
                  "ieee" varchar,
                  "endpoint_id" integer not null,
                  "cluster" integer,
                  "attribute" integer,
                  "expire" integer,
                  "zone_status" text,
                  "data" varchar,
                  "name" varchar,
                  "type" varchar,
                  "value" varchar,
                  FOREIGN KEY(ieee,endpoint_id) REFERENCES channels(ieee,endpoint_id) ON DELETE CASCADE
              );"""
          )
          self._create_index("attribute_idx", "attributes", "ieee, endpoint_id, cluster, attribute")
      def _create_table_groups(self):
          self._create_table(
               "groups",
               """(
                  "id" varchar  primary key,
                  "group_idx" integer,
                  "name" varchar,
                  "channel_type" integer,
                  "created" varchar,
                  "updated" varchar
               );"""
          )
          self._create_index("group_idx", "groups", "group_idx")
      def _create_table_group_members(self):
          self._create_table(
              "group_members",
              """(
                  "group_id" varchar,
                  "channel_id" varchar,
                  FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
                  FOREIGN KEY(channel_id) REFERENCES channels(id) ON DELETE CASCADE);"""
          )
          self._create_index(
              "group_members_idxs", "group_members", "group_id, channel_id"
          )
      def _create_table_neighbours(self):
          self._create_table(
               "neighbours",
               """(
                 "addr" varchar,
                 "lqi" integer
               );"""
          )
      def _create_table_rules(self):
          self._create_table(
              "rules",
              """(
                  "id" varchar primary key,
                  "name" varchar,
                  "status" integer,
                  "created" varchar ,
                  "updated" varchar ,
                  "user_id" varchar,
                  "homegate_id" varchar,
                  "type" integer,
                  "favorite" integer,
                  FOREIGN KEY(homegate_id) REFERENCES homegate(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("rule_idx", "rules", "id ,homegate_id")
      def _create_table_conditions(self):
          self._create_table(
              "conditions",
              """(
                 "id" varchar,
                 "auto_mode" text,
                 "timer" text,
                 "access_control" text,
                 FOREIGN KEY(id) REFERENCES rules(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("condition_idx", "conditions", "id")
      def _create_table_condition_alarm_mode(self):
          self._create_table(
              "condition_alarm_mode",
              """(
                 "id" varchar,
                 "channel_id" varchar,
                 "ieee" varchar,
                 "zone_status" integer,
                 FOREIGN KEY(id) REFERENCES rules(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("condition_alarm_mode_idx", "condition_alarm_mode", "id")
      def _create_table_conditions_bind_channel(self):
          self._create_table(
              "conditions_bind_channel",
              """(
                 "id" varchar,
                 "channel_id" varchar,
                 "channel_ieee" varchar,
                 "channel_type" integer,
                 "channel_status" varchar,
                 FOREIGN KEY(id) REFERENCES rules(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("conditions_bind_channel_idx", "conditions_bind_channel", "id")
      def _create_table_actions(self):
          self._create_table(
              "actions",
              """(
                 "id" varchar,
                 "delay" integer,
                 "rules" text,
                 "active_notification" integer,
                 FOREIGN KEY(id) REFERENCES rules(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("actions_idx", "actions", "id")
      def _create_table_action_channels(self):
          self._create_table(
              "action_channels",
              """(
                 "id" varchar,
                 "channel_id" varchar,
                 "channel_icon" varchar,
                 "channel_ieee" varchar,
                 "channel_type" integer,
                 "channel_status" varchar,
                 FOREIGN KEY(id) REFERENCES rule(id) ON DELETE CASCADE
              );"""
          )
          self._create_index("action_channelsx", "action_channels", "id")
      def _create_table_notification(self):
          self._create_table(
              "notification",
              """(
                 "id" varchar,
                 "user_id" varchar,
                 "type" integer,
                 "title" varchar,
                 "body" TEXT,
                 "created" varchar
              );"""
          )
          self._create_index("actions_idx", "notification", "id,user_id")
      def _create_table_camera(self):
          self._create_table(
              "cameras",
              """(
                 "id" varchar,
                 "name" varchar,
                 "roomId" varchar,
                 "cameraIp" TEXT,
                 "cameraInfo" TEXT,
                 "streamUri" TEXT,
                 "snapshotUri" TEXT,
                 "created" varchar,
                 "updated" varchar
              );""")
          self._create_index("cameras_idx", "cameras", "id")
      def _create_table_rule_execute(self):
          self._create_table(
              "rule_execute",
              """(
                 "rule_id" varchar,
                 "type" varchar,
                 "updated" varchar
              );""")
      def _init_homegate(self,ids,token,site,name,model,wan_mac,wwan_mac,serial,sw,jn):
          id =[]
          id.append(ids) # Homegate id
          id.append(str(uuid.uuid4())) # Alarm Mode id
          id.append(str(uuid.uuid4()))  # Dis alarm
          id.append(str(uuid.uuid4())) # Arrive Home id
          id.append(str(uuid.uuid4())) # Sos id
          id.append(str(uuid.uuid4())) # Door Reminder id
          id.append(str(uuid.uuid4())) # Arrive home
          id.append(str(uuid.uuid4())) # Sleep
          id.append(str(uuid.uuid4())) # Leave
          query = """INSERT OR IGNORE INTO homegate (id,site,name,token,ip_local,ip_public,model,serial,wan_mac,wwan_mac,zig_version,sw_version,
                                                      hw_version,state,config,created,updated,last_update,last_seen) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);"""

          self.execute(query,(id[0],site,name,token,"192.168.10.1","0.0.0.0",model,serial,wan_mac,
                              wwan_mac,jn,sw,"1.0",1,None,int(time.time()),int(time.time()),int(time.time()),int(time.time())))

          query_rule = "INSERT INTO rules (id,name,status,created,updated,user_id,homegate_id,type,favorite) VALUES (?,?,?,?,?,?,?,?,?);"
          query_rule_condition = "INSERT OR IGNORE INTO conditions (id ,auto_mode,timer,access_control) VALUES (?,?,?,?);"
          query_rule_action = "INSERT OR IGNORE INTO actions (id ,delay,rules,active_notification) VALUES (?,?,?,?);"

          list_rules = [(id[1],"Bật báo động",0,int(time.time()),int(time.time()),"",id[0],1,True),
                        (id[2],"Tắt báo động",0,int(time.time()),int(time.time()),"",id[0],2,True),
                        (id[3],"Báo động ở nhà",0,int(time.time()),int(time.time()),"",id[0],3,True),
                        (id[4],"Khẩn cấp",0,int(time.time()),int(time.time()),"",id[0],4,True),
                        (id[5],"Nhắc cửa mở",0,int(time.time()),int(time.time()),"",id[0],5,False),
                        (id[6],"Về nhà",0,int(time.time()),int(time.time()),"",id[0],0,False),
                        (id[7],"Ra ngoài",0,int(time.time()),int(time.time()),"",id[0],0,False),
                        (id[8],"Đi ngủ",0,int(time.time()),int(time.time()),"",id[0],0,False)]
          self.executemany(query_rule,list_rules)
          access_control = json.dumps({"virtual":1,"bind_channel_ids":None})
          list_conditions = [(id[1],None,None,access_control),
                              (id[2],None,None,access_control),
                              (id[3],None,None,access_control),
                              (id[4],None,None,access_control),
                              (id[5],None,None,access_control),
                              (id[6],None,None,access_control),
                              (id[7],None,None,access_control),
                              (id[8],None,None,access_control)]
          self.executemany(query_rule_condition,list_conditions)
          list_actions = [(id[1],0,None,1),
                          (id[2],0,None,1),
                          (id[3],0,None,1),
                          (id[4],0,None,1),
                          (id[5],0,None,1),
                          (id[6],0,None,1),
                          (id[7],0,None,1),
                          (id[8],0,None,1)]
          self.executemany(query_rule_action,list_actions)
          query_room = "INSERT OR IGNORE INTO rooms (id , name , icon ,created ,updated) VALUES (? ,? ,? ,? ,?)"
          self.execute(query_room,(str(uuid.uuid4()),"Mặc định","",int(time.time()),int(time.time())))
          self.execute(query_room,(str(uuid.uuid4()),"Phòng khách","",int(time.time()),int(time.time())))
          self.execute(query_room,(str(uuid.uuid4()),"Phòng ngủ","",int(time.time()),int(time.time())))
          self.execute(query_room,(str(uuid.uuid4()),"Phòng bếp","",int(time.time()),int(time.time())))
          self.execute(query_room,(str(uuid.uuid4()),"Sân vườn","",int(time.time()),int(time.time())))
          self._db.commit()
if __name__ == '__main__':
    d = Init_database()
    print(d._init_homegate("3edae810-5b68-421a-8ef3-ff69d80926e0","APIQG@vD13bS[ur2dGmT@5AI)","dicomiot","Dhome mini","DHG-A1","4e:f9:18:e4:c8:54","fe:f8:9b:e9:68:48","DH-A1-A05B200001","1.0","1.0"))
    # arser = argparse.ArgumentParser()
    # parser.add_argument('-i', '--id', help='id', action='store_true')
    # parser.add_argument('-t', '--token', help='Token', action='store_true')
    # parser.add_argument('-wan','--wan', help='Wan mac',action='store_true')
    # parser.add_argument('-wwan','--wwan', help='wwan mac',action='store_true')
    # parser.add_argument('-s','--serial', help='serial_number',action='store_true')
    # args = parser.parse_args()
    # if args.id and args.token and args.wan and args.wwan and arg.serial:
    #    print(d._init_homegate(args.id,args.token,"dicomiot","Dhome mini","DHG-A1",args.wan,args.wwan",arg.serial,"1.0","1.0"))
