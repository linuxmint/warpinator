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

config_py = configure_file(
  output: 'config.py',
  input: 'config.py.in',
  configuration: pyconf
)

libexec_py = [
  config_py,
  'auth.py',
  'notifications.py',
  'ops.py',
  'prefs.py',
  'remote.py',
  'server.py',
  'transfers.py',
  'util.py',
  'warpinator.py',
  'warp_pb2.py',
  'warp_pb2_grpc.py',
  'wrappers.py'
]

install_data(libexec_py,
  install_dir: install_libdir
)

if include_firewall_mod
    subdir('firewall')
endif
