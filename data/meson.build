subdir('icons')

desktop_id = 'org.x.Warpinator'

desktop_conf = configuration_data()
desktop_conf.set('desktop_id', desktop_id)

i18n.merge_file(
    input: configure_file(
    input: 'org.x.Warpinator.desktop.in.in',
    output: 'org.x.Warpinator.desktop.in',
    configuration: desktop_conf
    ),
    output: '@0@.desktop'.format(desktop_id),
    type: 'desktop',
    po_dir: join_paths(meson_source_root, 'po'),
    install: true,
    install_dir: join_paths(get_option('datadir'), 'applications'),
)

install_data('warpinator-autostart.desktop',
    install_dir: join_paths(get_option('sysconfdir'), 'xdg', 'autostart')
)

install_data('org.x.Warpinator.gschema.xml',
    install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas')
)

if include_firewall_mod
    policyConf = configuration_data()
    policyConf.set('libexecdir', install_libdir)

    merged_file = i18n.merge_file(
        input: configure_file(
            input : 'org.x.warpinator.policy.in.in',
            output: 'org.x.warpinator.policy.in',
            configuration: policyConf,
        ),
        output: 'org.x.warpinator.policy',
        type: 'xml',
        po_dir: join_paths(meson_source_root, 'po'),
        install_dir: join_paths(get_option('datadir'), 'polkit-1', 'actions'),
        install: true,
    )
endif

current_date = run_command('sh', '-c', '''
      SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-`date +%s`}";
      FORMAT="+%Y-%m-%d";
      date -u -d @"$SOURCE_DATE_EPOCH" "$FORMAT" 2>/dev/null ||
      date -u -r  "$SOURCE_DATE_EPOCH" "$FORMAT" 2>/dev/null ||
      date -u "$FORMAT"''', check: false).stdout().strip()

appdata_conf = configuration_data()
appdata_conf.set('appid', desktop_id)
appdata_conf.set('app_version', meson.project_version())
appdata_conf.set('current_date', current_date)

appdata = i18n.merge_file(
    input: configure_file(
        input: files('org.x.Warpinator.appdata.xml.in.in'),
        output: 'org.x.Warpinator.appdata.xml.in',
        configuration: appdata_conf
    ),
    output: '@0@.appdata.xml'.format(desktop_id),
    type: 'xml',
    po_dir: join_paths(meson_source_root, 'po'),
    install_dir: join_paths(get_option('datadir'), 'metainfo'),
    install: true,
)

nemo_action = i18n.merge_file(
    input: 'warpinator-send.nemo_action.in',
    output: 'warpinator-send.nemo_action',
    type: 'desktop',
    po_dir: join_paths(meson_source_root, 'po'),
    install_dir: join_paths(get_option('datadir'), 'nemo', 'actions'),
    install: true,
)

install_data(
    'warpinator-send-check',
    install_dir: join_paths(get_option('datadir'), 'nemo', 'actions'),
    install_mode: 'rwxr-xr-x'
)