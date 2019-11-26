import keyring
import urllib.parse
# import pymarc
import xml.etree.ElementTree as ET
from sys import argv

import requests
import easygui

# Kommandozeilenargumente checken und system festlegen
if len(argv) == 1:
    key = "BIB-Sandbox"
    print("!    Zugriff auf Sandbox")
elif len(argv) == 2:
    if argv[1] == "prod":
        key = "BIB-Produktion"
        print("!!!ACHTUNG!!!\nZugriff aufs Produktionssystem!")
    elif argv[1] == "sb":
        print("!    Zugriff auf Sandbox")
        key = "BIB-Sandbox"
    else:
        print("""!    Falscher Wert für System.
!    Mögliche Werte:
!    prod -> Produktionssystem
!    sb -> Sandbox
!    Script wird mit Zugriff auf die Sandbox ausgeführt.""")
        key = "BIB-Sandbox"
else:
    print("""!   Falsche Anzahl an Argumenten. Benutzung dieses Scripts:
!   $ python3 -i boilerplate.py [prod|sb]
!   Script wird mit Zugriff auf die Sandbox ausgeführt.""")
    key = "BIB-Sandbox"

# store api key in system keyring
api_key = keyring.get_password("ALMA-API", key).rstrip()

# api-url-templates
base_url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1'
barcode_api = base_url + "/items?item_barcode={barcode}"
holdings_api = base_url + "/bibs/{mms_id}/holdings"
bib_api = base_url + "/bibs/{mms_id}"
item_api = base_url + "/bibs/{mms_id}/holdings/{holding_id}/items"

session = requests.Session()
session.headers.update({
    "accept": "application/json",
    "authorization": f"apikey {api_key}",
})

def get_user_input(msg=""):
    """Get Barcode and temporary call number from user."""

    if not msg:
        msg = "Bitte folgende Daten eingeben."
    else:
        msg = msg

    try:
        temp_cn, barcode = easygui.multenterbox(msg=msg,
                                                title="SEMAPP",
                                                fields=["Temporäre Signatur", "Barcode"])
    except:
        return None, None

    return barcode.strip(), temp_cn.strip()

def set_to_semapp(barcode, temp_cn):
    try:
        item = session.get(barcode_api.format(barcode=urllib.parse.quote_plus(barcode)))
        item.raise_for_status()
        print(item.text)
    except requests.exceptions.HTTPError as err:
        print(err)
        easygui.msgbox(msg=f"Ein Fehler ist aufgetreten. Stimmt der Barcode {barcode}?")
        quit()

    ij = item.json()

    # change the values in the item
    ij["holding_data"]["in_temp_location"] = True
    ij["holding_data"]["temp_library"] = {"value": "BHB", "desc": "Hauptbibliothek"}
    ij["holding_data"]["temp_location"] = {'value': 'SEMAP', 'desc': 'Semesterhandapparat'}
    ij["holding_data"]["temp_call_number_type"] = {'value': '8', 'desc': 'Other scheme'}
    ij["holding_data"]["temp_call_number"] = temp_cn

    # PUT the changed item
    try:
        put_res = session.put(ij["link"], json=ij)
        put_res.raise_for_status
    except requests.exceptions.HTTPError as err:
        print(err)
        easygui.msgbox(msg=f"Ein Fehler ist aufgetreten. Bitte kontrollieren sie das Item im System!")
        quit()

# main loop
while True:
    barcode, temp_cn = get_user_input()

    if not barcode:
        quit()
    else:
        set_to_semapp(barcode, temp_cn)
