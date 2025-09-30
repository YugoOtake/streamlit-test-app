import streamlit as st
import os
import shutil
import importlib.util
import time
from datetime import datetime
import zipfile

# Streamlitアプリケーションの設定
st.set_page_config(layout="centered", page_title="ファイル処理自動化ツール (Cloud/ファイルアップロード)")

# --- st.session_state の初期化をアプリの最上部で行う ---
# これにより、アプリの再実行時にも状態が保持され、key の衝突を防ぐ
# operation_mode_selection は不要になるため削除（ファイルアップロード方式に固定）
if 'script_source_selection' not in st.session_state:
    st.session_state.script_source_selection = "ファイルをアップロード" # デフォルトをファイルアップロードに固定

# --- アプリケーション終了時のクリーンアップ ---
# Streamlit Cloudの一時ディレクトリは毎回クリーンアップ
@st.cache_data(ttl=3600) # 1時間キャッシュ
def cleanup_temp_dirs_cloud_mode():
    if os.path.exists("temp_uploaded_input"):
        shutil.rmtree("temp_uploaded_input")
    if os.path.exists("temp_script"):
        shutil.rmtree("temp_script")
    if os.path.exists("temp_output_cloud"):
        shutil.rmtree("temp_output_cloud")
    if os.path.exists("processed_files.zip"):
        os.remove("processed_files.zip")

# アプリケーション起動時に一度だけ実行
if 'cleaned_up_cloud_mode' not in st.session_state:
    cleanup_temp_dirs_cloud_mode()
    st.session_state['cleaned_up_cloud_mode'] = True

st.title("📂 ファイル処理自動化ツール (Cloud/ファイルアップロード)")
st.markdown("---")

# --- 利用モードの表示 (固定) ---
st.header("利用モード: Streamlit Cloud (ファイルアップロード/ダウンロード)")
st.info("このアプリケーションは、Webブラウザからファイルをアップロードして利用します。")
st.markdown("---")

# --- 入力ファイルのアップロード (Streamlit Cloudモードのみ) ---
temp_input_dir = ""

st.header("1. 入力ファイルのアップロード")

uploaded_files = st.file_uploader(
    "処理したいファイルをアップロードしてください (複数選択可)",
    type=None, # 任意のファイルタイプを受け入れる
    accept_multiple_files=True,
    key="input_file_uploader"
)

if not uploaded_files:
    st.warning("処理するファイルをアップロードしてください。")
    st.stop()

# アップロードされたファイルを一時的に保存するディレクトリ
temp_input_dir = "temp_uploaded_input"
os.makedirs(temp_input_dir, exist_ok=True)

# 以前のファイルを削除
for filename in os.listdir(temp_input_dir):
    file_path = os.path.join(temp_input_dir, filename)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        st.error(f"一時入力ディレクトリのクリア中にエラーが発生しました: {e}")

# アップロードされたファイルを一時ディレクトリに保存
for uploaded_file in uploaded_files:
    file_path = os.path.join(temp_input_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"ファイルを保存しました: {uploaded_file.name}")

input_dir = temp_input_dir # 処理スクリプトに渡す入力ディレクトリを一時ディレクトリに設定
output_dir = "temp_output_cloud" # クラウドモード用の一時出力ディレクトリ
os.makedirs(output_dir, exist_ok=True) # 作成

st.markdown("---")

# --- 処理スクリプトのアップロード/指定 ---
st.header("2. 処理スクリプトの指定 (.pyファイル)")

# script_source の選択肢を「ファイルをアップロード」のみに限定
script_source = st.radio(
    "処理スクリプトの指定方法を選択してください",
    ("ファイルをアップロード",), # 選択肢を一つに限定
    key="script_source_selection",
    help="処理ロジックを含むPythonスクリプト (.py) をアップロードしてください。",
    index=0 # 常に最初の選択肢を選択
)

temp_script_path = ""

# ファイルアップロードのロジックを固定
if script_source == "ファイルをアップロード":
    uploaded_script = st.file_uploader(
        "処理ロジックを含むPythonスクリプト (.py) をアップロードしてください",
        type="py",
        key="script_file_uploader"
    )

    if not uploaded_script:
        st.warning("処理スクリプトをアップロードしてください。")
        st.stop()

    # アップロードされたスクリプトを一時的に保存
    temp_script_path = os.path.join("temp_script", uploaded_script.name)
    os.makedirs(os.path.dirname(temp_script_path), exist_ok=True)

    with open(temp_script_path, "wb") as f:
        f.write(uploaded_script.getbuffer())
    st.success(f"処理スクリプトを保存しました: {uploaded_script.name}")

st.markdown("---")

# --- 処理実行ボタン ---
st.header("3. 処理の実行")
if st.button("処理を開始する", help="指定されたファイルとスクリプトで処理を実行します", key="start_processing_button"):
    st.write("処理を開始します...")

    # クラウドモードなので、出力ディレクトリは毎回クリア
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir) # 以前の出力をクリア
    os.makedirs(output_dir, exist_ok=True)

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

    # --- 処理結果のダウンロード (Streamlit Cloudモード) ---
    st.markdown("---")
    st.header("4. 処理結果のダウンロード")

    if os.path.exists(output_dir) and os.listdir(output_dir):
        zip_file_path = "processed_files.zip"
        # 以前のZIPファイルを削除
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

        # 出力ディレクトリをZIP圧縮
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir) # ZIP内のパス
                    zipf.write(file_path, arcname)

        with open(zip_file_path, "rb") as f:
            st.download_button(
                label="処理結果をダウンロード (ZIP)",
                data=f.read(),
                file_name="processed_files.zip",
                mime="application/zip",
                key="download_button"
            )
        st.success("ダウンロード準備ができました。")
    else:
        st.info("出力ファイルがありません。処理が成功したか確認してください。")

st.markdown("---")
st.write("ご不明な点があればお問い合わせください。")
