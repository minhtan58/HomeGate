#!/bin/sh /etc/rc.common

USE_PROCD=1

START=86
STOP=01

CONFIGURATION=config

start_service() {
    # Reading config
    config_load "${CONFIGURATION}"
    local port
    local channel
    local mqtt_local
    local mqtt_cloud
    local admin_panel
    local debug
    local jn_version
    local sw_version
    # Config /etc/config/dhome
    config_get port connect port
    config_get channel connect channel
    config_get mqtt_local connect mqtt_local
    config_get mqtt_cloud connect mqtt_cloud
    config_get admin_panel setting admin_panel
    config_get debug setting debug
    config_get jn_verion info jn_version
    config_get sw_verion info sw_version


    procd_open_instance

    # pass config to script on start
    procd_set_param command /usr/bin/python3.7 -m zigate
    procd_set_param file /etc/config/dhome
    procd_set_param respawn \
      ${respawn_threshold:-3600} \
      ${respawn_timeout:-5} ${respawn_retry:-5}
    procd_set_param limits core="unlimited"
    procd_set_param user root
    procd_set_param pidfile /var/run/dhome.pid
    procd_set_param stdout 1
    procd_set_param stderr 1
    procd_close_instance
}
