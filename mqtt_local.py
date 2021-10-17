from pydispatch import dispatcher
import logging
import secrets
from .const import (ZIGATE_ATTRIBUTE_ADDED, ZIGATE_CHANNEL_UPDATED,
                    ZIGATE_DEVICE_ADDED, ZIGATE_DEVICE_REMOVED,
                    ZIGATE_DEVICE_UPDATED, ZIGATE_RULE_UPDATED,
                    ZIGATE_CHANNEL_ALARM_UPDATED, MQTT_MESSAGE_ACTION)
import paho.mqtt.client as mqtt
import json
import ssl
from .config import (CA_LOCAL, CLIENT_LOCAL_CRT, CLIENT_LOCAL_KEY, MQTT_LOCAL_HOST,
                     MQTT_LOCAL_USERNAME, MQTT_LOCAL_PORT, MAIN_LOCAL_TOPIC, APP_ID, USER_ID_INIT, TOKEN_INIT)
from .config_manager import ConfigManager
import time
import logging
LOGGER = logging.getLogger("MQTT_LOCAL")
class MQTT_Broker(object):

    def __init__(self, zigate, db):
        self.zigate = zigate
        self.db = db
        self.hg = self.db.get_homegate_info_all()
        self.user = self.db.get_all_user()
        self.client = mqtt.Client(
            client_id=self.hg['serial'], clean_session=False, userdata=None, transport="tcp")
        # self.client.tls_set(ca_certs=CA_LOCAL, certfile=CLIENT_LOCAL_CRT,keyfile=CLIENT_LOCAL_KEY, cert_reqs=ssl.CERT_REQUIRED,
        #                     tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
        self.client.username_pw_set(MQTT_LOCAL_USERNAME, self.hg['token'])
        dispatcher.connect(self.channel_updated, ZIGATE_CHANNEL_UPDATED)
        dispatcher.connect(self.channel_alarm_updated,
                           ZIGATE_CHANNEL_ALARM_UPDATED)
        dispatcher.connect(self.device_added, ZIGATE_DEVICE_ADDED)
        dispatcher.connect(self.device_updated, ZIGATE_DEVICE_UPDATED)
        dispatcher.connect(self.device_removed, ZIGATE_DEVICE_REMOVED)
        dispatcher.connect(self.rule_updated, ZIGATE_RULE_UPDATED)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.will_set(MAIN_LOCAL_TOPIC+"/response/all/info",
                             payload=self.offline(), qos=0, retain=False)

    def connect(self):
        self.client.connect(MQTT_LOCAL_HOST, MQTT_LOCAL_PORT,
                            60, bind_address="0.0.0.0")

    def start(self):
        self.connect()
        self.client.loop_forever()

    def offline(self):
        data = {"action": "update",
                "token": "",
                          "type": "state",
                          "value": {
                              "state": 0
                          }
                }
        return json.dumps(data)

    def online(self):
        data = {"state": 1}
        self._publish_response_default("info", "update", "state", data)

    def topic_filter(self, topic):
        return list(topic.split("/"))

    def dispatch_signal(signal=dispatcher.Any, sender=dispatcher.Anonymous,
                        *arguments, **named):
        '''
        Dispatch signal with exception proof
        '''
        LOGGER.debug('Dispatch %s', signal)
        try:
            dispatcher.send(signal, sender, *arguments, **named)
        except Exception:
            LOGGER.error('Exception dispatching signal %s', signal)
            LOGGER.error(traceback.format_exc())

    def _publish_request(self, topic, action, name, value):
        '''
        Publish data request topic
        '''
        topics = MAIN_LOCAL_TOPIC+"/request/{}".format(topic)
        data = {"action": action,
                "token": "",
                "type": name,
                "value": value
                }
        LOGGER.debug('Publish data request  %s',topics)
        self.client.publish(topics, json.dumps(data), retain=False)

    def _publish_response(self, topic, action, type, value, channel_id=None, user_id=None, access_token=None):
        '''
        Publish data response topic
        Error topic code :
                  0 : Not correct data
                  1 : Not found
                  2 : Missing param
        '''
        if user_id is not None:
            topics = MAIN_LOCAL_TOPIC+"/response/"+user_id+"/{}".format(topic)
            data = {"action": action,
                    "token": access_token,
                    "type": type,
                    "value": value
                    }
            LOGGER.debug('Publish data %s',topics)
            self.client.publish(topics, json.dumps(data), retain=False)
        else:
            for user in self.user:
                if user[5] == 1:
                    topics = MAIN_LOCAL_TOPIC+"/response/" + \
                        user[0]+"/{}".format(topic)
                    data = {"action": action,
                            "token": user[6],
                            "type": type,
                            "value": value
                            }
                    LOGGER.debug('Publish data %s',topics)
                    self.client.publish(topics, json.dumps(data), retain=False)
                else:
                    limit_user = self.db.check_user_access_channle(
                        user[0], channel_id)
                    if limit_user:
                        topics = MAIN_LOCAL_TOPIC+"/response/" + \
                            user[0]+"/{}".format(topic)
                        data = {"action": action,
                                "token": user[6],
                                "type": type,
                                "value": value
                                }
                        LOGGER.debug('Publish data %s',topics)
                        self.client.publish(
                            topics, json.dumps(data), retain=False)

    def _publish_response_default(self, topic, action, type, value):
        '''
        Publish data response topic
        '''
        topics = MAIN_LOCAL_TOPIC+"/response/all/{}".format(topic)
        data = {"action": action,
                "token": "",
                "type": type,
                "value": value
                }
        LOGGER.debug('Publish default %s',topics)
        self.client.publish(topics, json.dumps(data), retain=False)

    def _publish_response_init(self, topic, action, type, value):
        '''
        Publish data response topic
        '''
        topics = MAIN_LOCAL_TOPIC+"/response/"+USER_ID_INIT+"/{}".format(topic)
        data = {"action": action,
                "token": TOKEN_INIT,
                "type": type,
                "value": value
                }
        LOGGER.debug('Publish data init %s',topics)
        self.client.publish(topics, json.dumps(data), retain=False)

    def _publish_data_init(self):
        '''
        Publish data init when startup
        '''
        self._publish_response("reload","update","all",self.db.update_total_homegate_db())

    def device_added(self, device):
        self._publish_response("device", "add", "add_new", device)
        rules = self.db.get_rule_secure()
        self._publish_response("rules", "update", "rule_channel", rules)

    def device_updated(self, device):
        LOGGER.debug('Device_changed {}'.format(device))
        # self.db._update_data(device)

    def device_removed(self, device):
        '''
        Remove device
        '''
        LOGGER.debug('Device_removed {}'.format(id))
        # self._publish_request("device","delete","id",id)

    # Channel
    def channel_updated(self, channel):
        if channel:
            self._publish_response("channel", "update", "status", channel)

    def channel_alarm_updated(self, channel):
        if channel:
            if channel['notifi'] != False:
                self._publish_response(
                    "notification", "add", "channel", channel['notifi'])
            self._publish_response("channel", "update",
                                   "status", channel['channel'])
    # User

    def rule_updated(self, rule):
        if rule:
            action = {"id": rule['id']}
            self._publish_response("rule", "run", rule['type'], action)

    # On connect and receive message Mqtt cloud
    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected with result code {}".format(rc))
        client.subscribe(MAIN_LOCAL_TOPIC+"/request/#")
        self.online()
        # self._publish_data_init()

    def on_disconnect(self, client, userdata, flags, rc):
        if rc == 1:
            self.client.reconnect()

    def on_message(self, client, userdata, msg):

        access_token = ""
        payload = {}
        if msg.payload:
            payload = json.loads(msg.payload.decode())
            access_token = payload['token']
        if msg.topic:
            topic = self.topic_filter(msg.topic)
            n = topic[1]
            command = str(topic[2])
            user_id = str(topic[3])
            type_action = str(topic[4])
            print(topic)
            print(payload)
            if user_id == 'all':
                if type_action == 'user':
                    self.login_response(payload)
                elif type_action == 'info':
                    self.homegate_response(payload)
                elif type_action == 'doorbell':
                    sefl.doorbell_response(payload)
                else:
                    pass
            for user in self.user:
                if user[6] == access_token:
                    if type_action == 'config':
                        self.config_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'homegate':
                        self.homegate_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'device':
                        self.device_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'channel':
                        self.channel_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'notification':
                        self.notifi_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'rule':
                        self.rule_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'camera':
                        self.camera_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'user':
                        self.user_response(data=payload, user=user_id, token=access_token)
                    elif type_action == 'room':
                        self.room_response(data=payload, user=user_id, token=access_token)
                    else:
                        print("Not found action")
                else:
                    print("Access_token error")
    ###### USER ######

    def login_response(self, data):
        if data['action'] == 'add' and data['type'] == 'login':
            value = data['value']
            if value['app_id'] == APP_ID and value['token_homegate'] == self.hg['token']:
                token = secrets.token_urlsafe(32)
                user = self.db.add_user(value['user_id'], "Admin", 1, token)
                if user == 1:
                    data = {"access_token": token}
                    self.user = self.db.get_all_user()
                    self._publish_response(
                        "user", "add", "login", data, user_id=value['user_id'], access_token=token)
                else:
                    data = {"access_token": user[6]}
                    self._publish_response(
                        "user", "add", "login", data, user_id=value['user_id'], access_token=user[6])
            else:
                self._publish_response_default(
                    "error", "add", "login", {"code": 0})

    def init_response(self, data):
        if data['action'] == 'init' and data['type'] == 'homegate' and data['token'] == TOKEN_INIT:
            value = data['value']
            print("ValueS", value)
            sys = ConfigManager().config_system(
                value['token'], value['serial'], value['wwan_mac'], value['wan_mac'])
            print("System", sys)
            if sys:
                data = self.db._init_homegate(value['id'], value['token'], value['site'], value['name'], value['model'], value['wan_mac'],
                                              value['wwan_mac'], value['serial'], value['sw_version'], value['zig_version'])
                print("Data", data)
                self._publish_response_init("config", "add", "homegate", data)
        elif data['action'] == 'command' and data['type'] == 'system' and data['token'] == TOKEN_INIT:
            value = data['value']
            if value:
                data = ConfigManager().cmd(value['cmd'])
                self._publish_response_init(
                    "config", "command", "system", data)
        else:
            pass


    def config_response(self, data, user, token):
        if data['action'] == 'update' and data['type'] == 'set_wifi':
            value = data['value']
            if value:
                wifi = ConfigManager().add_wifi(
                    value['ssid'], value['password'])
                if wifi:
                    self._publish_response("config", "update", "set_wifi", {
                                           "success": True}, user_id=user, access_token=token)
                else:
                    self._publish_response("error", "update", "set_wifi", {
                                           "code": 0}, user_id=user, access_token=token)

    # Device Response
    def homegate_response(self, data, user, token):
        if data['action'] == 'get':
            if data['type'] == 'id':
                data = self.db.update_total_homegate_db()
                if data:
                    self._publish_response(
                        "homegate", "update", "id", data, user_id=user, access_token=token)
        elif data['action'] == 'get' and data['type'] == 'info':
            data = self.db.get_homegate_info()
            self._publish_response_default(
                "info", "get", "info", data, user_id=user, access_token=token)
        elif data['action'] == 'update' and data['type'] == 'sw_update':
            value = data['value']
            ConfigManager().udpate(value['site'], value['version'])

        else:
            pass

    def device_response(self, data, user, token):
        value = data['value']
        if data['action'] == 'get':
            if data['type'] == 'all':
                device = self.db.get_device(all=True)
                self._publish_response(
                    "device", "get", "all", device, user_id=user, access_token=token)
        elif data['action'] == "update":
            value = data.value
            device = self.db.update_device(
                value.id, data['type'], value[data['type']])
            if device:
                self._publish_response("device", "update", "success", data['type'], self.db.get_device(
                    id=value.id), user_id=user, access_token=token)
            else:
                self._publish_response(
                    "device", "update", "error", data['type'], device, user_id=user, access_token=token)
        elif data['action'] == 'add':
            if data['type'] == "permit_join":
                if value['status'] == 1:
                    print("Action permit")
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
                    print("Remove device ", value['id'])
                    self.zigate.remove_device_ieee(device)
                    self._publish_response("device", "delete", "id", {
                                           "id": value['id']}, user_id=user, access_token=token)
                else:
                    self._publish_response("error", "delete", "device", {
                                           "code": 0}, user_id=user, access_token=token)
        else:
            pass

    def channel_response(self, data, user, token):
        value = data['value']
        if data['action'] == "update":
            if data['type'] == "status":
                ieee = self.db._get_ieee(value.id)
                if ieee:
                    self.action_onoff(ieee, int(value[data['type']]))
                    channel = self.db.update_device(
                        value.id, data['type'], value[data['type']])
            if data['type'] == "all":
               channle =  self.db.update_channel_info(value['id'],data['value'])
               if channle == False:
                  self._publish_response("channel", "update", "all", {
                                          "id": value['id']}, user_id=user, access_token=token)

        elif data['action'] == 'get':
            if data['type'] == 'id':
                channel = self.db.get_channel(id=data.value)
                if device:
                    self._publish_data(
                        "channle", "get", "success", "id", channel)
                else:
                    self._publish_data(
                        "channel", "get", "error", "id", channel)
            elif data['type'] == 'all':
                device = self.db.get_device(all=True)
                self._publish_data("device", "get", "success", "all", device)
        elif data['action'] == 'delete':
            ''' Delete device
                    Check id if have return ieee or return False
            '''
            if data['type'] == "id":
                device = self.db.remove_channel(value['id'])
                if device:
                    LOGGER.debug("Delete channel %s",value['id'])
                    self.zigate.remove_device_ieee(device)
                    self._publish_response("channel", "delete", "id", {
                                           "id": value['id']}, user_id=user, access_token=token)

                else:
                    self._publish_response("error", "delete", "channel", {
                                           "code": 0}, user_id=user, access_token=token)

    def rule_response(self, data, user, token):
        value = data['value']
        if data['action'] == "run":
            if data['type'] == '1':
                self.zigate.action_ias_set_enable_warning(1)
                rule_condidtion_channel = self.db.update_rule_alarm(1, 1)
                for c in rule_condidtion_channel['channels']:
                    print("List device enable ", c)
                    self.zigate.action_ias_set_zone_node_valid(
                        c['zone_id'], c['zone_status'])
            elif data['type'] == '2':
                self.zigate.action_ias_set_diasble_warning()
                rule_condidtion_channel = self.db.update_rule_alarm(2, 1)

            elif data['type'] == '3':
                self.zigate.action_ias_set_in_home()
                rule_condidtion_channel = self.db.update_rule_alarm(3, 1)
                for c in rule_condidtion_channel['channels']:
                    print("List device athome enable ", c)
                    self.zigate.action_ias_set_zone_node_valid(
                        c['zone_id'], c['zone_status'])

            elif data['type'] == '4':
                rule_condidtion_channel = self.db.update_rule_alarm(4, 1)
                for c in rule_condidtion_channel:
                    if c['type'] == 21:
                        status = c['status']
                        #[{'type': 'volume', 'value': 1}, {'type': 'duration', 'value': 180}]
                        level = status[0]['value']
                        duration = status[1]['value']
                        self.zigate.action_ias_warning(c['ieee'], duration, level)
            else:
                pass
        # else data['action'] == "delete":
        #      pass

    def notifi_response(self, data, user, token):
        if data['action'] == "get" and data['type'] == "all":
            noti = self.db.get_all_notifi()
            self._publish_response("rules", "update", "status", {
                                   "notification": noti}, user_id=user, access_token=token)
    def doorbell_response(self):
        self.zigate._call_door_bell()
    def room_response(self):
        value = data['value']
        if data['action'] == "add":
           self.db.add_room(value)
           self._publish_response("rules", "update", "status", {
                                  "notification": noti}, user_id=user, access_token=token)
        elif data['action'] == "update" and data['type'] == 'id':
             self.db.update_room(value['id'],value)
