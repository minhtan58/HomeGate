
import logging
logging.basicConfig()
logging.root.setLevel(logging.DEBUG)
import zigate
z = zigate.connect()

z.start_mqtt_local()
z.start_mqtt_cloud()
z.permit_join()

z.factory_reset()
z.erase_persistent()
