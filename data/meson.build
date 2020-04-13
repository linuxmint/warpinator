subdir('icons')

i18n.merge_file(
    input: 'warpinator.desktop.in',
    output: 'warpinator.desktop',
    type: 'desktop',
    po_dir: join_paths(meson.source_root(), 'po'),
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications')
)

install_data('warpinator-autostart.desktop',
    install_dir: join_paths(get_option('sysconfdir'), 'xdg', 'autostart')
)

install_data('org.x.warpinator.gschema.xml',
    install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)
