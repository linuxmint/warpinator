project('warp', 'c', version: '0.0.1', meson_version: '>=0.45.0')


install_datadir = join_paths(get_option('prefix'), get_option('datadir'), 'warp')
install_libdir = join_paths(get_option('prefix'), get_option('libexecdir'), 'warp')
install_bindir = join_paths(get_option('prefix'), get_option('bindir'))

subdir('data')
subdir('src')
subdir('bin')
subdir('install-scripts')
