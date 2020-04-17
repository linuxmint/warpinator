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

merged_file = i18n.merge_file(
    input: 'org.x.warpinator.policy.in.in',
    output: 'org.x.warpinator.policy',
    type: 'xml',
    po_dir: join_paths(meson.source_root(), 'po'),
    install_dir: join_paths(get_option('datadir'), 'polkit-1', 'actions'),
    install: true,
)

##### How can we i18n and configure a file?  (.in.in -> .in -> final file)
##### I'm unable to let the build set the libexec location, as the input files
##### are checked at runtime.  Or I'm missing something.
# policyConf = configuration_data()
# policyConf.set('libexecdir', install_libdir)

# rootPolicyFile = configure_file(
#   input : org.x.warpinator.policy.in,
#   output: 'org.x.warpinator.policy',
#   configuration: policyConf,
# )

# install_data(rootPolicyFile,
#   install_dir: join_paths(get_option('datadir'), 'polkit-1', 'actions')
# )
