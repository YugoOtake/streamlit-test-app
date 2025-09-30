import streamlit as st
import os
import shutil
import importlib.util
import time
from datetime import datetime

# Streamlitアプリケーションの設定
st.set_page_config(layout="centered", page_title="ファイル処理自動化ツール (ローカルPC専用)")

# --- st.session_state の初期化をアプリの最上部で行う ---
# これにより、アプリの再実行時にも状態が保持され、key の衝突を防ぐ
# operation_mode_selection の選択肢を「ローカルPC (フォルダパス指定)」のみに限定
if 'operation_mode_selection' not in st.session_state:
    st.session_state.operation_mode_selection = "ローカルPC (フォルダパス指定)" # デフォルト値を固定

if 'script_source_selection' not in st.session_state:
    st.session_state.script_source_selection = "ローカルパスを指定" # デフォルトをローカルパス指定に固定

# --- クリーンアップ関数はStreamlit Cloud関連なので削除 ---

st.title("📂 ファイル処理自動化ツール (ローカルPC専用)")
st.markdown("---")

# --- モード選択 ---
st.header("利用モードの選択")

# st.radio の選択肢を「ローカルPC (フォルダパス指定)」のみに限定
operation_mode = st.radio(
    "どちらのモードで利用しますか？",
    ("ローカルPC (フォルダパス指定)",), # 選択肢を一つに限定
    key="operation_mode_selection",
    help="このツールはローカルPCでのフォルダパス指定に特化しています。",
    index=0 # 常に最初の選択肢を選択
)

# 以降の条件分岐では、st.session_state.operation_mode_selection を直接参照する
# (st.radioの戻り値 operation_mode も同じ値を持つが、一貫性のためにセッションステートを参照)

st.markdown("---")

# --- 入力/出力ディレクトリのパス指定 (ローカルPCモードのみ) ---
input_dir = ""
output_dir = ""

# operation_mode_selection が "ローカルPC (フォルダパス指定)" の場合のみ表示されるが、
# 上記で選択肢を一つに固定したため、常に表示されるようになる
if st.session_state.operation_mode_selection == "ローカルPC (フォルダパス指定)":
    st.header("1. 入力/出力フォルダの指定")
    st.warning("この機能は、**ローカルPCでStreamlitアプリを実行している場合のみ**有効です。") # Streamlit Cloudでは動作しません の文言を削除

    input_dir = st.text_input(
        "入力フォルダのパスを入力してください (例: C:/Users/YourName/InputData)",
        value="./input", # デフォルト値を設定
        key="input_folder_path",
        help="処理したいファイルが保存されているフォルダの絶対パスまたは相対パスを指定してください。"
    )
    output_dir = st.text_input(
        "出力フォルダのパスを入力してください (例: C:/Users/YourName/OutputData)",
        value="./output", # デフォルト値を設定
        key="output_folder_path",
        help="処理結果を保存するフォルダの絶対パスまたは相対パスを指定してください。存在しない場合は自動で作成されます。"
    )

    # フォルダの存在確認と作成
    if input_dir:
        if not os.path.isdir(input_dir):
            st.error(f"指定された入力フォルダが見つかりません: {input_dir}")
            st.stop()
    else:
        st.warning("入力フォルダが指定されていません。")
        st.stop()

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        st.warning("出力フォルダが指定されていません。処理結果はダウンロードできません。")
        st.stop()

    st.markdown("---")

# --- 入力ファイルのアップロード (Streamlit Cloudモードのみ) は完全に削除 ---

# --- 処理スクリプトのアップロード/指定 ---
st.header("2. 処理スクリプトの指定 (.pyファイル)")

# script_source の選択肢から「ファイルをアップロード」を削除し、デフォルトを「ローカルパスを指定」に固定
script_source = st.radio(
    "処理スクリプトの指定方法を選択してください",
    ("ローカルパスを指定",), # 選択肢を一つに限定
    key="script_source_selection",
    help="ローカルPC上のPythonスクリプトのパスを指定してください。",
    index=0 # 常に最初の選択肢を選択
)

temp_script_path = ""

# Streamlit Cloud関連の条件分岐を削除し、ローカルパス指定に一本化
if script_source == "ローカルパスを指定":
    local_script_path = st.text_input(
        "処理スクリプトのパスを入力してください (例: C:/Scripts/my_processor.py)",
        key="local_script_path_input",
        help="処理ロジックを含むPythonスクリプトの絶対パスまたは相対パスを指定してください。"
    )
    if not local_script_path:
        st.warning("処理スクリプトのパスを入力してください。")
        st.stop()
    if not os.path.isfile(local_script_path):
        st.error(f"指定された処理スクリプトが見つかりません: {local_script_path}")
        st.stop()
    if not local_script_path.endswith('.py'):
        st.error("指定されたファイルはPythonスクリプト (.py) ではありません。")
        st.stop()
    
    temp_script_path = local_script_path # ローカルパスを直接使用

st.markdown("---")

# --- 処理実行ボタン ---
st.header("3. 処理の実行")
if st.button("処理を開始する", help="指定されたファイル/フォルダとスクリプトで処理を実行します", key="start_processing_button"):
    st.write("処理を開始します...")

    # ローカルPCモードなので、出力ディレクトリは常にユーザーが管理
    # Streamlit Cloud関連の出力ディレクトリクリアロジックは削除

    try:
        # スクリプトをモジュールとしてロード
        spec = importlib.util.spec_from_file_location("processing_script", temp_script_path)
        processing_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(processing_module)

        # 実行ログの記録
        log_file_path = os.path.join(output_dir, "execution_log.txt")
        with open(log_file_path, "w", encoding="utf-8") as log_f:
            start_time = datetime.now()
            log_f.write(f"処理開始時刻: {start_time}\n")
            log_f.write(f"入力ディレクトリ: {input_dir}\n")
            log_f.write(f"出力ディレクトリ: {output_dir}\n")
            log_f.write(f"処理スクリプト: {os.path.basename(temp_script_path)}\n\n")
            log_f.write("--- 処理スクリプトの出力開始 ---\n")

            if hasattr(processing_module, 'main') and callable(processing_module.main):
                def script_log_func(message):
                    st.text(f"スクリプトログ: {message}")
                    log_f.write(f"[スクリプトログ] {message}\n")

                processing_module.main(input_dir, output_dir, script_log_func)
                log_f.write("\n--- 処理スクリプトの出力終了 ---\n")
                end_time = datetime.now()
                log_f.write(f"処理終了時刻: {end_time}\n")
                log_f.write(f"処理時間: {end_time - start_time}\n")
                st.success("処理が完了しました！")
            else:
                st.error("アップロードされたスクリプトに 'main(input_dir, output_dir, log_func)' 関数が見つかりません。")
                st.info("スクリプトの例:\n\n"
                        "```python\n"
                        "import os\n"
                        "import pandas as pd\n\n"
                        "def main(input_dir, output_dir, log_func):\n"
                        "    log_func('処理を開始します。')\n"
                        "    # 入力ディレクトリ内のCSVファイルを読み込み、結合する例\n"
                        "    all_data = []\n"
                        "    for filename in os.listdir(input_dir):\n"
                        "        if filename.endswith('.csv'):\n"
                        "            filepath = os.path.join(input_dir, filename)\n"
                        "            log_func(f'ファイル読み込み中: {filename}')\n"
                        "            df = pd.read_csv(filepath)\n"
                        "            all_data.append(df)\n"
                        "    \n"
                        "    if all_data:\n"
                        "        combined_df = pd.concat(all_data, ignore_index=True)\n"
                        "        output_path = os.path.join(output_dir, 'combined_output.csv')\n"
                        "        combined_df.to_csv(output_path, index=False)\n"
                        "        log_func(f'処理結果を保存しました: {output_path}')\n"
                        "    else:\n"
                        "        log_func('処理対象のCSVファイルが見つかりませんでした。')\n"
                        "    log_func('処理が終了しました。')\n"
                        "```")

    except Exception as e:
        st.error(f"処理中にエラーが発生しました: {e}")
        st.exception(e) # 詳細なエラーメッセージを表示

    # --- 処理結果のダウンロード (Streamlit Cloudモードのみ) は削除 ---
    st.markdown("---")
    st.write("処理結果は指定された出力フォルダに保存されています。")

# --- アプリケーション終了時のクリーンアップ (Streamlit Cloud関連なので削除) ---

st.markdown("---")
st.write("ご不明な点があればお問い合わせください。")
