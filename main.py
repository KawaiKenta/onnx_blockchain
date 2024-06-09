import hashlib
import json
import subprocess
import sys
import onnx
from web3 import Web3

market_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
provider_url = "http://host.docker.internal:8545"
private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
upload_path = "localhost:3000/api/v1/upload"
web3 = Web3(Web3.HTTPProvider(provider_url))
web3.eth.defualtAccount = web3.eth.account.from_key(private_key)


def load_commands(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data['commands'], data['inputs'], data['output']


def load_contract(abi_path, bytecode_path):
    abi = load_json(abi_path)
    bytecode = load_bytecode(bytecode_path)
    return web3.eth.contract(abi=abi, bytecode=bytecode)


def load_bytecode(bytecode_path="blockchain/bytecode"):
    with open(bytecode_path, 'r') as file:
        bytecode = file.read()
    return bytecode


def load_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return json.dumps(data, separators=(',', ':'))


def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {
            'command': command,
            'output': result.stdout,
        }
    except subprocess.CalledProcessError as e:
        return {
            'command': command,
            'output': e.stderr,
        }


def execute_commands(commands):
    results = []
    for command in commands:
        result = execute_command(command)
        results.append(result)
    return results


def get_environment_info():
    commands = [
        "python --version",
        "pip freeze --all",
        "nvidia-smi",
        "nvcc --version",
        "cat /etc/os-release",
    ]
    info = execute_commands(commands)
    return info


def get_onnx_metadata(onnx_file):
    try:
        model = onnx.load(onnx_file)
        metadata = {
            "ir_version": model.ir_version,
            "producer_name": model.producer_name,
            "producer_version": model.producer_version,
            "domain": model.domain,
            "model_version": model.model_version,
            "doc_string": model.doc_string,
            "graph_name": model.graph.name,
            "graph_doc_string": model.graph.doc_string,
            "inputs": [input.name for input in model.graph.input],
            "outputs": [output.name for output in model.graph.output],
        }
        return metadata
    except Exception as e:
        return {"error": str(e)}


def calculate_checksum(files):
    sha256_hash = hashlib.sha256()
    for file in files:
        with open(file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def save_results(env_info, results, input_checksum, onnx_metadata, onnx_checksum, file_path='results.json'):
    final_result = {
        "environment": env_info,
        "commands": results,
        "input_checksum": input_checksum,
        "onnx_meta": onnx_metadata,
        "onnx_checksum": onnx_checksum,
    }
    with open(file_path, 'w') as file:
        json.dump(final_result, file, indent=4)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <json-file>")
        sys.exit(1)

    file_path = sys.argv[1]
    commands, data_input, onnx_output = load_commands(file_path)

    # create metadatas
    env_info = get_environment_info()

    # commandの実行
    results = execute_commands(commands)

    # data_input->input_checksum
    input_checksum = calculate_checksum(data_input)

    # onnx->onnx_checksum
    onnx_checksum = calculate_checksum([onnx_output])

    # onnx->onnx_metadata
    onnx_metadata = get_onnx_metadata(onnx_output)

    # save to results.json
    save_results(env_info, results,  input_checksum, onnx_metadata,
                 onnx_checksum, file_path='results.json')

    # deploy via Market
    market = web3.eth.contract(
        address=market_address, abi=load_json("blockchain/Market/abi.json")
    )
    transaction = market.functions.createONNXMeta(
        upload_path,
        load_json('results.json'),
        onnx_checksum,
    ).transact()
    tx_receipt = web3.eth.wait_for_transaction_receipt(transaction)


if __name__ == "__main__":
    main()
