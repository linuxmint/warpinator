project('warpinator', 'c', version: '1.7.0', meson_version: '>=0.47.0')

RPC_API_VERSION = '2'

i18n = import('i18n')
gettext_package = meson.project_name()
locale_dir = join_paths(get_option('prefix'), get_option('localedir'))

install_datadir = join_paths(get_option('prefix'), get_option('datadir'), 'warpinator')
install_libdir = join_paths(get_option('prefix'), get_option('libexecdir'), 'warpinator')
install_bindir = join_paths(get_option('prefix'), get_option('bindir'))

meson_source_root = meson.current_source_dir()

include_firewall_mod = get_option('include-firewall-mod')
bundle_zeroconf = get_option('bundle-zeroconf')
bundle_landlock = get_option('bundle-landlock')

# grpc 1.30.2 on ubuntu 22.04 is broken
pymod = import('python')
python3 = pymod.find_installation('python3')
bundle_grpc = python3.language_version().version_compare('3.10') and \
              get_option('bundle-grpc-with-py310') and \
              host_machine.cpu() == 'x86_64'

subdir('data')
subdir('src')
subdir('bin')
subdir('po')
subdir('resources')
subdir('install-scripts')

message('\n'.join(['',
'',
'    @0@-@1@'.format(meson.project_name(), meson.project_version()),
'',
'    prefix:                 @0@'.format(get_option('prefix')),
'    source code location:   @0@'.format(meson_source_root),
'',
'    building for flatpak:   @0@'.format(get_option('flatpak-build')),
'    including ufw script:   @0@'.format(include_firewall_mod),
'    bundling zeroconf:      @0@'.format(bundle_zeroconf and not get_option('flatpak-build')),
'    bundling landlock:      @0@'.format(bundle_landlock),
'    bundling grpc:          @0@'.format(bundle_grpc),
'',
]))
