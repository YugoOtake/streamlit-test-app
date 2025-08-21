import streamlit as st
import pandas as pd

st.title('私の初めてのStreamlitアプリ') # アプリのタイトル

st.write('これはStreamlitで作成したシンプルなWebアプリケーションです。')

# テキスト入力ボックス
user_input = st.text_input('あなたの名前を入力してください:', 'ゲスト')
st.write(f'こんにちは、{user_input}さん！')

# スライダー
age = st.slider('あなたの年齢を選んでください:', 0, 100, 25)
st.write(f'あなたは{age}歳ですね。')

# チェックボックス
if st.checkbox('データフレームを表示する'):
    data = {
        'col1': [1, 2, 3, 4],
        'col2': ['A', 'B', 'C', 'D']
    }
    df = pd.DataFrame(data)
    st.dataframe(df) # データフレームを表示

# ボタン
if st.button('メッセージを表示'):
    st.success('ボタンがクリックされました！')

st.markdown('---') # 区切り線
st.write('これでStreamlitの基本がわかりましたね！')
