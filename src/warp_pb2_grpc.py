# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

import warp_pb2 as warp__pb2

GRPC_GENERATED_VERSION = '1.73.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in warp_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class WarpStub(object):
    """************ Important! ***************

    If you change anything here, you *must* run 'generate-protobuf' to update the
    generated stub files.

    Never change the existing members and member values of messages, only add new ones.

    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.CheckDuplexConnection = channel.unary_unary(
                '/Warp/CheckDuplexConnection',
                request_serializer=warp__pb2.LookupName.SerializeToString,
                response_deserializer=warp__pb2.HaveDuplex.FromString,
                _registered_method=True)
        self.WaitingForDuplex = channel.unary_unary(
                '/Warp/WaitingForDuplex',
                request_serializer=warp__pb2.LookupName.SerializeToString,
                response_deserializer=warp__pb2.HaveDuplex.FromString,
                _registered_method=True)
        self.GetRemoteMachineInfo = channel.unary_unary(
                '/Warp/GetRemoteMachineInfo',
                request_serializer=warp__pb2.LookupName.SerializeToString,
                response_deserializer=warp__pb2.RemoteMachineInfo.FromString,
                _registered_method=True)
        self.GetRemoteMachineAvatar = channel.unary_stream(
                '/Warp/GetRemoteMachineAvatar',
                request_serializer=warp__pb2.LookupName.SerializeToString,
                response_deserializer=warp__pb2.RemoteMachineAvatar.FromString,
                _registered_method=True)
        self.ProcessTransferOpRequest = channel.unary_unary(
                '/Warp/ProcessTransferOpRequest',
                request_serializer=warp__pb2.TransferOpRequest.SerializeToString,
                response_deserializer=warp__pb2.VoidType.FromString,
                _registered_method=True)
        self.PauseTransferOp = channel.unary_unary(
                '/Warp/PauseTransferOp',
                request_serializer=warp__pb2.OpInfo.SerializeToString,
                response_deserializer=warp__pb2.VoidType.FromString,
                _registered_method=True)
        self.StartTransfer = channel.unary_stream(
                '/Warp/StartTransfer',
                request_serializer=warp__pb2.OpInfo.SerializeToString,
                response_deserializer=warp__pb2.FileChunk.FromString,
                _registered_method=True)
        self.CancelTransferOpRequest = channel.unary_unary(
                '/Warp/CancelTransferOpRequest',
                request_serializer=warp__pb2.OpInfo.SerializeToString,
                response_deserializer=warp__pb2.VoidType.FromString,
                _registered_method=True)
        self.StopTransfer = channel.unary_unary(
                '/Warp/StopTransfer',
                request_serializer=warp__pb2.StopInfo.SerializeToString,
                response_deserializer=warp__pb2.VoidType.FromString,
                _registered_method=True)
        self.Ping = channel.unary_unary(
                '/Warp/Ping',
                request_serializer=warp__pb2.LookupName.SerializeToString,
                response_deserializer=warp__pb2.VoidType.FromString,
                _registered_method=True)


class WarpServicer(object):
    """************ Important! ***************

    If you change anything here, you *must* run 'generate-protobuf' to update the
    generated stub files.

    Never change the existing members and member values of messages, only add new ones.

    """

    def CheckDuplexConnection(self, request, context):
        """Sender methods
        api v1 duplex method (ping style)
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def WaitingForDuplex(self, request, context):
        """api v2 duplex method (block/future)
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetRemoteMachineInfo(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetRemoteMachineAvatar(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ProcessTransferOpRequest(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def PauseTransferOp(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StartTransfer(self, request, context):
        """Receiver methods
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def CancelTransferOpRequest(self, request, context):
        """Both
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StopTransfer(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Ping(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_WarpServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'CheckDuplexConnection': grpc.unary_unary_rpc_method_handler(
                    servicer.CheckDuplexConnection,
                    request_deserializer=warp__pb2.LookupName.FromString,
                    response_serializer=warp__pb2.HaveDuplex.SerializeToString,
            ),
            'WaitingForDuplex': grpc.unary_unary_rpc_method_handler(
                    servicer.WaitingForDuplex,
                    request_deserializer=warp__pb2.LookupName.FromString,
                    response_serializer=warp__pb2.HaveDuplex.SerializeToString,
            ),
            'GetRemoteMachineInfo': grpc.unary_unary_rpc_method_handler(
                    servicer.GetRemoteMachineInfo,
                    request_deserializer=warp__pb2.LookupName.FromString,
                    response_serializer=warp__pb2.RemoteMachineInfo.SerializeToString,
            ),
            'GetRemoteMachineAvatar': grpc.unary_stream_rpc_method_handler(
                    servicer.GetRemoteMachineAvatar,
                    request_deserializer=warp__pb2.LookupName.FromString,
                    response_serializer=warp__pb2.RemoteMachineAvatar.SerializeToString,
            ),
            'ProcessTransferOpRequest': grpc.unary_unary_rpc_method_handler(
                    servicer.ProcessTransferOpRequest,
                    request_deserializer=warp__pb2.TransferOpRequest.FromString,
                    response_serializer=warp__pb2.VoidType.SerializeToString,
            ),
            'PauseTransferOp': grpc.unary_unary_rpc_method_handler(
                    servicer.PauseTransferOp,
                    request_deserializer=warp__pb2.OpInfo.FromString,
                    response_serializer=warp__pb2.VoidType.SerializeToString,
            ),
            'StartTransfer': grpc.unary_stream_rpc_method_handler(
                    servicer.StartTransfer,
                    request_deserializer=warp__pb2.OpInfo.FromString,
                    response_serializer=warp__pb2.FileChunk.SerializeToString,
            ),
            'CancelTransferOpRequest': grpc.unary_unary_rpc_method_handler(
                    servicer.CancelTransferOpRequest,
                    request_deserializer=warp__pb2.OpInfo.FromString,
                    response_serializer=warp__pb2.VoidType.SerializeToString,
            ),
            'StopTransfer': grpc.unary_unary_rpc_method_handler(
                    servicer.StopTransfer,
                    request_deserializer=warp__pb2.StopInfo.FromString,
                    response_serializer=warp__pb2.VoidType.SerializeToString,
            ),
            'Ping': grpc.unary_unary_rpc_method_handler(
                    servicer.Ping,
                    request_deserializer=warp__pb2.LookupName.FromString,
                    response_serializer=warp__pb2.VoidType.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Warp', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('Warp', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class Warp(object):
    """************ Important! ***************

    If you change anything here, you *must* run 'generate-protobuf' to update the
    generated stub files.

    Never change the existing members and member values of messages, only add new ones.

    """

    @staticmethod
    def CheckDuplexConnection(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/CheckDuplexConnection',
            warp__pb2.LookupName.SerializeToString,
            warp__pb2.HaveDuplex.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def WaitingForDuplex(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/WaitingForDuplex',
            warp__pb2.LookupName.SerializeToString,
            warp__pb2.HaveDuplex.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetRemoteMachineInfo(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/GetRemoteMachineInfo',
            warp__pb2.LookupName.SerializeToString,
            warp__pb2.RemoteMachineInfo.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetRemoteMachineAvatar(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(
            request,
            target,
            '/Warp/GetRemoteMachineAvatar',
            warp__pb2.LookupName.SerializeToString,
            warp__pb2.RemoteMachineAvatar.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def ProcessTransferOpRequest(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/ProcessTransferOpRequest',
            warp__pb2.TransferOpRequest.SerializeToString,
            warp__pb2.VoidType.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def PauseTransferOp(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/PauseTransferOp',
            warp__pb2.OpInfo.SerializeToString,
            warp__pb2.VoidType.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def StartTransfer(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(
            request,
            target,
            '/Warp/StartTransfer',
            warp__pb2.OpInfo.SerializeToString,
            warp__pb2.FileChunk.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def CancelTransferOpRequest(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/CancelTransferOpRequest',
            warp__pb2.OpInfo.SerializeToString,
            warp__pb2.VoidType.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def StopTransfer(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/StopTransfer',
            warp__pb2.StopInfo.SerializeToString,
            warp__pb2.VoidType.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def Ping(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/Warp/Ping',
            warp__pb2.LookupName.SerializeToString,
            warp__pb2.VoidType.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)


class WarpRegistrationStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.RequestCertificate = channel.unary_unary(
                '/WarpRegistration/RequestCertificate',
                request_serializer=warp__pb2.RegRequest.SerializeToString,
                response_deserializer=warp__pb2.RegResponse.FromString,
                _registered_method=True)
        self.RegisterService = channel.unary_unary(
                '/WarpRegistration/RegisterService',
                request_serializer=warp__pb2.ServiceRegistration.SerializeToString,
                response_deserializer=warp__pb2.ServiceRegistration.FromString,
                _registered_method=True)


class WarpRegistrationServicer(object):
    """Missing associated documentation comment in .proto file."""

    def RequestCertificate(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RegisterService(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_WarpRegistrationServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'RequestCertificate': grpc.unary_unary_rpc_method_handler(
                    servicer.RequestCertificate,
                    request_deserializer=warp__pb2.RegRequest.FromString,
                    response_serializer=warp__pb2.RegResponse.SerializeToString,
            ),
            'RegisterService': grpc.unary_unary_rpc_method_handler(
                    servicer.RegisterService,
                    request_deserializer=warp__pb2.ServiceRegistration.FromString,
                    response_serializer=warp__pb2.ServiceRegistration.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'WarpRegistration', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('WarpRegistration', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class WarpRegistration(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def RequestCertificate(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/WarpRegistration/RequestCertificate',
            warp__pb2.RegRequest.SerializeToString,
            warp__pb2.RegResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def RegisterService(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/WarpRegistration/RegisterService',
            warp__pb2.ServiceRegistration.SerializeToString,
            warp__pb2.ServiceRegistration.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
