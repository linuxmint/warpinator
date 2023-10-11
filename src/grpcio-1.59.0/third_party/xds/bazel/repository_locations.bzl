REPOSITORY_LOCATIONS = dict(
    bazel_gazelle = dict(
        sha256 = "62ca106be173579c0a167deb23358fdfe71ffa1e4cfdddf5582af26520f1c66f",
        urls = ["https://github.com/bazelbuild/bazel-gazelle/releases/download/v0.23.0/bazel-gazelle-v0.23.0.tar.gz"],
    ),
    bazel_skylib = dict(
        sha256 = "1c531376ac7e5a180e0237938a2536de0c54d93f5c278634818e0efc952dd56c",
        urls = ["https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/1.0.3/bazel-skylib-1.0.3.tar.gz"],
    ),
    com_envoyproxy_protoc_gen_validate = dict(
        sha256 = "c695fc5a2e5a1b52904cd8a58ce7a1c3a80f7f50719496fd606e551685c01101",
        strip_prefix = "protoc-gen-validate-0.6.1",
        urls = ["https://github.com/envoyproxy/protoc-gen-validate/archive/refs/tags/v0.6.1.tar.gz"],
    ),
    com_github_grpc_grpc = dict(
        sha256 = "13e7c6460cd979726e5b3b129bb01c34532f115883ac696a75eb7f1d6a9765ed",
        strip_prefix = "grpc-1.40.0",
        urls = ["https://github.com/grpc/grpc/archive/refs/tags/v1.40.0.tar.gz"],
    ),
    com_google_googleapis = dict(
        # TODO(dio): Consider writing a Skylark macro for importing Google API proto.
        sha256 = "9b4e0d0a04a217c06b426aefd03b82581a9510ca766d2d1c70e52bb2ad4a0703",
        strip_prefix = "googleapis-114a745b2841a044e98cdbb19358ed29fcf4a5f1",
        urls = ["https://github.com/googleapis/googleapis/archive/114a745b2841a044e98cdbb19358ed29fcf4a5f1.tar.gz"],
    ),
    com_google_protobuf = dict(
        sha256 = "52b6160ae9266630adb5e96a9fc645215336371a740e87d411bfb63ea2f268a0",
        strip_prefix = "protobuf-3.18.0",
        urls = ["https://github.com/protocolbuffers/protobuf/releases/download/v3.18.0/protobuf-all-3.18.0.tar.gz"],
    ),
    io_bazel_rules_go = dict(
        sha256 = "69de5c704a05ff37862f7e0f5534d4f479418afc21806c887db544a316f3cb6b",
        urls = ["https://github.com/bazelbuild/rules_go/releases/download/v0.27.0/rules_go-v0.27.0.tar.gz"],
    ),
)
