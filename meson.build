project('warpinator', 'c', version: '0.0.1', meson_version: '>=0.45.0')

i18n = import('i18n')
gettext_package = meson.project_name()
locale_dir = join_paths(get_option('prefix'), get_option('localedir'))

install_datadir = join_paths(get_option('prefix'), get_option('datadir'), 'warpinator')
install_libdir = join_paths(get_option('prefix'), get_option('libexecdir'), 'warpinator')
install_bindir = join_paths(get_option('prefix'), get_option('bindir'))

subdir('data')
subdir('src')
subdir('bin')
subdir('po')
subdir('resources')
subdir('install-scripts')
