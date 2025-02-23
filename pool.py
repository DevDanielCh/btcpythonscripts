# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 17:03:38 2025
@author: ChangeMe
"""
import requests
import os
import subprocess
import time
import json
from datetime import datetime
from colorama import Fore, Style, init

API_URL = "https://bitcoinpuzzles.io/api/block"

CONFIG_FILE = "config.json"
IN_FILE = "in.txt"
OUT_FILE = "out.txt"

# Initialize colorama
init(autoreset=True)


def clear_screen():
    """Clears the terminal screen to provide a clean output view."""
    os.system("cls" if os.name == "nt" else "clear")


def load_config():
    """Carrega a configuração do arquivo JSON, ou cria uma nova se não existir."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    return {}


def save_config(config):
    """Salva a configuração no arquivo JSON."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)
    print("Configuração salva com sucesso!")


def setup_config():
    """Pergunta ao usuário se deseja alterar a configuração e salva os valores."""
    config = load_config()

    if config:
        print("\nConfiguração encontrada:")
        print(f"POOL_TOKEN: {config.get('POOL_TOKEN', 'Não definido')}")
        print(f"ADDITIONAL_ADDRESS: {config.get('ADDITIONAL_ADDRESS', 'Não definido')}")
        print(f"COMANDO_SCAN: {config.get('COMANDO_SCAN', 'Não definido')}")
        change = input("\nDeseja alterar a configuração? (s/n): ").strip().lower()
        if change != "s":
            return config

    # Solicita novos valores ao usuário
    config["POOL_TOKEN"] = input("Digite o POOL_TOKEN: ").strip()
    config["ADDITIONAL_ADDRESS"] = input("Digite o ADDITIONAL_ADDRESS: ").strip()
    config["COMANDO_SCAN"] = input(
        "Digite o comando para escanear os ranges.\n"
        "Use os seguintes placeholders para os valores dinâmicos:\n"
        "- {start} representa o início do range\n"
        "- {end} representa o fim do range\n"
        "- {in_file} representa o nome do arquivo de entrada\n"
        "- {out_file} representa o nome do arquivo de saída\n"
        "Comando: "
    ).strip()

    save_config(config)
    return config


def logger(level, message):
    """
    Logs a message with a timestamp and colored log level.

    Args:
        level (str): The log level (e.g., "Info", "Warning", "Error", "Success", "KEYFOUND").
        message (str): The message to log.
    """
    # Get the current date and time
    current_time = datetime.now()

    # Format the date and time as [YYYY-MM-DD.HH:MM:SS]
    formatted_time = current_time.strftime("[%Y-%m-%d.%H:%M:%S]")

    # Map log levels to colors
    color_map = {
        "Info": Fore.CYAN,
        "Warning": Fore.YELLOW,
        "Error": Fore.RED,
        "Success": Fore.GREEN,
        "KEYFOUND": Fore.MAGENTA,
    }

    # Get the color for the log level (default to white if not found)
    color = color_map.get(level, Fore.WHITE)

    # Print the formatted message with color
    print(f"{formatted_time} {color}[{level}]{Style.RESET_ALL} {message}")


def fetch_block_data():
    """Fetches the block data from the API.

    Sends a GET request to the API to retrieve information about the current block.
    If successful, it returns the block data in JSON format; otherwise, it prints an error.
    """
    headers = {"pool-token": POOL_TOKEN}
    try:
        response = requests.get(API_URL, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger(
                "Error",
                f"Error fetching block: {response.status_code} - {response.text}",
            )
            return None
    except requests.RequestException as e:
        logger("Error", f"Request Error {e}")
        return None


def save_addresses_to_file(addresses, additional_address, filename="in.txt"):
    """Saves a list of addresses and the additional address to a file.

    The function takes a list of addresses and appends the additional address to the file.
    Each address is saved in a new line in the 'in.txt' file.
    """
    try:
        with open(filename, "w") as file:
            for address in addresses:
                file.write(address + "\n")
            file.write(additional_address + "\n")
        logger("Info", f"Addresses saved successfully to '{filename}'.")
    except Exception as e:
        logger("Error", f"Error saving address: {e}")


def clear_file(filename):
    """Clears the content of a specified file.

    This function opens the file in write mode and empties its contents by not writing anything.
    It then prints a success message or an error message if something goes wrong.
    """
    try:
        with open(filename, "w"):
            pass
        logger("Info", f"File '{filename}' cleared successfully.")
    except Exception as e:
        logger("Error", f"Error clearing file '{filename}': {e}")


def run_program(start, end, command_template):
    """Runs the external cuBitCrack program with the given keyspace.

    This function generates a keyspace based on the provided start and end range,
    then executes the cuBitCrack program with specific options to attempt cracking the private keys.
    """
    command = command_template.format(
        start=start, end=end, in_file=IN_FILE, out_file=OUT_FILE
    ).split()
    try:
        logger("Info", f"Running with keyspace {start}:{end}")
        subprocess.run(command, check=True)
        logger("Success", "Script loaded successfully")
    except subprocess.CalledProcessError as e:
        logger("Error", f"Error running script: {e}")
    except Exception as e:
        logger("Error", f"Error exception: {e}")


def post_private_keys(private_keys):
    """Sends private keys to the API in batches of up to 10 keys.

    The private keys are sent in JSON format in a POST request. Each batch of keys is logged before it is sent.
    The function prints the response from the API or any error messages.
    """
    headers = {"pool-token": POOL_TOKEN, "Content-Type": "application/json"}
    data = {"privateKeys": private_keys}

    logger("Info", f"Sending the array of private keys ({len(private_keys)} / 10)")

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        if response.status_code == 200:
            logger("Success", "Private keys sent successfully.")
        else:
            logger(
                "Error",
                f"Error sending private keys: {response.status_code} - {response.text}",
            )
    except requests.RequestException as e:
        logger("Error", f"Error making the POST request: {e}")


def process_out_file(additional_address):
    """Processes the 'out.txt' and 'in.txt' files, extracts the private keys, and sends them to the API.

    This function checks if the 'out.txt' and 'in.txt' files exist, reads the private keys and addresses from the files,
    matches them, and sends batches of 10 private keys to the API. If the private key for the additional address is found,
    the program stops early.
    """
    if not os.path.exists(OUT_FILE):
        logger("Warning", f"File '{OUT_FILE}' not found.")
        return False

    if not os.path.exists(IN_FILE):
        logger("Warning", f"File '{IN_FILE}' not found.")
        return False

    private_keys = {}
    addresses = []
    found_additional_address = False

    try:
        # Reading the addresses from the in.txt file
        with open(IN_FILE, "r") as file:
            addresses = [line.strip() for line in file if line.strip()]

        # Removing the additional address to avoid inconsistency
        if additional_address in addresses:
            addresses.remove(additional_address)

        # Reading the addresses and private keys from the out.txt file
        with open(OUT_FILE, "r") as file:
            current_address = None
            for line in file:
                parts = line.split()  # Split the line into parts by whitespace

                if (
                    len(parts) >= 3
                ):  # Ensure that the line contains at least 3 parts (address, something, private key)
                    current_address = parts[0].strip()  # The first string (address)

                    # Makeshift for BitCrack Bug
                    if len(current_address) < 34:
                        # Prefix with '1' until the length is 34
                        current_address = current_address.rjust(34, "1")

                    private_key = parts[1].strip()  # The third string (private key)

                    # Store the private key with the address as the key in the dictionary
                    private_keys[current_address] = "0x" + private_key

                    # Checking if it is the key for the additional address
                    if current_address == additional_address:
                        found_additional_address = True

        # If the private key for the additional address was found
        if found_additional_address:
            logger(
                "KEYFOUND",
                "Private key for the additional address found! Stopping the program.",
            )
            logger("KEYFOUND", f"{private_keys.get(additional_address)}")
            try:
                with open("KEYFOUND.txt", "w") as file:
                    file.write(private_keys.get(additional_address) + "\n")

                logger("KEYFOUND", f"Addresses saved successfully to KEYFOUND.txt")
            except Exception as e:
                logger("KEYFOUND Error", f"Error saving address: {e}")

            return True

        # Checking if the number of private keys matches the number of addresses
        if len(private_keys) != len(addresses):
            logger(
                "Error",
                f"Number of private keys ({len(private_keys)}) does not match the number of addresses ({len(addresses)}).",
            )
            clear_file(OUT_FILE)
            return False

        # Sorting the private keys in the same order as the addresses in in.txt
        ordered_private_keys = []
        for addr in addresses:
            # Check for both the original address and the modified address
            if addr in private_keys:
                ordered_private_keys.append(private_keys[addr])
            else:
                # Makeshift for BitCrack Bug: Create a modified address if length is less than 34
                modified_addr = addr.rjust(34, "1") if len(addr) < 34 else addr
                if modified_addr in private_keys:
                    ordered_private_keys.append(private_keys[modified_addr])
                else:
                    logger("Warning", f"Address '{addr}' not found in private keys.")

        # Sending the private keys in batches of 10
        for i in range(0, len(ordered_private_keys), 10):
            batch = ordered_private_keys[i : i + 10]
            if len(batch) == 10:
                post_private_keys(batch)
                # print(f"[SUCCESS]: {len(batch)}")
            else:
                logger("Warning", f"Batch with less than 10 keys ignored: {len(batch)}")

    except Exception as e:
        logger("Error", f"processing files: {e}")

    # Clear the out.txt file after processing
    # return True
    clear_file(OUT_FILE)
    return False


# Carregar ou configurar os valores antes de iniciar o loop
config = setup_config()
POOL_TOKEN = config["POOL_TOKEN"]
ADDITIONAL_ADDRESS = config["ADDITIONAL_ADDRESS"]
COMANDO_SCAN = config["COMANDO_SCAN"]

# Main loop
if __name__ == "__main__":
    while True:
        clear_screen()
        block_data = fetch_block_data()
        if block_data:
            addresses = block_data.get("checkwork_addresses", [])
            if addresses:
                save_addresses_to_file(addresses, ADDITIONAL_ADDRESS)

                # Extracting start and end from the range
                range_data = block_data.get("range", {})
                start = range_data.get("start", "").replace("0x", "")
                end = range_data.get("end", "").replace("0x", "")

                if start and end:
                    run_program(start, end, COMANDO_SCAN)
                    if process_out_file(ADDITIONAL_ADDRESS):
                        break
                else:
                    logger("Info", "Start or End not found in the range.")
            else:
                logger("Warning", "No addresses found in the block.")
        else:
            logger("Error", "Error fetching block data.")
