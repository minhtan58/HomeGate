#! /usr/bin/python3


class Homegate(object):
    """docstring fo Homegate entity."""

    def __init__(self,id,site,name,token,wan_mac,wwan_mac,ip_local,ip_public,model,serial,state,config,zig_version,hw_version,sw_version,created,updated,last_update,last_seen):
        self.id = id
        self.site = site
        self.name = name
        self.token = token
        self.wan_mac = wan_mac
        self.wwan_mac = wwan_mac
        self.ip_local = ip_local
        self.ip_public = ip_public
        self.model = model
        self.serial = serial
        self.state = state
        self.config = config
        self.zig_version = zig_version
        self.hw_version = hw_version
        self.created = created
        self.last_update =last_update
        self.updated = updated
        self.last_seen =last_seen
