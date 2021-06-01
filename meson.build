project('warpinator', 'c', version: '1.2.0', meson_version: '>=0.45.0')

RPC_API_VERSION = '2'

i18n = import('i18n')
gettext_package = meson.project_name()
locale_dir = join_paths(get_option('prefix'), get_option('localedir'))

install_datadir = join_paths(get_option('prefix'), get_option('datadir'), 'warpinator')
install_libdir = join_paths(get_option('prefix'), get_option('libexecdir'), 'warpinator')
install_bindir = join_paths(get_option('prefix'), get_option('bindir'))

include_firewall_mod = get_option('include-firewall-mod')
bundle_zeroconf = get_option('bundle-zeroconf')

subdir('data')
subdir('src')
subdir('bin')
subdir('po')
subdir('resources')
subdir('install-scripts')
