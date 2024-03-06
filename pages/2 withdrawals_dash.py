import streamlit as st
st.set_page_config(layout='wide')

from web3 import Web3, AsyncWeb3
from eth_abi import decode
import asyncio

from datetime import datetime
import requests
import json
import pandas as pd
import os

from dotenv import load_dotenv
load_dotenv()

# etherscan_key = os.getenv('ETHERSCAN_KEY')


def decode_logs_data(logs:list, abi:list): 

    for log in logs:
        # Convert hex values to integers
        keys_to_convert = ['blockNumber', 'timeStamp', 'gasPrice', 'gasUsed', 'logIndex', 'transactionIndex']
        for key in keys_to_convert:
            if key in log:
                # print(f"key: {key}, value: {log[key]}")
                log[key] = int(log[key], 16)
        # convert logs data
        w3 = Web3(Web3.HTTPProvider(f''))    
        receipt_event_signature_hex = log['topics'][0]
        event_list = [item for item in abi if item['type'] == 'event']

        for event in event_list:
            # Generate event signature hash
            name = event['name']
            inputs = ",".join([param['type'] for param in event['inputs']])
            event_signature_text = f"{name}({inputs})"
            event_signature_hex = w3.to_hex(w3.keccak(text=event_signature_text))

            # Check if the event signature matches the log's signature
            if event_signature_hex == receipt_event_signature_hex:
                decoded_log = {"event": event['name']}

                # Decode indexed topics
                indexed_params = [input for input in event['inputs'] if input['indexed']]
                for i, param in enumerate(indexed_params):
                    topic = log['topics'][i+1]
                    decoded_log[param['name']] = decode([param['type']], bytes.fromhex(topic[2:]))[0]

                # Decode non-indexed data
                non_indexed_params = [input for input in event['inputs'] if not input['indexed']]
                non_indexed_types = [param['type'] for param in non_indexed_params]
                non_indexed_values = decode(non_indexed_types, bytes.fromhex(log['data'][2:]))
                for i, param in enumerate(non_indexed_params):
                    decoded_log[param['name']] = non_indexed_values[i]

                log['decoded_data'] = decoded_log
                break  # Break the inner loop as we've found the matching event

    return logs

def get_proxy_abi(address:str):
    proxy_contract = json.loads(requests.get('https://api.etherscan.io/api?module=contract&action=getsourcecode&address=' + address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text)['result']
    proxy_contract_address = proxy_contract[0]['Implementation']
    proxy_contract_abi = json.loads(requests.get('https://api.etherscan.io/api?module=contract&action=getabi&address=' + proxy_contract_address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text)['result']
    return proxy_contract_abi

def get_logs_decode(address:str):
    log = requests.get('https://api.etherscan.io/api?module=logs&action=getLogs&fromBlock=19098696&toBlock=latest&address=' + address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text
    log_list = json.loads(log)

    proxy_abi = json.loads(get_proxy_abi(address))
    # print(type(proxy_abi))
    logs_decoded = decode_logs_data(log_list['result'], proxy_abi)
    return logs_decoded

curr_dir = os.path.dirname(os.path.dirname(__file__))

# # load wallets info
@st.cache_data(ttl=1800)
def load_wallets():
    wallets = json.load(open(os.path.join(curr_dir, 'inception_wallets.json')))['wallets']
    return wallets

@st.cache_data(ttl=1800)
def get_wallets_logs(wallets):
    all_logs = []
    for wallet in wallets:
        print(f"Getting logs for {wallet['address']}...")
        address = str(wallet['address'])
        logs = get_logs_decode(address)
        print(f"Logs for {wallet['name']}")
        print("========================= \n\n")
        all_logs.append(logs)
    return all_logs

@st.cache_data(ttl=1800)
def withdraw_logs(all_logs:list):
    withdraw_logs = []
    redeem_logs = []
    for log_list in all_logs:
        for log in log_list:
            if 'decoded_data' in log:
                # print(log['decoded_data']['event'])
                if log['decoded_data']['event'] == 'Withdraw':
                    withdraw_logs.append(log)

                if log['decoded_data']['event'] == 'Redeem':
                    redeem_logs.append(log)
   
    return withdraw_logs, redeem_logs

async def check_Redeemed(contract_address, sender, current_block):
    # function getPendingWithdrawalOf
    reedem_status = {}
    proxy_abi = json.loads(get_proxy_abi(contract_address))
    
    contract =  w3_async.eth.contract(address = contract_address, abi = proxy_abi)
    isAbleToRedeem = await contract.functions.isAbleToRedeem(sender).call(block_identifier = current_block)
    reedem_status['address'] = isAbleToRedeem
    return reedem_status

# setup rpc
w3_async = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider('https://rpc.ankr.com/eth/' + os.getenv('ANKR_KEY')))
w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth/' + os.getenv('ANKR_KEY')))
# load data
wallets = load_wallets()
all_logs = get_wallets_logs(wallets)
withdraw_logs, redeem_logs = withdraw_logs(all_logs)

st.write('Data loaded for all wallets')

# save withdraw logs to a csv file
withdraw_logs_df = pd.DataFrame(withdraw_logs)
withdraw_logs_df.to_csv(os.path.join(curr_dir, 'withdraw_logs.csv'), index=False)

# read withdraw logs from csv file
withdraw_logs_df = pd.read_csv(os.path.join(curr_dir, 'withdraw_logs.csv'))
withdraw_logs_df['timeStamp'] = pd.to_datetime(withdraw_logs_df['timeStamp'], unit='s')
withdraw_logs_df.sort_values(by='timeStamp', ascending=False, inplace=True)
withdraw_logs_df.reset_index(drop=True, inplace=True)


# save withdraw logs to a csv file
redeem_logs_df = pd.DataFrame(redeem_logs)
redeem_logs_df.to_csv(os.path.join(curr_dir, 'redeem_logs.csv'), index=False)

# read withdraw logs from csv file
redeem_logs_df = pd.read_csv(os.path.join(curr_dir, 'redeem_logs.csv'))
redeem_logs_df['timeStamp'] = pd.to_datetime(redeem_logs_df['timeStamp'], unit='s')
redeem_logs_df.sort_values(by='timeStamp', ascending=False, inplace=True)
redeem_logs_df.reset_index(drop=True, inplace=True)


# convert decoded_data to separate columns
def convert_decoded_data_to_columns(decoded_data:str):
    decoded_data = eval(decoded_data)
    if decoded_data['event'] == 'Withdraw':
        return pd.Series([decoded_data['event'], decoded_data['sender'], decoded_data['receiver'], decoded_data['owner'], decoded_data['amount'], decoded_data['iShares']])
    if decoded_data['event'] == 'Redeem':
        return pd.Series([decoded_data['event'], decoded_data['sender'], decoded_data['receiver'], decoded_data['amount']])
    
withdraw_logs_df[['event', 'sender', 'receiver', 'owner', 'amount', 'iShares']] = withdraw_logs_df['decoded_data'].apply(convert_decoded_data_to_columns)
redeem_logs_df[['event', 'sender', 'receiver', 'amount']] = redeem_logs_df['decoded_data'].apply(convert_decoded_data_to_columns)


withdraw_logs_df['amount'] = withdraw_logs_df['amount'].astype('float') / 10**18  
redeem_logs_df['amount'] = redeem_logs_df['amount'].astype('float') / 10**18                  
# columns order
withdraw_logs_df['Redeemed'] = 'None'
withdraw_logs_df['AbleRedeem'] = 'True'
withdraw_logs_df = withdraw_logs_df[['timeStamp', 'address', 'AbleRedeem', 'Redeemed', 'sender', 'amount', 'event', 'transactionHash', 'decoded_data']]
redeem_logs_df = redeem_logs_df[['timeStamp', 'address', 'amount', 'sender', 'event',  'transactionHash', 'decoded_data']]

st.title('Inception Monitoring Dashboard')

# add filter for the logs on the dashboard so user can filter by date
# filter by date
st.write('Filter by date')
start_date = pd.to_datetime(st.date_input('Start date', datetime.utcnow() - pd.Timedelta(days=8)))
end_date = pd.to_datetime(st.date_input('End date', datetime.utcnow())) + pd.Timedelta(days=1)
mask_withd = (withdraw_logs_df['timeStamp'] > start_date) & (withdraw_logs_df['timeStamp'] <= end_date)
withdraw_logs_df_filtered = withdraw_logs_df.loc[mask_withd]
mask_redeem = (redeem_logs_df['timeStamp'] > start_date) & (redeem_logs_df['timeStamp'] <= end_date)
redeem_logs_df_filtered = redeem_logs_df.loc[mask_redeem]

# add filter by wallet
st.write('Filter by wallet')
wallet_filter_list = withdraw_logs_df_filtered['address'].unique().tolist()
wallet_filter_list.insert(0, 'All')
wallet_filter = st.selectbox('Select wallet', wallet_filter_list)
if wallet_filter != 'All':
    withdraw_logs_df_filtered = withdraw_logs_df_filtered[withdraw_logs_df_filtered['address'] == wallet_filter]
    redeem_logs_df_filtered = redeem_logs_df_filtered[redeem_logs_df_filtered['address'] == wallet_filter]

# was withdrawal redeemed or not
def flag_redeemed(withdraw_logs_df, redeem_logs_df):
    # Инициализация столбца Redeemed с False
    withdraw_logs_df['Redeemed'] = 'None'

    # Используем временный DataFrame для отслеживания использованных redeem
    redeem_used = pd.DataFrame(columns=redeem_logs_df.columns)

    for index, withdraw_row in withdraw_logs_df.iterrows():
        tolerance_percent = 1  # Погрешность в процентах
        tolerance_value = withdraw_row['amount'] * tolerance_percent / 100  # Абсолютное значение погрешности

        potential_redeems = redeem_logs_df[
            (redeem_logs_df['sender'] == withdraw_row['sender']) & 
            (redeem_logs_df['amount'] >= withdraw_row['amount'] - tolerance_value) & 
            (redeem_logs_df['amount'] <= withdraw_row['amount'] + tolerance_value) &
            (redeem_logs_df['timeStamp'] > withdraw_row['timeStamp'])
        ].sort_values(by='timeStamp') # Сортировка по timeStamp для обработки самого раннего события redeem
        
        for _, redeem_row in potential_redeems.iterrows():
            # Проверка, что redeem не использован
            if not redeem_row['transactionHash'] in redeem_used['transactionHash'].values:
                withdraw_logs_df.at[index, 'Redeemed'] = 'Redeemed'
                redeem_used = pd.concat([redeem_used, redeem_row.to_frame().T])
                break  # Прерывание цикла после нахождения первого подходящего redeem
    
    return withdraw_logs_df

withdraw_logs_df_filtered = flag_redeemed(withdraw_logs_df_filtered, redeem_logs_df_filtered)

# rpc status check
# st.write('Check RPC status')
current_block = w3.eth.block_number

# check rpc status for sender address
non_redeemed_df = withdraw_logs_df_filtered[withdraw_logs_df_filtered['Redeemed'] == 'None']

@st.cache_data(ttl=1800)
def check_redeemed_df(withdraw_logs_df_filtered, non_redeemed_df):
    for i in range(len(non_redeemed_df)):
        try:
            contract_address = Web3.to_checksum_address(non_redeemed_df['address'].iloc[i])
            sender_address = Web3.to_checksum_address(non_redeemed_df['sender'].iloc[i])
            status = asyncio.run(check_Redeemed(contract_address, sender_address, current_block))
            # add data to withdraw_logs_df_filtered
            withdraw_logs_df_filtered.at[non_redeemed_df.index[i], 'AbleRedeem'] = str(status['address'])
        except Exception as e:
            withdraw_logs_df_filtered.at[non_redeemed_df.index[i], 'AbleRedeem'] = f"Error: {e}"
        # st.write(f"Sender address: {sender_address} | Redeem status: {status['address']}")
    return withdraw_logs_df_filtered

withdraw_logs_df_filtered = check_redeemed_df(withdraw_logs_df_filtered, non_redeemed_df)
st.write('AbleRedeem status checked')

# show stats table
st.write('Wallet Stats for the selected period')
wallet_stats = withdraw_logs_df_filtered.groupby('address').agg({'amount': ['sum', 'count']}).reset_index()    
wallet_stats.columns = ['Wallet', 'Total Amount', 'Count']
wallet_stats.rename(columns={'Total Amount':'Withd amount', 'Count':'Withd count'}, inplace=True)
st.write(wallet_stats)

@st.cache_data(ttl=1800)
def get_block():
    block_data = w3.eth.get_block('latest')
    current_block = block_data['number']
    block_timestamp = block_data['timestamp']
    # convert timestamp to human readable format
    block_timestamp = datetime.utcfromtimestamp(block_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return current_block, block_timestamp

current_block, block_timestamp = get_block()

# show table with logs
st.title('Withdraw logs')
st.write(f"\n Current block: {current_block} | Timestamp: {block_timestamp} (UTC)")
st.write(withdraw_logs_df_filtered)

st.write('Redeem logs')
# add checkbox to show redeem logs
show_redeem = st.checkbox('Show Redeem logs')
if show_redeem:
    st.write(redeem_logs_df_filtered)


