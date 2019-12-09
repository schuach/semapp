import pickle
from sys import argv, exit
import urllib.parse

import requests
import easygui

# config for api-key -- DO NOT PUT THIS FILE UNDER VERSION CONTROL!
import config.config as config

# get api-key from config
api_key = config.keys["Sandbox"]

# api-url-templates
base_url = 'https://api-eu.hosted.exlibrisgroup.com/almaws/v1'
barcode_api = base_url + "/items?item_barcode={barcode}"

session = requests.Session()
session.headers.update({
    "accept": "application/json",
    "authorization": f"apikey {api_key}",
})

semapps_path = "config/semapps.pickle"

def create_semapp(semapps):
    """Ask for new course reserve, return an updated list."""
    semapps = semapps
    title = "SEMAPP"
    msg = "Bitte Namen für den neuen Semesterhandapparat eingeben!"
    new_semapp = ""

    while not new_semapp:
        new_semapp = easygui.enterbox(msg, title).strip()

        # prüfen, ob der Name mit einem Großbuchstaben beginnt. Wenn nicht,
        # nächster Versuch
        if new_semapp[0].islower():
            easygui.msgbox("Der Name des Semesterhandapparates muss mit einem Großbuchstaben beginnen.")
            new_semapp = ""
            continue

        if new_semapp:
            if new_semapp in semapps:
                # Wenn ein Apparat dieses Namens schon vorhanden ist, nichts tun
                easygui.msgbox(f'Apparat "{new_semapp}" ist bereits vorhanden!')
            else:
                # Neuen Apparat zur Liste hinzufügen
                confirm_msg = f'Neuen Semesterhandapparat "{new_semapp}" anlegen?'
                confirmation = easygui.ccbox(confirm_msg, title)
                if confirmation:
                    semapps.append(new_semapp)

    # pickle the new list
    pickle.dump(sorted(semapps), open(semapps_path, "wb"))
    return sorted(semapps)

def remove_semapp(semapps):
    semapps = semapps
    title = "SEMAPP"
    msg = "Welchen Handapparat möchten Sie aus der Liste ENTFERNEN?"
    semapp_to_remove = easygui.choicebox(msg, title, semapps).strip()

    confirm_msg = f'Wollen Sie wirklich den Apparat "{semapp_to_remove}" aus der Liste ENTFERNEN?'
    confirmation = easygui.ccbox(confirm_msg, title)
    if confirmation:
        semapps.remove(semapp_to_remove)
        # pickle the new list
        pickle.dump(sorted(semapps), open(semapps_path, "wb"))

    return sorted(semapps)

def choose_semapp(semapps):
    msg = "Bitte wählen Sie aus, zu welchen Semesterhandapparat Sie Exemplare hinzufügen möchten."
    title = "SEMAPP"
    choices = (["*** Neuen Semesterhandapparat anlegen ***"]
               + semapps
               + ["*** Einen Semesterhandapparat aus der Liste entfernen ***"])

    choice = easygui.choicebox(msg, title, choices)

    if choice == choices[0]:
        choose_semapp(create_semapp(semapps))
    elif choice == choices[-1]:
        choose_semapp(remove_semapp(semapps))
    else:
        return choice

def get_user_input(semapp):
    """Get Barcode and temporary call number from user."""

    msg = f'Exemplar zu Semapp "{semapp}" hinzufügen.'

    try:
        count, barcode = easygui.multenterbox(msg=msg,
                                                title="SEMAPP",
                                                fields=["Laufende Nummer", "Barcode"])
    except:
        return None, None

    return barcode.strip(), count.strip()

def move_to_semapp(barcode, semapp, count):
    try:
        item = session.get(barcode_api.format(barcode=urllib.parse.quote_plus(barcode)))
        item.raise_for_status()
    except requests.exceptions.HTTPError as err:
        easygui.msgbox(msg=f"Ein Fehler ist aufgetreten. Stimmt der Barcode {barcode}?")
        exit(1)

    ij = item.json()
    if ij["holding_data"]["in_temp_location"]:
        easygui.msgbox(f"Exemplar {barcode} ist bereits an einem temporären Standort.")
        return

    # change the values in the item
    ij["holding_data"]["in_temp_location"] = True
    ij["holding_data"]["temp_library"] = {"value": "BHB", "desc": "Hauptbibliothek"}
    ij["holding_data"]["temp_location"] = {'value': 'SEMAP', 'desc': 'Semesterhandapparat'}
    ij["holding_data"]["temp_call_number_type"] = {'value': '8', 'desc': 'Other scheme'}
    if count:
        ij["holding_data"]["temp_call_number"] = semapp + f"/{count}"
    else:
        ij["holding_data"]["temp_call_number"] = semapp

    # PUT the changed item
    try:
        put_res = session.put(ij["link"], json=ij)
        put_res.raise_for_status
    except requests.exceptions.HTTPError as err:
        easygui.msgbox(msg=f"Ein Fehler ist aufgetreten. Bitte kontrollieren sie das Item im System!")
        exit(1)

def main():

    # Liste der Semapps holen, oder wenn leer, anlegen
    try:
        semapps = pickle.load(open(semapps_path, "rb"))
    except FileNotFoundError:
        semapps = create_semapp([])

    # die Benutzerin nach dem Semapp fragen
    if len(semapps) > 0:
        semapp = choose_semapp(semapps)
    else:
        semapps = create_semapp(semapps)
        semapp = choose_semapp(semapps)

    # beenden, falls auf cancel geklickt wird
    if semapp is None:
        exit(0)

    # Main loop
    while True:
        barcode, count = get_user_input(semapp)

        if barcode:
            move_to_semapp(barcode, semapp, count)
        else:
            exit(0)

if __name__ == "__main__":
    main()
