load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")
load("@bazel_gazelle//:deps.bzl", "gazelle_dependencies", "go_repository")
load("@com_google_googleapis//:repository_rules.bzl", "switched_rules_by_language")
load("@io_bazel_rules_go//go:deps.bzl", "go_register_toolchains", "go_rules_dependencies")
load("@com_envoyproxy_protoc_gen_validate//bazel:repositories.bzl", "pgv_dependencies")

# go version for rules_go
GO_VERSION = "1.16.6"

def xds_dependency_imports(go_version = GO_VERSION):
    protobuf_deps()
    go_rules_dependencies()
    go_register_toolchains(go_version)
    gazelle_dependencies()
    pgv_dependencies()

    switched_rules_by_language(
        name = "com_google_googleapis_imports",
        cc = True,
        go = True,
        grpc = True,
        rules_override = {
            "py_proto_library": ["@com_github_cncf_xds//bazel:api_build_system.bzl", "",],
        },
    )

    go_repository(
        name = "com_github_iancoleman_strcase",
        importpath = "github.com/iancoleman/strcase",
        sum = "h1:ux/56T2xqZO/3cP1I2F86qpeoYPCOzk+KF/UH/Ar+lk=",
        version = "v0.0.0-20180726023541-3605ed457bf7",
    )

    go_repository(
        name = "com_github_spf13_afero",
        importpath = "github.com/spf13/afero",
        sum = "h1:8q6vk3hthlpb2SouZcnBVKboxWQWMDNF38bwholZrJc=",
        version = "v1.3.4",
    )

    go_repository(
        name = "com_github_lyft_protoc_gen_star",
        importpath = "github.com/lyft/protoc-gen-star",
        sum = "h1:sImehRT+p7lW9n6R7MQc5hVgzWGEkDVZU4AsBQ4Isu8=",
        version = "v0.5.1",
    )

    go_repository(
        name = "org_golang_google_grpc",
        build_file_proto_mode = "disable",
        importpath = "google.golang.org/grpc",
        sum = "h1:AGJ0Ih4mHjSeibYkFGh1dD9KJ/eOtZ93I6hoHhukQ5Q=",
        version = "v1.40.0",
    )

# Old name for backward compatibility.
# TODO(roth): Remove this once callers are migrated to the new name.
def udpa_dependency_imports(go_version = GO_VERSION):
  xds_dependency_imports(go_version=go_version)
