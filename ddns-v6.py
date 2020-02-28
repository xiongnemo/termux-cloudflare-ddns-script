#!/data/data/com.termux/files/usr/bin/python
import os
import sys
import getopt
import requests
import json
import time
import CloudFlare

CF_API = "https://api.cloudflare.com/client/v4"
RRTYPE = "AAAA"


def verify_token(header: dict) -> bool:
    r = requests.get(CF_API + "/user/tokens/verify", headers=header)
    if r.status_code != 200:
        print(
            "----------------------------------------------------------------\n"
            "ERROR: Invalid CloudFlare Credentials - " +
            str(r.status_code) + "\n"
            "----------------------------------------------------------------\n"
            "Make sure the API_KEY is correct. You can\n"
            "get your scoped CloudFlare API Token here:\n"
            "https://dash.cloudflare.com/profile/api-tokens\n"
            "----------------------------------------------------------------\n"
        )
        return False
    return True


def verify_zone(header: dict, zone_name: str) -> str:
    r = requests.get(CF_API + "/zones?name=" + zone_name, headers=header)
    result = json.loads(r.text)
    if result['result']:
        return result['result'][0]['id']
    else:
        print(
            "----------------------------------------------------------------\n"
            "ERROR: Zone for " + zone_name + " was not found in your CloudFlare Account\n"
            "----------------------------------------------------------------\n"
            "Make sure the ZONE variable is correct and the domain exists\n"
            "in your CloudFlare account. You can add a new domain here:\n"
            "https://www.cloudflare.com/a/add-site\n"
            "----------------------------------------------------------------\n"
        )
        return ""


def verify_dns_record(header: dict, cf_zone_id: str, dns_name: str, zone_name: str) -> str:
    r = requests.get(CF_API + "/zones/" + cf_zone_id + "/dns_records?type=" + RRTYPE + "&name=" + dns_name,
                     headers=header)
    result = json.loads(r.text)
    if result['result']:
        print("Found existing record for " + dns_name + ".")
        return result['result'][0]['id']
    else:
        print(RRTYPE + " DNS record for " + dns_name +
              " was not found in " + zone_name + " zone.")
        return ""


def create_dns_record(header: dict, cf_zone_id: str, dns_name: str, ip_address: str) -> str:
    post_body = {
        'type': RRTYPE,
        'name': dns_name,
        'content': ip_address,
        "proxied": False,
        "ttl": 1
    }
    r = requests.post(CF_API + "/zones/" + cf_zone_id +
                      "/dns_records", data=post_body, headers=header)
    result = json.loads(r.text)
    return result['result']['id']


def do_dns_update(cf, zone_name, zone_id, dns_name, ip_address, ip_address_type):

    try:
        params = {'name': dns_name, 'match': 'all', 'type': ip_address_type}
        dns_records = cf.zones.dns_records.get(zone_id, params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones/dns_records %s - %d %s - api call failed' % (dns_name, e, e))
    updated = False

    for dns_record in dns_records:
        old_ip_address = dns_record['content']
        old_ip_address_type = dns_record['type']
        if ip_address_type not in ['A', 'AAAA']:
            continue
        if ip_address_type != old_ip_address_type:
            print('IGNORED: %s %s ; wrong address family' %
                  (dns_name, old_ip_address))
            continue

        if ip_address == old_ip_address:
            print('UNCHANGED: %s %s' % (dns_name, ip_address))
            updated = True
            continue

        proxied_state = dns_record['proxied']

        dns_record_id = dns_record['id']
        dns_record = {
            'name': dns_name,
            'type': ip_address_type,
            'content': ip_address,
            'proxied': proxied_state
        }
        try:
            dns_record = cf.zones.dns_records.put(
                zone_id, dns_record_id, data=dns_record)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            exit('/zones.dns_records.put %s - %d %s - api call failed' %
                 (dns_name, e, e))
        print('UPDATED: %s %s -> %s' % (dns_name, old_ip_address, ip_address))
        updated = True

    if updated:
        return

    dns_record = {
        'name': dns_name,
        'type': ip_address_type,
        'content': ip_address
    }
    try:
        dns_record = cf.zones.dns_records.post(zone_id, data=dns_record)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/zones.dns_records.post %s - %d %s - api call failed' %
             (dns_name, e, e))
    print('CREATED: %s %s' % (dns_name, ip_address))


def get_ipv6_address() -> str:
    ipv6_status = os.system("curl -sf6 https://ifconfig.co")
    if ipv6_status:
        print("This device don't have working public IPv6 address(es)!")
        return ""
    temp_ipv6_address_string = os.popen("curl -sf6 https://ifconfig.co").read()
    temp_ipv6_address_string = temp_ipv6_address_string[:-1]
    print("Your public IPv6 address is: " + temp_ipv6_address_string)
    return temp_ipv6_address_string


def show_help():
    print('Usage: ddns-v6.py -a <Cloudflare API Key> -z <zone/domain name> -s <subdomain name>')
    print('   or: ddns-v6.py --API_KEY=<Cloudflare API Key> --ZONE=<zone/domain name> --SUBDOMAIN=<subdomain name>')


def main(argv):
    api_key = ""
    zone_name = ""
    subdomain_name = ""

    try:
        opts, args = getopt.getopt(
            argv, "ha:z:s:", ["help", "API_KEY=", "ZONE=", "SUBDOMAIN="])
    except getopt.GetoptError:
        show_help()
        exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            show_help()
            sys.exit(1)
        elif opt in ("-a", "--API_KEY"):
            api_key = arg
        elif opt in ("-z", "--ZONE"):
            zone_name = arg
        elif opt in ("-s", "--SUBDOMAIN"):
            subdomain_name = arg
    if api_key == "" or zone_name == "" or subdomain_name == "":
        print("Missing options.")
        show_help()
        exit(3)

    ipv6_address_string = get_ipv6_address()
    if ipv6_address_string == "":
        exit(1)

    print('Your API_KEY is：' + api_key)
    print('Desired zone name is：' + zone_name)
    print('Desired subdomain name is：' + subdomain_name)
    cf_dns_record_name = subdomain_name + '.' + zone_name
    print('Expect to update AAAA record for: ' + cf_dns_record_name)

    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }

    if not verify_token(header):
        exit(4)
    cf_zone_id = verify_zone(header, zone_name)
    if cf_zone_id == "":
        exit(5)
    cf_dns_record_id = verify_dns_record(
        header, cf_zone_id, cf_dns_record_name, zone_name)
    if cf_dns_record_id == "":
        print("We will add new record for this name.")
    cf = CloudFlare.CloudFlare(token=api_key)
    do_dns_update(cf, zone_name, cf_zone_id, cf_dns_record_name,
                  ipv6_address_string, RRTYPE)
    while True:
        time.sleep(300)
        ipv6_address_string = get_ipv6_address()
        if ipv6_address_string == "":
            continue
        else:
            do_dns_update(cf, zone_name, cf_zone_id,
                          cf_dns_record_name, ipv6_address_string, RRTYPE)
    exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
