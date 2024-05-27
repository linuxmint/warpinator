prefix_info = configuration_data()
prefix_info.set('install_libdir', install_libdir)

bin_file = configure_file(
  input : 'warpinator.in',
  output: 'warpinator',
  configuration: prefix_info,
)

install_data(
    bin_file,
    install_dir: get_option('bindir'),
    install_mode: 'rwxr-xr-x'
)

# This is only useful if installed in the system's bindir
if not get_option('flatpak-build')
    send_bin_file = configure_file(
      input : 'warpinator-send.in',
      output: 'warpinator-send',
      configuration: prefix_info,
    )

    install_data(
        send_bin_file,
        install_dir: get_option('bindir'),
        install_mode: 'rwxr-xr-x'
    )
endif