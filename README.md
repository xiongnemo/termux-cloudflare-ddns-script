# termux-cloudflare-ddns-script

A script using Cloudflare as a DDNS provider, for use with Python 3 on Termux. Only supports IPv6.

## Prerequisites

* Termux
* A working IPv6 address
* Python 3, curl

```zsh
apt install python curl
```

You may want to use GNU screen.

```zsh
apt install screen
```

Then, install Python packages

```zsh
pip install requests cloudflare
```

## Usage

Download:

```zsh
git clone https://github.com/xiongnemo/termux-cloudflare-ddns-script && cd termux-cloudflare-ddns-script && chmod +x ./ddns-v6.py
```

Run:

```zsh
./ddns-v6.py -a <Cloudflare API Key> -z <zone/domain name> -s <subdomain name>
```

or

```zsh
./ddns-v6.py --API_KEY=<Cloudflare API Key> --ZONE=<zone/domain name> --SUBDOMAIN=<subdomain name>
```

It will update your IPv6 address based on a 300 seconds interval. If you don't have a public IPv6 address at the time it tries to update, it will skip to next loop.

## Credits

[oznu/docker-cloudflare-ddns](https://github.com/oznu/docker-cloudflare-ddns) for original thoughts

[Cloudflare](https://github.com/cloudflare/python-cloudflare) for their splendid API, service and package
