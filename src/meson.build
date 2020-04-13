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

config_py = configure_file(
  output: 'config.py',
  input: 'config.py.in',
  configuration: pyconf
)

# I should be able to generated the protobuf files with custom_target() but I can't install_data()
# with them.  I may be mistaken.
meson.add_install_script(
    join_paths(meson.source_root(), 'install-scripts', 'meson_generate_and_install_protobuf_files.py'),
    meson.current_source_dir(),
    'warp.proto')

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
  'warpinator.py'
]

install_data(libexec_py,
  install_dir: install_libdir
)
