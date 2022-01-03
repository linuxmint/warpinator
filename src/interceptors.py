#!/usr/bin/python3

import zlib
import grpc
import logging

import prefs
import util

class StreamReponseWrapper():
    def __init__(self, response):
        self.response = response

    def __iter__(self):
        return self

    def __next__(self):
        chunk = self.response.__next__()

        try:
            if not chunk.chunk:
                return chunk
            else:
                dcchunk = zlib.decompress(chunk.chunk)
                chunk.chunk = dcchunk
                return chunk
        except Exception as e:
            logging.warning("Decompression error: %s" % e)
            # this will go to remote.start_transfer_op()'s handler.
            raise

    # Future
    def cancel(self):
        self.response.cancel()

class ChunkDecompressor(grpc.UnaryStreamClientInterceptor):
    def __init__(self):
        pass

    # Intercept the RPC response after it returns from the server but before it reaches
    # the remote.
    def intercept_unary_stream(self, continuation, client_call_details, request):
        # Only intercept transfer ops.
        if client_call_details.method != "/Warp/StartTransfer":
            return continuation(client_call_details, request)

        try:
            use_comp = request.use_compression
        except AttributeError:
            use_comp = False

        logging.debug("Transfer using compression: %d" % use_comp)

        # When always need to return the original response along with
        # whatever the remote will be iterating over. If there's no
        # compression, we just return the same response twice.
        if not use_comp:
            return continuation(client_call_details, request)

        return StreamReponseWrapper(continuation(client_call_details, request))

def _wrap_rpc_behavior(handler, fn):
        if handler is None:
            return None

        if not handler.request_streaming and handler.response_streaming:
            behavior_fn = handler.unary_stream
            handler_factory = grpc.unary_stream_rpc_method_handler

        elif handler.request_streaming and handler.response_streaming:
            behavior_fn = handler.stream_stream
            handler_factory = grpc.stream_stream_rpc_method_handler
        elif handler.request_streaming and not handler.response_streaming:
            behavior_fn = handler.stream_unary
            handler_factory = grpc.stream_unary_rpc_method_handler
        else:
            behavior_fn = handler.unary_unary
            handler_factory = grpc.unary_unary_rpc_method_handler
        return handler_factory(fn(behavior_fn,
                                  handler.request_streaming,
                                  handler.response_streaming),
                               request_deserializer=handler.request_deserializer,
                               response_serializer=handler.response_serializer)

class ChunkCompressor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        # Only intercept transfer ops.
        if handler_call_details.method != "/Warp/StartTransfer":
            return continuation(handler_call_details)

        # Intercept the RPC response and compress it on its way back to the remote client
        # if enabled, otherwise send the original response unchanged.
        def compression_wrapper(behavior, request_streaming, response_streaming):
            def replacement_handler(request_or_iterator, servicer_context):
                # We (the sender) expressed our compression preference in ProcessTransferOpRequest
                # The receiver is telling us here the result of our pref and their pref so we end
                # up agreeing. An exception here means the receiver doesn't support this at all.

                # Incoming message from the remote client (request).
                try:
                    use_comp = request_or_iterator.use_compression
                except AttributeError:
                    use_comp = False

                logging.debug("Transfer using compression: %d" % use_comp)

                if not use_comp:
                    return behavior(request_or_iterator, servicer_context)

                # Compression level is only specified during compression.
                comp_level = prefs.get_compression_level()
                response = behavior(request_or_iterator, servicer_context)

                # Outgoing response goes thru compressor() before it gets sent back to the remote client.
                def compressor(response):
                    # chunks are warp_pb2.FileChunks
                    for chunk in response:
                        try:
                            if not chunk.chunk:
                                # Directory or symlink, or file terminator block.
                                yield chunk
                            else:
                                chunk.chunk = zlib.compress(chunk.chunk, level=comp_level)
                                yield chunk
                        except Exception as e:
                            logging.warning("Compression error: %s" % e)
                            servicer_context.abort(code=grpc.StatusCode.DATA_LOSS, details='Something went wrong with data compression: %s' % e)

                return compressor(response)

            return replacement_handler
        return _wrap_rpc_behavior(continuation(handler_call_details), compression_wrapper)
