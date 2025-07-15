pyconf = configuration_data()
pyconf.set('prefix', get_option('prefix'))
pyconf.set('datadir', get_option('datadir'))
pyconf.set('pkgdatadir', install_datadir)
pyconf.set('libexecdir', install_libdir)
pyconf.set('libdir', get_option('libdir'))
pyconf.set('PACKAGE', meson.project_name())
pyconf.set('VERSION', meson.project_version())
pyconf.set('gettext_package', gettext_package)
pyconf.set('locale_dir', locale_dir)
pyconf.set('include_firewall_mod', include_firewall_mod)
pyconf.set('bundle_zeroconf', bundle_zeroconf)
pyconf.set('bundle_grpc', bundle_grpc)
pyconf.set('flatpak_build', get_option('flatpak-build'))
pyconf.set_quoted('RPC_API_VERSION', RPC_API_VERSION)

config_py = configure_file(
  output: 'config.py',
  input: 'config.py.in',
  configuration: pyconf
)

libexec_py = [
  config_py,
  'auth.py',
  'dbus_service.py',
  'interceptors.py',
  'misc.py',
  'networkmonitor.py',
  'notifications.py',
  'ops.py',
  'prefs.py',
  'remote.py',
  'remote_registration.py',
  'server.py',
  'transfers.py',
  'util.py',
  'warp_pb2.py',
  'warp_pb2_grpc.py',
  'warpinator.py',
]

install_data(libexec_py,
  install_dir: install_libdir
)

install_data(
    'warpinator-launch.py',
    install_dir: install_libdir,
    install_mode: 'rwxr-xr-x'
)

if include_firewall_mod
    subdir('firewall')
endif


install_libdir = join_paths(get_option('prefix'), get_option('libexecdir'), 'warpinator')
install_bindir = join_paths(get_option('prefix'), get_option('bindir'))

meson_source_root = meson.current_source_dir()


if bundle_grpc
    dependency('python3')
    current_grpc_version = '1.73.1'
    current_protobuf_version = '6.31.1'
    current_zeroconf_version  = '0.115.2'

    setup = join_paths(meson_source_root, 'grpcio-' + current_grpc_version, 'build_script.py')

    grpc = custom_target('grpc_build',
        output: 'grpc',
        command: [setup, join_paths(meson_source_root, 'grpcio-' + current_grpc_version), join_paths(meson.current_build_dir(), 'grpc')],
        install: true,
        install_dir: install_libdir,
        build_by_default: true,
    )

    setup = join_paths(meson_source_root, 'protobuf-' + current_protobuf_version, 'build_script.py')

    grpc = custom_target('proto_build',
        output: 'google',
        command: [setup, join_paths(meson_source_root, 'protobuf-' + current_protobuf_version), join_paths(meson.current_build_dir(), 'google')],
        install: true,
        install_dir: install_libdir,
        build_by_default: true,
    )

    setup = join_paths(meson_source_root, 'zeroconf-' + current_zeroconf_version, 'build_script.py')

    grpc = custom_target('zeroconf_build',
        output: 'zeroconf',
        command: [setup, join_paths(meson_source_root, 'zeroconf-' + current_zeroconf_version), join_paths(meson.current_build_dir(), 'zeroconf')],
        install: true,
        install_dir: install_libdir,
        build_by_default: true,
    )
endif

if bundle_landlock
    install_subdir(
        'landlock',
        install_dir: join_paths(install_libdir, 'landlock'),
        strip_directory: true
    )
endif