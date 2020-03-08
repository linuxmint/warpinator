import grpc
import rpc_fallbacks
import util

class client_interceptor(grpc.UnaryStreamClientInterceptor):
    def __init__(self):
        pass

    def intercept_unary_stream(self, continuation, client_call_details, request):
        response_iterator = continuation(client_call_details, request)

        if client_call_details.method == "/Warp/GetRemoteMachineAvatar":
            return self.handle_avatar(response_iterator)

        return response_iterator

    def handle_avatar(self, response_iterator):
        def process_stream(iterator):
            try:
                for avatar_chunk in response_iterator:
                    yield avatar_chunk
            except grpc.RpcError as e:
                print("Could not fetch remote avatar, using a generic one. (%s, %s)" % (e.code(), e.details()))
                for avatar_chunk in rpc_fallbacks.default_avatar_iterator():
                    yield avatar_chunk

        return process_stream(response_iterator)

