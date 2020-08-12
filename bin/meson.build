prefix_info = configuration_data()
prefix_info.set('prefix', get_option('prefix'))

bin_file = configure_file(
  input : 'warpinator.in',
  output: 'warpinator',
  configuration: prefix_info,
)

install_data(bin_file, install_dir: get_option('bindir'))
