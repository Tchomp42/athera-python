from settings import *
from athera.api import storage
import time
import unittest
import uuid
from requests import codes
import os

class StorageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = os.getenv("ATHERA_API_TEST_TOKEN")
        if not cls.token:
            raise ValueError("ATHERA_API_TEST_TOKEN environment variable must be set")

    # User Mounts
    def test_get_drivers(self):
        """ Positive test - Get drivers of the user, the provided group_id and the group's ancestors """
        response = storage.get_drivers(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            self.token,
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
            self.token,
            environment.ATHERA_API_TEST_ORG_DRIVER_ID,
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
            self.token,
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
            self.token,
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

    def test_rescan_driver(self):
        """ Positive test - Perform a rescan on the HOME driver"""
        driver_id = environment.ATHERA_API_TEST_HOME_DRIVER_ID
        status = self.get_driver_indexing_status(driver_id)
        self.assertEqual(status, False, "Cannot test rescan because Home driver is being indexed")
        
        response = storage.rescan_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            self.token,
            driver_id,
        )
        self.assertEqual(response.status_code, codes.ok)
        

    def test_dropcache_driver(self):
        """ Positive test - Perform a Drop Cache on the Org driver """
        driver_id = environment.ATHERA_API_TEST_ORG_DRIVER_ID
        status = self.get_driver_indexing_status(driver_id)
        self.assertEqual(status, False, "Cannot test dropcache because Org driver is being indexed")
        
        response = storage.dropcache_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            self.token,
            driver_id,
        )
        self.assertEqual(response.status_code, codes.ok)


    def get_driver_indexing_status(self, driver_id):
        response = storage.get_driver(
            environment.ATHERA_API_TEST_BASE_URL,
            environment.ATHERA_API_TEST_GROUP_ID,
            self.token,
            driver_id,
        )
        self.assertEqual(response.status_code, codes.ok)
        data = response.json()
        self.assertEqual(data["type"], "GCS")
        statuses = data["statuses"]
        self.assertNotEqual(len(statuses), 0)
        reindex_status = statuses[0]
        return reindex_status["indexingInProgress"]
    