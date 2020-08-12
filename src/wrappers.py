import zeroconf
from zeroconf import ServiceInfo
from packaging import version

zc_version = version.parse(zeroconf.__version__)
break_version = version.parse("0.27")

zc_new_api = zc_version >= break_version

# python-zeroconf breaks api for >=0.27, ServiceInfo 'address' is removed,
# 'addresses' needs to be used

def new_service_info(type_: str,
                     name: str,
                     address: bytes,
                     port: int,
                     properties={}):

    if zc_new_api:
        return ServiceInfo(type_,
                           name,
                           port=port,
                           addresses=[address],
                           properties=properties)
    else:
        return ServiceInfo(type_,
                           name,
                           address,
                           port,
                           properties=properties)
