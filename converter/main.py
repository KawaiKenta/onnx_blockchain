import torch
import torch.onnx
import onnx
from onnx2torch import convert


def main():
    # モデルのパス
    pytorch_model_path = "latest_model.pth"
    onnx_model_path = "converted_model.onnx"

    # # 実際には自分のモデルに合わせてください)
    model = torch.load(pytorch_model_path)
    model.eval()

    # ダミーの入力を作成 (入力サイズはモデルによって異なります)
    dummy_input = torch.randn(1, 3, 224, 224)

    # モデルをONNX形式に変換
    torch.onnx.export(model, dummy_input, onnx_model_path, verbose=True)

    # ONNXモデルの検証
    onnx_model = onnx.load(onnx_model_path)
    onnx.checker.check_model(onnx_model)
    print(f"ONNX model has been successfully converted and saved to {
          onnx_model_path}")

    # Or you can load a regular onnx model and pass it to the converter
    onnx_model = onnx.load(onnx_model_path)
    torch_model_2 = convert(onnx_model)


if __name__ == "__main__":
    main()
