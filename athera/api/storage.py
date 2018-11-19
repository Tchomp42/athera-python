import requests
from athera.api.common import headers, api_debug

route_driver  = "/storage/driver"
route_drivers  = "/storage/drivers"
route_driver_id  = "/storage/driver/{driver_id}"

# Drivers
@api_debug
def get_drivers(base_url, group_id, token):
    """
    Get all user storage drivers. It gets the drivers associated with the active-group-id and the one of its group lineage. 
    eg: If you provide a project-id, you will get as well the drivers for the org-id.
    Response: [403 Forbidden] Incorrect or inaccessible group_id
    """
    url = base_url + route_drivers
    response = requests.get(url, headers=headers(group_id, token))
    return response

@api_debug
def get_driver(base_url, group_id, token, driver_id):
    """
    Get storage driver from driver_id, you will get information such as on its type, its mounts and its indexing-status.
    Response: [403 Forbidden] Incorrect or inaccessible group_id
    """
    url = base_url + route_driver_id.format(driver_id=driver_id)
    response = requests.get(url, headers=headers(group_id, token))
    return response

@api_debug
def delete_driver(base_url, group_id, token, driver_id):
    """
    Get storage driver from driver_id, you will get information such as on its type, its mounts and its indexing-status.
    Response: [403 Forbidden] Incorrect or inaccessible group_id
    """
    url = base_url + route_driver_id.format(driver_id=driver_id)
    response = requests.delete(url, headers=headers(group_id, token))
    return response

def create_gcs_storage_driver_request(name, bucket_id, client_secret):
    return {
        "name": name,
        "gcs" : {
            "bucket_id": bucket_id,
            "client_secret": client_secret,
        },
        "option": {
            "create_default_mount": True,
        }
    }

@api_debug
def create_driver(base_url, group_id, token, storage_driver_request):
    """
    storage_driver_request parameter must be generated using the following function:
    - create_gcs_storage_driver_request()    
    Response: [403 Forbidden] Incorrect or inaccessible group_id
    """
    url = base_url + route_driver
    response = requests.post(url, headers=headers(group_id, token), json=storage_driver_request)
    return response


@api_debug
def rescan_driver(base_url, group_id, token, driver_id, path):
    """
    Response: [403 Forbidden] Incorrect or inaccessible group_id
    """
    body = {
        "type": "RESCAN",
        "path": path
    }
    url = base_url + route_driver_id.format(driver_id=driver_id)
    response = requests.post(url, headers=headers(group_id, token), json=body)
    return response

@api_debug
def dropcache_driver(base_url, group_id, token, driver_id):
    """
    This action should be avoided as much as possible. Use rescan driver if want a reindex.
    Response: [403 Forbidden] Incorrect or inaccessible group_id
    """
    body = {
        "type": "DROP"
    }
    url = base_url + route_driver_id.format(driver_id=driver_id)
    response = requests.post(url, headers=headers(group_id, token), json=body)
    return response


