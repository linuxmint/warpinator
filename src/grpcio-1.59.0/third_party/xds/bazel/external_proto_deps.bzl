# Any external dependency imported in the xds/ .protos requires entries in
# the maps below, to allow the Bazel proto and language specific bindings to be
# inferred from the import directives.
#
# This file needs to be interpreted as both Python 3 and Starlark, so only the
# common subset of Python should be used.

# This maps from .proto import directive path to the Bazel dependency path for
# external dependencies. Since BUILD files are generated, this is the canonical
# place to define this mapping.
EXTERNAL_PROTO_IMPORT_BAZEL_DEP_MAP = {
    "google/api/expr/v1alpha1/checked.proto": "@com_google_googleapis//google/api/expr/v1alpha1:checked_proto",
    "google/api/expr/v1alpha1/syntax.proto": "@com_google_googleapis//google/api/expr/v1alpha1:syntax_proto",
}

# This maps from the Bazel proto_library target to the Go language binding target for external dependencies.
EXTERNAL_PROTO_GO_BAZEL_DEP_MAP = {
    # Note @com_google_googleapis are point to @go_googleapis.
    # This is done to address //test/build:go_build_test build error:
    #
    # link: package conflict error:
    #   google.golang.org/genproto/googleapis/api/annotations: multiple copies of package passed to linker:
    #
    # @go_googleapis//google/api:annotations_go_proto
    # @com_google_googleapis//google/api:annotations_go_proto
    #
    # TODO(https://github.com/bazelbuild/rules_go/issues/1986): update to
    #    @com_google_googleapis when the bug is resolved. Also see the note to
    #    go_googleapis in https://github.com/bazelbuild/rules_go/blob/master/go/dependencies.rst#overriding-dependencies
    "@com_google_googleapis//google/api/expr/v1alpha1:checked_proto": "@go_googleapis//google/api/expr/v1alpha1:expr_go_proto",
    "@com_google_googleapis//google/api/expr/v1alpha1:syntax_proto": "@go_googleapis//google/api/expr/v1alpha1:expr_go_proto",
}

# This maps from the Bazel proto_library target to the C++ language binding target for external dependencies.
EXTERNAL_PROTO_CC_BAZEL_DEP_MAP = {
    "@com_google_googleapis//google/api/expr/v1alpha1:checked_proto": "@com_google_googleapis//google/api/expr/v1alpha1:checked_cc_proto",
    "@com_google_googleapis//google/api/expr/v1alpha1:syntax_proto": "@com_google_googleapis//google/api/expr/v1alpha1:syntax_cc_proto",
}

# This maps from the Bazel proto_library target to the Python language binding target for external dependencies.
EXTERNAL_PROTO_PY_BAZEL_DEP_MAP = {
    "@com_google_googleapis//google/api/expr/v1alpha1:checked_proto": "@com_google_googleapis//google/api/expr/v1alpha1:expr_py_proto",
    "@com_google_googleapis//google/api/expr/v1alpha1:syntax_proto": "@com_google_googleapis//google/api/expr/v1alpha1:expr_py_proto",
}
