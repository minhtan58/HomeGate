
from pydispatch import dispatcher
import logging
from .const import (ZIGATE_ATTRIBUTE_ADDED, ZIGATE_CHANNEL_UPDATED,
                    ZIGATE_DEVICE_ADDED, ZIGATE_DEVICE_REMOVED,
                    ZIGATE_DEVICE_UPDATED,ZIGATE_RULE_UPDATED,
                    ZIGATE_CHANNEL_ALARM_UPDATED,MQTT_MESSAGE_ACTION,DOOR_BELL_CALL)
import paho.mqtt.client as mqtt
import json
import ssl
from .config import (CA_CLOUD,CLIENT_CLOUD_CRT,CLIENT_CLOUD_KEY,MQTT_CLOUD_HOST,MQTT_CLOUD_PORT,MAIN_CLOUD_TOPIC)
from .config_manager import ConfigManager
class MQTT_Broker(object):

    def __init__(self,zigate,db):
        ''' Connect Mqtt Cloud
            client_id : Homegate serial_number
            username : Homegate id
            password : Homegate token
        '''
        self.db = db
        self.zigate = zigate
        self.hg = self.db.get_homegate_info_all()
        self.main_topic = MAIN_CLOUD_TOPIC+self.hg['id']
        self.client = mqtt.Client(client_id=self.hg['serial'],clean_session=True, userdata=None, transport="tcp")
        self.client.tls_set(ca_certs=CA_CLOUD, certfile=CLIENT_CLOUD_CRT,keyfile=CLIENT_CLOUD_KEY, cert_reqs=ssl.CERT_REQUIRED,
                            tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
        self.client.username_pw_set(self.hg['id'],self.hg['token'])
        dispatcher.connect(self.channel_updated, ZIGATE_CHANNEL_UPDATED)
        dispatcher.connect(self.channel_alarm_updated,ZIGATE_CHANNEL_ALARM_UPDATED)
        dispatcher.connect(self.device_added, ZIGATE_DEVICE_ADDED)
        dispatcher.connect(self.device_updated, ZIGATE_DEVICE_UPDATED)
        dispatcher.connect(self.device_removed, ZIGATE_DEVICE_REMOVED)
        dispatcher.connect(self.rule_updated, ZIGATE_RULE_UPDATED)
        dispatcher.connect(self.door_bell_call, DOOR_BELL_CALL)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(self.main_topic+"/response/info", payload=self.offline(), qos=0, retain=True)

    def connect(self):
        self.client.connect(MQTT_CLOUD_HOST,MQTT_CLOUD_PORT,30)

    def start(self):
        self.connect()
        self.client.loop_forever()
    def offline(self):
        data = {  "action":"update",
                  "token":self.hg['token'],
                  "type":"state",
                  "value":{
                  "state":0
                  }
                }
        return json.dumps(data)
    def online(self):
        data = {"state":1}
        self._publish_response("info","update","state",data)
    def join_user_homegate(self):
        user = self.db.get_all_user_id()
        self._publish_response("user","join","user_id",{"user_id":user})

    def topic_filter(self,topic):
        return list(topic.split("/"))
    def get_homegate_info(self):
        return self.db.get_homegate_info()

    def _publish_request(self, topic, action,name,value):
        '''
        Publish data request topic
        '''
        topics = self.main_topic+"/request/{}".format(topic)
        data = {  "action":action,
                  "token":self.hg['token'],
                  "type":name,
                  "value":value
                }
        logging.info('Publish {}'.format(topics))
        self.client.publish(topics,json.dumps(data), retain=False)

    def _publish_response(self,topic,action,name,value):
        '''
        Publish data response topic
        '''
        topics = self.main_topic+"/response/{}".format(topic)
        data = {  "action":action,
                  "token":self.hg['token'],
                  "type":name,
                  "value":value
                }
        print('Publish {}'.format(topics))
        self.client.publish(topics,json.dumps(data), retain=False)
    def _publish_data_init(self):
        '''
        Publish data init when startup
        '''
        self._publish_response("user","join","user_id",{"user_id":self.db.get_all_user_id()})
        ip = ConfigManager().cmd('/etc/dhome/network/check_ip_local')
        self.db.update_homegate_info("ip_local",str(ip),self.hg['id'])
        self._publish_response("reload","update","all",self.db.update_total_homegate_db())

    def device_added(self,device):
        print(device)
        self._publish_response("device","add","add_new",device)

    def device_updated(self,device):
        logging.debug('Device_changed {}'.format(device))
        # self.db._update_data(device)

    def device_removed(self, device):
        '''
        Remove device
        '''
        logging.debug('Device_removed {}'.format(id))
        # self._publish_request("device","delete","id",id)

    # Channel
    def channel_updated(self,channel):
        print('Channel_updated {}'.format(channel))
        if channel:
           self._publish_response("channel","update","status",channel)
    def channel_alarm_updated(self,channel):
        print('Channel_updated alarm  {}'.format(channel))
        if channel:
           if channel['notifi'] !=False:
              self._publish_response("notification","add","channel",channel['notifi'])
           self._publish_response("channel","update","status",channel['channel'])
    # User
    def rule_updated(self,rule):
        print("Rules updated".format(rule))
        if rule:
           action  = {"id":rule['id']}
           self._publish_response("rule","run",rule['type'],action)

    ## On connect and receive message Mqtt cloud
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(self.main_topic+"/request/#")
            self.online()
            try:
                ip = ConfigManager().get_ip_local()
                if ip:
                   self.db.update_homegate_info("ip_local",str(ip),self.hg['id'])
                self._publish_response("reload","update","all",self.db.update_total_homegate_db())
            except Exception as e:
                   print(e)
            self._publish_response("user","join","user_id",{"user_id":self.db.get_all_user_id()})
            print("connected {}".format(rc))
        else:
            print("Bad connection Returned code=",rc)
    def on_disconnect(self, client, userdata, flags, rc):
        if rc != 0:
           self.client.reconnect()
           print("On_disconnect.......................")
    def on_message(self, client, userdata, msg):
        payload = {}
        if msg.payload:
            payload = json.loads(msg.payload.decode())
            print("Cloud message",payload)

        if msg.topic:
           topic = self.topic_filter(msg.topic)
           print("Cloud topic",topic)
           command = str(topic[2])
           user_id = str(topic[3])
           type_action = str(topic[4])
           if type_action == "device":
              self.device_response(payload)
           elif type_action == "channel":
                self.channel_respone(payload)
           elif type_action == "camera":
                self.camera_respone(payload)
           elif type_action == "rule":
                self.rule_respone(payload)
           elif type_action == "homegate":
                self.homegate_response(payload)
           elif type_action == "notification":
                self.notifi_respone(payload)
           else:
               pass

    # Device Response
    def homegate_response(self,data):
        print(data['action'])
        if data['action'] == 'get':
           if data['type'] == 'id':
              data = self.db.update_total_homegate_db()
              if data:
                 self._publish_response("homegate","update","id",data)
        elif data['action'] == 'get' and data['type'] =='info':
             data = self.db.get_homegate_info()
             self._publish_response_default("info","get","info",data)
        elif data['action']  == 'update' and data['type'] == 'sw_update':
             value = data['value']
             ConfigManager().udpate(value['site'],value['version'])
        else:
            pass
    def device_response(self,data):
        value = data['value']
        if data['action'] == 'get':
           if data['type'] == 'all':
              device = self.db.get_device(all=True)
              self._publish_response("device","get","all",)
        elif data['action'] == "update":
             value = data.value
             device = self.db.update_device(value.id,data['type'],value[data['type']])
             if device:
                self._publish_response("device","update","success",data['type'],self.db.get_device(id=value.id))
             else:
                self._publish_response("device","update","error",data['type'],device)
        elif data['action'] == 'add':
             if data['type'] == "permit_join":
                if value['status']== 1:
                   self.zigate.permit_join()
                else:
                   self.zigate.stop_permit_join()
        elif data['action'] == "delete":
             ''' Delete device
                 Check id if have return ieee or return False
             '''
             if data['type'] == "id":
                device = self.db.remove_device(value['id'])
                if device:
                    print("Remove device ",value['id'])
                    self.zigate.remove_device_ieee(device)
                    self._publish_response("device","delete","id",{"id":value['id']})
                else:
                   self._publish_response("error","delete","device",{"code":0})
        else:
            pass

    def channel_respone(self,data):
        if data['action'] == "update":
           if data['type'] == "status":
              ieee = self.db._get_ieee(value.id)
              if ieee:
                 self.action_onoff(ieee,int(value[data['type']]))
                 channel = self.db.update_device(value.id,data['type'],value[data['type']])
           if name == "config":
              pass
        elif data['action'] == 'get':
           if data['type'] == 'id':
              channel = self.db.get_channel(id=data.value)
              if device:
                 self._publish_data("channle","get","success","id",channel)
              else:
                 self._publish_data("channel","get","error","id",channel)
           elif data['type'] == 'all':
                device = self.db.get_device(all=True)
                self._publish_data("device","get","success","all",device)
        elif data['action'] == 'delete':
             ''' Delete device
                 Check id if have return ieee or return False
             '''
             if data['type'] == "id":
                device = self.db.remove_device(value['id'])
                if device:
                    print("Remove device ",value['id'])
                    self.zigate.remove_device_ieee(device)
                    self._publish_response("device","delete","id",{"id":value['id']})
                else:
                   self._publish_response("error","delete","device",{"code":0})

    def rule_respone(self,data):
        value = data['value']
        if data['action'] == "run":
           if data['type'] == '1':
              self.zigate.action_ias_set_enable_warning(1)
              rule_condidtion_channel = self.db.update_rule_alarm(1,1)
              for c in rule_condidtion_channel['channels']:
                  print("List device enable ",c)
                  self.zigate.action_ias_set_zone_node_valid(c['zone_id'],c['zone_status'])
           elif data['type'] == '0':
                self.zigate.action_ias_set_diasble_warning()
                rule_condidtion_channel = self.db.update_rule_alarm(0,1)

           elif data['type'] == '2':
                self.zigate.action_ias_set_in_home()
                rule_condidtion_channel = self.db.update_rule_alarm(2,1)
                for c in rule_condidtion_channel['channels']:
                    print("List device athome enable ",c)
                    self.zigate.action_ias_set_zone_node_valid(c['zone_id'],c['zone_status'])

           elif data['type'] == '3':
                rule_condidtion_channel = self.db.update_rule_alarm(3,1)
                for c in rule_condidtion_channel:
                       if c['type'] == 21:
                          status = c['status']
                          #[{'type': 'volume', 'value': 1}, {'type': 'duration', 'value': 180}]
                          level = status[0]['value']
                          duration = status[1]['value']
                          self.zigate.action_ias_warning(c['ieee'],duration,level)
           else:
                pass
        # else data['action'] == "delete":
        #      pass
    def camera_respone(self,data):
        value = data['value']
        if data['action'] == "add" and data['type'] == "id":
           camera =  self.db.add_new_camera(value['name'],value['cameraInfo'],value['cameraIp'],value['cameraUris'],value['room_id'])
           if camera:
              self._publish_response("camera","add","id",camera)
        elif data['action'] == "get" and data['type'] == "all":
             data_camera = self.db.get_camera(all=True)
             self._publish_response("camera","get","all",data_camera)

    def notifi_respone(self,data,user,token):
        if data['action'] == "get" and data['type'] == "all":
           noti = self.db.get_all_notifi()
           self._publish_response("rules","update","status",{"notification":noti})
    def door_bell_call(self):
        data = self.db.add_door_bell_noti()
        self._publish_response("notification","add","channel",data)
