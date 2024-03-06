import streamlit as st
from web3 import Web3
import requests
import json
import os

from dotenv import load_dotenv
load_dotenv()
curr_dir = os.path.dirname(os.path.dirname(__file__))

@st.cache_data
def get_block():
    current_block = int(w3.eth.get_block('latest')['number'])
    st.write(f"Current block: {current_block}")
    return current_block

@st.cache_data
def get_proxy_abi(address:str):
    proxy_contract = json.loads(requests.get('https://api.etherscan.io/api?module=contract&action=getsourcecode&address=' + address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text)['result']
    proxy_contract_address = proxy_contract[0]['Implementation']
    proxy_contract_abi = json.loads(requests.get('https://api.etherscan.io/api?module=contract&action=getabi&address=' + proxy_contract_address + '&apikey=' + os.getenv('ETHERSCAN_KEY')).text)['result']
    return proxy_contract_abi

@st.cache_data
def load_wallets():
    wallets = json.load(open(os.path.join(curr_dir, 'inception_wallets.json')))['wallets']
    return wallets

@st.cache_data
def wallet_rpc_stats(wallet, current_block:int):
    address = wallet['address']
    name = wallet['name']
    st.write(f"**Name: {name}**, {address}")
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

        st.write(f"Withdraw: {totalAmountToWithdraw} | Assets: {totalAssets}")
        if totalAmountToWithdraw > totalAssets:
            # write red color that need action
            st.markdown('<span style="color:red">**_Need action_**</span>', unsafe_allow_html=True)
    except Exception as e:
        st.write(f"Error with RPC requests: {e}")
        st.write()

    st.write('-------------------')    
    
    return 0


w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth/' + os.getenv('ANKR_KEY')))
current_block = get_block()
wallets = load_wallets()

for wallet in wallets:
    wallet_rpc_stats(wallet, current_block)








