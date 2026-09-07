"""Local Ethereum-compatible chain using eth-tester + Web3."""
from pathlib import Path
from web3 import Web3
from eth_tester import EthereumTester, PyEVMBackend
from web3.providers.eth_tester import EthereumTesterProvider
from solcx import compile_source, install_solc

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "ContentRegistry.sol"


def deploy_local():
    install_solc("0.8.20")
    source = CONTRACT.read_text(encoding="utf-8")
    compiled = compile_source(source, solc_version="0.8.20")
    _, artifact = compiled.popitem()
    w3 = Web3(EthereumTesterProvider(EthereumTester(PyEVMBackend())))
    acct = w3.eth.accounts[0]
    w3.eth.default_account = acct
    c = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bin"])
    tx = c.constructor().transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    instance = w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])
    return w3, instance


def register_and_verify(content_hash_hex: str, source_url: str):
    w3, contract = deploy_local()
    content_hash = bytes.fromhex(content_hash_hex)
    tx = contract.functions.registerContent(content_hash, source_url).transact()
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    record = contract.functions.getRecord(0).call()
    on_chain_hash = record[0].hex()
    if on_chain_hash.startswith("0x"):
        on_chain_hash = on_chain_hash[2:]
    return {
        "transaction_hash": receipt.transactionHash.hex(),
        "contract_address": contract.address,
        "record_id": 0,
        "on_chain_hash": on_chain_hash,
        "source_url": record[1],
        "timestamp": record[2],
        "verified": on_chain_hash.lower() == content_hash_hex.lower(),
    }
