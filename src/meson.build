pyconf = configuration_data()
pyconf.set('prefix', get_option('prefix'))
pyconf.set('datadir', get_option('datadir'))
pyconf.set('pkgdatadir', install_datadir)
pyconf.set('libexecdir', install_libdir)
pyconf.set('libdir', get_option('libdir'))
pyconf.set('PACKAGE', meson.project_name())
pyconf.set('VERSION', meson.project_version())
pyconf.set('GETTEXT_PACKAGE', meson.project_name())

config_py = configure_file(
  output: 'config.py',
  input: 'config.py.in',
  configuration: pyconf
)

libexec_py = [
  config_py,
  'prefs.py',
  'util.py',
  'warp.py',
]

install_data(libexec_py,
  install_dir: install_libdir
)

data = [
  'warp-window.ui',
]

install_data(data,
  install_dir: install_datadir
)

meson.add_install_script('sh', '-c',
    'mkdir -p "@0@"'.format(install_bindir))

meson.add_install_script('sh', '-c',
    'ln -sf "@0@" "@1@"'.format((join_paths(install_libdir, 'warp.py')),
                                (join_paths(install_bindir, 'warp'))))

meson.add_install_script('sh', '-c', 'python3 -m compileall "@0@"'.format(install_libdir))
