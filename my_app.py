import streamlit as st
import os
import shutil
import importlib.util
import time
from datetime import datetime

# Streamlitアプリケーションの設定
st.set_page_config(layout="centered", page_title="ファイル処理自動化ツール")

# --- st.session_state の初期化をアプリの最上部で行う ---
# これにより、アプリの再実行時にも状態が保持され、key の衝突を防ぐ
if 'operation_mode_selection' not in st.session_state:
    st.session_state.operation_mode_selection = "Streamlit Cloud (ファイルアップロード/ダウンロード)"

if 'script_source_selection' not in st.session_state:
    st.session_state.script_source_selection = "ファイルをアップロード"

# --- アプリケーション終了時のクリーンアップ ---
# Streamlit Cloudの一時ディレクトリは毎回クリーンアップ
# ローカルPCモードではユーザーが指定したディレクトリはクリーンアップしない
# この関数も、st.session_state の初期化後に配置
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

st.title("📂 ファイル処理自動化ツール")
st.markdown("---")

# --- モード選択 ---
st.header("利用モードの選択")

# st.radio の key を st.session_state のキーと一致させる
# value 引数を使って st.session_state から現在の値を取得
operation_mode = st.radio(
    "どちらのモードで利用しますか？",
    ("Streamlit Cloud (ファイルアップロード/ダウンロード)", "ローカルPC (フォルダパス指定)"),
    key="operation_mode_selection",  # ★★★ key を st.session_state の変数名と一致させる ★★★
    help="Streamlit Cloudにデプロイする場合は上のオプションを選択してください。",
    # on_change は不要。key が st.session_state と結びついているため、自動的に更新される
)

# 以降の条件分岐では、st.session_state.operation_mode_selection を直接参照する
# (st.radioの戻り値 operation_mode も同じ値を持つが、一貫性のためにセッションステートを参照)

st.markdown("---")

# --- 入力/出力ディレクトリのパス指定 (ローカルPCモードのみ) ---
input_dir = ""
output_dir = ""
if st.session_state.operation_mode_selection == "ローカルPC (フォルダパス指定)": # st.session_state を参照
    st.header("1. 入力/出力フォルダの指定 (ローカルPC)")
    st.warning("この機能は、**ローカルPCでStreamlitアプリを実行している場合のみ**有効です。Streamlit Cloudでは動作しません。")

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
    if input_dir and not os.path.isdir(input_dir):
        st.error(f"指定された入力フォルダが見つかりません: {input_dir}")
        st.stop()
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        st.warning("出力フォルダが指定されていません。処理結果はダウンロードできません。")
        st.stop()

    st.markdown("---")

# --- 入力ファイルのアップロード (Streamlit Cloudモードのみ) ---
temp_input_dir = ""
if st.session_state.operation_mode_selection == "Streamlit Cloud (ファイルアップロード/ダウンロード)": # st.session_state を参照
    st.header("1. 入力ファイルのアップロード (Streamlit Cloud)")
    uploaded_files = st.file_uploader(
        "処理したいファイルをアップロードしてください (複数選択可)",
        type=None,
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

# st.radio の key を st.session_state のキーと一致させる
script_source = st.radio(
    "処理スクリプトの指定方法を選択してください",
    ("ファイルをアップロード", "ローカルパスを指定 (ローカルPCモードのみ)"),
    key="script_source_selection", # ★★★ key を st.session_state の変数名と一致させる ★★★
    help="Streamlit Cloudでは「ファイルをアップロード」を選択してください。"
)

# 以降の条件分岐では、st.session_state.script_source_selection を直接参照する

temp_script_path = ""
if st.session_state.script_source_selection == "ファイルをアップロード": # st.session_state を参照
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

elif st.session_state.script_source_selection == "ローカルパスを指定 (ローカルPCモードのみ)": # st.session_state を参照
    if st.session_state.operation_mode_selection == "Streamlit Cloud (ファイルアップロード/ダウンロード)": # st.session_state を参照
        st.error("ローカルパス指定はStreamlit Cloudではサポートされていません。「ファイルをアップロード」を選択してください。")
        st.stop()

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

    # ローカルPCモードの場合、出力ディレクトリをクリアしない（ユーザーが管理）
    # クラウドモードの場合、出力ディレクトリは毎回クリア
    if st.session_state.operation_mode_selection == "Streamlit Cloud (ファイルアップロード/ダウンロード)": # st.session_state を参照
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir) # 以前の出力をクリア
        os.makedirs(output_dir, exist_ok=True)

    try:
        # スクリプトをモジュールとしてロード
        spec = importlib.util.spec_from_file_location("processing_script", temp_script_path)
        processing_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(processing_module)

        # 実行ログの記録
        # ローカルPCモードでは output_dir に直接ログを書き込む
        # クラウドモードでは output_dir (temp_output_cloud) に書き込む
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
                        "    else:         log_func('処理対象のCSVファイルが見つかりませんでした。')\n"
                        "    log_func('処理が終了しました。')\n"
                        "```")

    except Exception as e:
        st.error(f"処理中にエラーが発生しました: {e}")
        st.exception(e) # 詳細なエラーメッセージを表示

    # --- 処理結果のダウンロード (Streamlit Cloudモードのみ) ---
    if st.session_state.operation_mode_selection == "Streamlit Cloud (ファイルアップロード/ダウンロード)": # st.session_state を参照
        st.markdown("---")
        st.header("4. 処理結果のダウンロード")
        if os.path.exists(output_dir) and os.listdir(output_dir):
            zip_file_path = "processed_files.zip"
            # 以前のZIPファイルを削除
            if os.path.exists(zip_file_path):
                os.remove(zip_file_path)

            # 出力ディレクトリをZIP圧縮
            shutil.make_archive(os.path.splitext(zip_file_path)[0], 'zip', output_dir)

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

# --- アプリケーション終了時のクリーンアップ ---
# Streamlit Cloudの一時ディレクトリは毎回クリーンアップ
# ローカルPCモードではユーザーが指定したディレクトリはクリーンアップしない
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

st.markdown("---")
st.write("ご不明な点があればお問い合わせください。")
