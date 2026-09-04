# Reticulum config for the node. Rendered by `planetai reticulum` into config/reticulum/config.
# Interfaces:
#   TCP server: Sideband, NomadNet or another node connects here over the LAN or the tailnet. Always on.
#   RNode:      a LoRa radio on USB. Commented out: needs the device passed into the container (Linux only;
#               macOS Docker cannot see USB serial) and the frequency for your region.
[reticulum]
  enable_transport = No
  share_instance = Yes
  shared_instance_port = 37428
  instance_control_port = 37429
  panic_on_interface_error = No

[logging]
  loglevel = 3

[interfaces]
  [[TCP Server]]
    type = TCPServerInterface
    enabled = yes
    listen_ip = 0.0.0.0
    listen_port = 4242

  # [[RNode LoRa]]
  #   type = RNodeInterface
  #   enabled = yes
  #   port = /dev/ttyACM0
  #   frequency = 923000000        # AS923 (Bali / SE Asia) · 868000000 EU · 915000000 US. Match local law.
  #   bandwidth = 125000
  #   txpower = 17
  #   spreadingfactor = 8
  #   codingrate = 5
