import grpc
import rpc_fallbacks

class client_interceptor(grpc.UnaryStreamClientInterceptor):
    def __init__(self):
        pass

    # This 'intercepts' any outgoing unary->stream rpc call
    def intercept_unary_stream(self, continuation, client_call_details, request):
        # We let the call continue to the server, and receive the iterator back.
        response_iterator = continuation(client_call_details, request)

        # See if it's a method we're interested in
        if client_call_details.method == "/Warp/GetRemoteMachineAvatar":
            return self.handle_avatar(response_iterator)

        # Pass it unmodified if not.
        return response_iterator

    def handle_avatar(self, response_iterator):
        # We've got the response from the server.  This is a generator of file
        # chunks.

        def process_stream(iterator):
            """ We wrap it in our own generator that lets us operate on it as we go.
                We need to attempt to iterate thru the original response because that's
                the only way we'll get the .abort exception (see GetRemoteMachineAvatar).
                If we get it, we catch it, and return our fallback generator in its place.
                Otherwise, we just let our wrapper run its course. """

            try:
                for avatar_chunk in response_iterator:
                    yield avatar_chunk
            except grpc.RpcError as e:
                print("Could not fetch remote avatar, using a generic one. (%s, %s)" % (e.code(), e.details()))
                for avatar_chunk in rpc_fallbacks.default_avatar_iterator():
                    yield avatar_chunk

        return process_stream(response_iterator)

