subdir('icons')

i18n.merge_file(
    input: 'warp-autostart.desktop.in',
    output: 'warp-autostart.desktop',
    type: 'desktop',
    po_dir: join_paths(meson.source_root(), 'po'),
    install: true,
    install_dir: join_paths(get_option('sysconfdir'), 'xdg', 'autostart')
)

i18n.merge_file(
    input: 'warp.desktop.in',
    output: 'warp.desktop',
    type: 'desktop',
    po_dir: join_paths(meson.source_root(), 'po'),
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

install_data('org.linuxmint.warp.gschema.xml',
    install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)
