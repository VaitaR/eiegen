import streamlit as st
from web3 import Web3
import requests
import json
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
curr_dir = os.path.dirname(os.path.dirname(__file__))

@st.cache_data(ttl=1800)
def get_block():
    block_data = w3.eth.get_block('latest')
    current_block = block_data['number']
    block_timestamp = block_data['timestamp']
    # convert timestamp to human readable format
    block_timestamp = datetime.utcfromtimestamp(block_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return current_block, block_timestamp

@st.cache_data(ttl=1800)
def get_proxy_abi(address:str):
    proxy_contract = json.loads(requests.get('https://api.etherscan.io/api?module=contract&action=getsourcecode&address=' + address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text)['result']
    proxy_contract_address = proxy_contract[0]['Implementation']
    proxy_contract_abi = json.loads(requests.get('https://api.etherscan.io/api?module=contract&action=getabi&address=' + proxy_contract_address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text)['result']
    return proxy_contract_abi

@st.cache_data(ttl=1800)
def load_wallets():
    wallets = json.load(open(os.path.join(curr_dir, 'inception_wallets.json')))['wallets']
    return wallets

@st.cache_data(ttl=1800)
def wallet_rpc_stats(wallet, current_block:int):
    address = wallet['address']
    name = wallet['name']
    # print adress as etherscan hyperlink
    st.write(f"**Name: {name}**, [{address}](https://etherscan.io/address/{address})")
    try:
        abi = get_proxy_abi(address)
    except Exception as e:
        st.write(f"Error with proxy: {e}")
        return 0    
    contract =  w3.eth.contract(address = address, abi = abi)
    try:
        totalAmountToWithdraw = contract.functions.totalAmountToWithdraw().call(block_identifier = current_block)
        totalAmountToWithdraw = round(totalAmountToWithdraw / 10**18, 4)
        totalAssets = contract.functions.totalAssets().call(block_identifier = current_block)
        totalAssets = round(totalAssets / 10**18, 4)
        PendingWithdrawalAmountFromEL = contract.functions.getPendingWithdrawalAmountFromEL().call(block_identifier = current_block)
        PendingWithdrawalAmountFromEL = round(PendingWithdrawalAmountFromEL / 10**18, 4)

        st.write(f"Withdraw: {totalAmountToWithdraw} | Pending: {PendingWithdrawalAmountFromEL} | Assets: {totalAssets}")
        if PendingWithdrawalAmountFromEL != 0:
            if totalAmountToWithdraw > totalAssets + PendingWithdrawalAmountFromEL:
                # write red color that need action
                st.markdown('<span style="color:orange">**_Orange danger_**</span>', unsafe_allow_html=True)
        elif totalAmountToWithdraw > totalAssets:
            # write red color that need action
            st.markdown('<span style="color:red">**_Red danger_**</span>', unsafe_allow_html=True)
    except Exception as e:
        st.write(f"Error with RPC requests: {e}")
        st.write()

    st.write('-------------------')    
    
    return 0


w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth/' + os.getenv('ANKR_KEY')))

current_block, block_timestamp = get_block()
st.write(f"Current block: {current_block}")
st.write(f"Block timestamp: {block_timestamp} (UTC)")
st.write('-------------------')

wallets = load_wallets()

for wallet in wallets:
    wallet_rpc_stats(wallet, current_block)








