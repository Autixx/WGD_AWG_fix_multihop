Thats my fork for WGDashboard with couple of features - AWG2.0 support, easy-to-route connection destination (such 3x-ui has) and multihop with balancers support.
Original project: [https://wg.wgdashboard.dev/](https://wg.wgdashboard.dev/)

## Ubuntu 22.04 / 24.04 installer

Run on a clean VPS:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/Autixx/WGD_AWG_fix_multihop.git
cd WGD_AWG_fix_multihop
sudo bash scripts/install_ubuntu.sh
```

One-command deploy with ready inbound `wg0` (keys + NAT + interface up):

```bash
sudo bash scripts/install_ubuntu.sh --bootstrap-inbound wg0
```

Example for AWG inbound:

```bash
sudo bash scripts/install_ubuntu.sh --bootstrap-inbound awg0 --bootstrap-protocol awg --bootstrap-listen-port 51820
```

After install:

```bash
systemctl status wg-dashboard.service --no-pager
journalctl -u wg-dashboard.service -f
```
