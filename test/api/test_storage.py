from settings import *
from athera.api import storage
import time
import unittest
import uuid
from requests import codes


class StorageTest(unittest.TestCase):
    # User Mounts
    def test_get_drivers(self):
        """ Positive test - Get drivers of the user, the provided group_id and the group's ancestors """
        response = storage.get_drivers(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
        )
        self.assertEqual(response.status_code, codes.ok)
        data = response.json()
        drivers = data['drivers'] 
        self.assertNotEqual(len(drivers), 0)
        first_driver = drivers[0]
        mounts = first_driver["mounts"]
        self.assertNotEqual(len(mounts), 0)

    def test_get_driver(self):
        """ Positive test -Get information on the driver """
        response = storage.get_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            environment.ATHERA_API_TEST_GROUP_DRIVER_ID,
        )
        self.assertEqual(response.status_code, codes.ok)
        driver = response.json()
        self.assertEqual(driver["type"], "GCS")
        statuses = driver["statuses"]
        self.assertNotEqual(len(statuses), 0)
        mounts = driver["mounts"]
        self.assertNotEqual(len(mounts), 0)
        mount = mounts[0]
        self.assertEqual(mount["type"], "MountTypeGroup")
        self.assertEqual(mount["id"], environment.ATHERA_API_TEST_GROUP_MOUNT_ID)
        self.assertEqual(mount["mountLocation"], environment.ATHERA_API_TEST_GROUP_MOUNT_LOCATION)

    def test_create_delete_gcs_driver(self):
        """ Positive test - Create & Delete a GCS driver """
        
        fake_name = "my driver"
        
        response = storage.create_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            storage.create_gcs_storage_driver_request(
                name=fake_name,
                bucket_id=environment.ATHERA_API_TEST_GCS_BUCKET_ID,
                client_secret=environment.ATHERA_API_TEST_GCS_CLIENT_SECRET,
            ),
        )
        self.assertEqual(response.status_code, codes.ok)
        driver = response.json()
        self.assertEqual(driver["name"], fake_name)
        self.assertEqual(driver["type"], "GCS")
        mounts = driver["mounts"]
        self.assertEqual(len(mounts), 1)
        mount = mounts[0]
        self.assertEqual(mount["type"], "MountTypeGroupCustom")
        self.assertEqual(mount["name"], fake_name)

        new_driver_id = driver["id"]

        # Delete driver
        response = storage.delete_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            driver["id"],
        )
        self.assertEqual(response.status_code, codes.ok)
        driver = response.json()
        self.assertEqual(driver["id"], new_driver_id)
        self.assertEqual(driver["name"], fake_name)
        self.assertEqual(driver["type"], "GCS")
        mounts = driver["mounts"]
        self.assertEqual(len(mounts), 1)
        mount = mounts[0]
        self.assertEqual(mount["type"], "MountTypeGroupCustom")
        self.assertEqual(mount["name"], fake_name)

    def test_rescan_driver_root(self):
        """ Positive test - Rescans the entire driver """
        driver_id = environment.ATHERA_API_TEST_GROUP_DRIVER_ID
        status = self.get_driver_indexing_status(driver_id)
        self.assertEqual(status['indexingInProgress'], False)
        
        response = storage.rescan_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            driver_id,
            "/"
        )
        self.assertEqual(response.status_code, codes.ok)
        # Wait for rescan to finish and checks for rescan path to equals "/"
        timeout = 600
        interval = 2
        time.sleep(interval) #Wait for PandoraWorker to launch the task
        while timeout > 0:
            status = self.get_driver_indexing_status(driver_id)
            if status['indexingInProgress'] == False:
                self.assertEqual(status['path'], "/")
                break
            time.sleep(interval)        
            timeout -= interval
            print("Still in progress ...")
        self.assertGreater(timeout, 0)

    def test_rescan_driver_broken_path(self):
        """ Error test - Rescans request has wrong path argument """
        driver_id = environment.ATHERA_API_TEST_GROUP_DRIVER_ID
        status = self.get_driver_indexing_status(driver_id)
        self.assertEqual(status['indexingInProgress'], False)

        response = storage.rescan_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            driver_id,
            "path/must/start/with/root/lol"
        )
        self.assertEqual(response.status_code, codes.bad_request)

    def test_rescan_driver_subfolder(self):
        """ Positive test - Rescans a subfolder """
        driver_id = environment.ATHERA_API_TEST_GROUP_DRIVER_ID
        status = self.get_driver_indexing_status(driver_id)
        self.assertEqual(status['indexingInProgress'], False)
        
        response = storage.rescan_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            driver_id,
            "/toto/tata"
        )
        self.assertEqual(response.status_code, codes.ok)
        # Wait for rescan to finish and checks for rescan path to equals "/"
        timeout = 600
        interval = 2
        time.sleep(interval) #Wait for PandoraWorker to launch the task
        while timeout > 0:
            status = self.get_driver_indexing_status(driver_id)
            if status['indexingInProgress'] == False:
                self.assertEqual(status['path'], "/toto/tata")
                break
            time.sleep(interval)        
            timeout -= interval
            print("Still in progress ...")
        self.assertGreater(timeout, 0)

    def test_dropcache_driver(self):
        """ Positive test - List the mounts the authenticated user has in this group """
        driver_id = environment.ATHERA_API_TEST_GROUP_DRIVER_ID
        status = self.get_driver_indexing_status(driver_id)
        self.assertEqual(status, False)
        
        response = storage.dropcache_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            driver_id,
        )
        self.assertEqual(response.status_code, codes.ok)


    def get_driver_indexing_status(self, driver_id):
        response = storage.get_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            environment.ATHERA_API_TEST_TOKEN,
            driver_id,
        )
        self.assertEqual(response.status_code, codes.ok)
        data = response.json()
        # print (data)
        self.assertEqual(data["type"], "GCS") # This is only guaranteed if using GROUP_DRIVER
        statuses = data["statuses"]
        self.assertNotEqual(len(statuses), 0)
        indexing_status = statuses[0] # Getting indexing status for the first region assuming it's the one we want
        return indexing_status
    