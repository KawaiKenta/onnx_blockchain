import hashlib
import json
import subprocess
import sys
import onnx

def load_commands(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data['commands'], data['output']

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

def calculate_checksum(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def save_results(results, onnx_metadata, checksum, file_path='results.json'):
    final_result = {
        "commands": results,
        "onnx_meta": onnx_metadata,
        "checksum": checksum,
    }
    with open(file_path, 'w') as file:
        json.dump(final_result, file, indent=4)

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <json-file>")
        sys.exit(1)

    file_path = sys.argv[1]
    commands, onnx_output = load_commands(file_path)
    
    results = []
    for command in commands:
        result = execute_command(command)
        results.append(result)

    # onnxにchecksumを追加
    checksum = calculate_checksum(onnx_output)

    # metadataを保存
    onnx_metadata = get_onnx_metadata(onnx_output)
    save_results(results, onnx_metadata, checksum)

if __name__ == "__main__":
    main()