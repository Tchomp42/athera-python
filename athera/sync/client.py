import os
import logging
import grpc
from athera.sync.sirius.services import service_pb2
from athera.sync.sirius.services import service_pb2_grpc
import sys
import io 

MAX_CHUNK_SIZE = 1024 * 1024  # 1Mb

MAP_PRETTY_NAME_TO_REGION_NAME = {
    "us-west1": "us-west1.files.athera.io:443",
    "europe-west1": "files.athera.io:443",
    "australia-southeast1": "australia-southeast1.files.athera.io:443"
}

class Client(object):
    """
    Client to query the remote grpc file sync service, Sirius.
    Improvements:
    In a futur version, check if token is expired before performing api call; if so, refresh it.
    """

    def __init__(self, region, token):
        """ 
        'region': specifies the ingress point for the data. Use the region closest to you.
                  Other regions may have to perform a 'rescan' on the mount_id to detect the newly uploaded file.
        'token':  0Auth2 token. see more in athera.auth.generate_jwt.py on how to generate such token
        """
        
        self.url = MAP_PRETTY_NAME_TO_REGION_NAME.get(region)
        if not self.url:
            raise ValueError("Wrong region, please provide one of the following: {}".format(REGION_NAMES.keys()))
        self.credentials = grpc.ssl_channel_credentials()
        self.token = token
        channel = grpc.secure_channel(self.url, self.credentials)
        self.stub = stub = service_pb2_grpc.SiriusStub(channel)
       

    def get_mounts(self, group_id):
        """
        Using the provided credentials, which identify a user, provide the mounts for the supplied group.
        It returns of list of object of the type below

        sirius.types.Mount:
            id              // (str) The id of the mount
            name            // (str) The name of the mount
            mount_location  // (str) The mount root path
            group_id        // (str) The id of the mount belongs to

        """

        request = service_pb2.MountsRequest()
        
        metadata = [('authorization', "bearer: {}".format(self.token)),
                    ('active-group', group_id)]
                
        try:
            mountsResponse = self.stub.Mounts(request, metadata=metadata)
            return mountsResponse.mounts, None
        except grpc.RpcError as e:
            logging.debug("grpc.RpcError %s", e)
            return None, e
        except AttributeError as e:
            return None, e

    def get_files(self, group_id, mount_id, path="/"):
        """
        Using the provided credentials, group and mount, provide a list of files at the (optional) supplied path.
        Returns a generator of objects of the type below.

        sirius.services.FilesListResponse:
            path        // (str) The location where the listing has been done (relative to the mount root).
            mount_id    // (str) The id of the mount being queried
            file        // (sirius.types.File) A protobuf object, see below

        sirius.types.File:
            path        // (str) The full path of the file (relative to the mount root).
            name        // (str) Name
            mount_id    // (str) The id of the mount being queried
            size        // (int) Size of the object in bytes
            type        // (sirius.types.File.Type) See below
            
        sirius.types.File.Type:
            // A protobuf enumeration type.
           enum Type {
                UNKNOWN = 0;
                DIRECTORY = 1;
                FILE = 2;
                SEQUENCE = 3;
            }
        """
        request = service_pb2.FilesListRequest(mount_id=mount_id, path=path)
        metadata = [('authorization', "bearer: {}".format(self.token)),
                    ('active-group', group_id)]
        try:
            response = self.stub.FilesList(request, metadata=metadata)
            for resp in response:
                yield resp, None
        except grpc.RpcError as e:
            yield None, e

    def download_to_file(self, group_id, mount_id, destination_file, path="/", chunk_size=MAX_CHUNK_SIZE): # ToDo: User provide a buffer
        """
        Download a file by chunks of up to 1 Mb.
        It will return an error if the path is not a file.
        'destination_file': the downloaded file will be saved at this location on your machine.
        """
        if chunk_size >= MAX_CHUNK_SIZE: # We limit the chunk size to 1Mb
            raise ValueError("chunk_size is too high, the maximum value for chunck_size is {} (1Mb)".format(MAX_CHUNK_SIZE))
        request = service_pb2.FileContentsRequest(mount_id=mount_id, path=path, chunk_size=chunk_size)
        metadata = [('authorization', "bearer: {}".format(self.token)),
                    ('active-group', group_id)]
        total_bytes = 0
        try:
            response = self.stub.FileContents(request, metadata=metadata)
            for resp in response:
                destination_file.write(resp.bytes)
            logging.debug("Successfully wrote {} bytes into {}".format(total_bytes, destination_file.name))
        except grpc.RpcError as e:
            return e
        except AttributeError as e:
            return e

    def upload_file(self, group_id, mount_id, file_to_upload, destination_path, chunk_size=MAX_CHUNK_SIZE):
        """
        Upload a file by chunks of up to 1 Mb.
        mount_id allows you to select on which mount you would like to upload your file.
        file_to_upload is a file object of the file to upload, read access is enough.
        destination_path is the path on the mount at which the file will be uploaded (relative to the mount root).
            Let's say the root path of the mount (you want to upload your file to) is /data/org/default-my-org
            And within this mount, you want to upload your file in the folder 'uploads'
            Let's say your filename is 'my_secret_movie.mov'
            Your 'destination_path' would be: 'uploads/my_secret_movie.mov'
        """
        if chunk_size >= MAX_CHUNK_SIZE:
            raise ValueError("chunk_size is too high, the maximum value for chunck_size is {} (1Mb)".format(MAX_CHUNK_SIZE))
        
        metadata = [
            ('authorization', "bearer: {}".format(self.token)),
            ('active-group', group_id),
            ('mount-id', mount_id),
            ('path', destination_path),
        ]

        try:
            response = self.stub.FileUpload(
                self._retrieve_file_bytes(file_to_upload, chunk_size),
                metadata=metadata
            )
            return response, None
        except grpc.RpcError as e:
            return None, e
        except AttributeError as e:
            return None, e

    def _retrieve_file_bytes(self, file, chunk_size):
        chunk = file.read(chunk_size)
        while chunk != b"":
            yield service_pb2.FileUploadRequest(
                chunk_size=chunk_size,
                bytes=chunk,
            )
            chunk = file.read(chunk_size)