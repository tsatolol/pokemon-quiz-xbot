import json
import pandas as pd

from docker.app import lambda_handler

def test_lambda_e2e(monkeypatch):
    # --- 1. load_data の差し替え ---
    # CSV 読み込み部分をダミーデータに置き換える
    dummy_data = pd.DataFrame([{"Name": "Pikachu", "Type": "Electric"}])
    monkeypatch.setattr("docker.app.load_data", lambda: dummy_data)

    # --- 2. _call_bedrock の差し替え ---
    # _call_bedrock を呼び出すと、ダミーのクイズ情報を含むレスポンスを返すようにする
    dummy_quiz = {
        "question": "What is Pikachu?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Option A",
        "explanation": "Electric type Pokémon."
    }
    dummy_response = {
        "output": {
            "message": {
                "content": [{
                    "text": json.dumps(dummy_quiz)
                }]
            }
        }
    }
    monkeypatch.setattr("docker.app._call_bedrock", lambda prompt: dummy_response)

    # --- 3. x_client.create_tweet の差し替え ---
    # ツイート投稿部分をダミー関数に置き換え、呼び出し内容を記録する
    tweet_calls = []
    def dummy_create_tweet(**kwargs):
        tweet_calls.append(kwargs)
        # 1回目の呼び出しではツイートオブジェクトを返す（ツイートID を含む）
        if len(tweet_calls) == 1:
            class DummyTweet:
                data = {"id": "101"}
            return DummyTweet()
        else:
            # 2回目の呼び出しではリプライ投稿をシミュレート
            class DummyReply:
                data = {}
            return DummyReply()
    monkeypatch.setattr("docker.app.x_client.create_tweet", dummy_create_tweet)

    # --- 4. ダミーの event と context を作成 ---
    dummy_event = {}  # EventBridge から渡されるイベント（内容は Lambda 内で使用していない前提）
    dummy_context = type("DummyContext", (), {})()  # 最低限の属性だけ持つダミーコンテキスト

    # --- 5. Lambda 関数の起動 ---
    # EventBridge によるスケジュール実行をシミュレーション
    lambda_handler(dummy_event, dummy_context)

    # --- 6. ツイート投稿が正しく行われたか検証 ---
    # ツイート投稿は2回呼ばれているはず（1回目: ツイート作成、2回目: リプライ投稿）
    assert len(tweet_calls) == 2

    # 1回目の呼び出し（ツイート作成）のパラメータを検証
    first_call = tweet_calls[0]
    assert first_call["text"] == dummy_quiz["question"]
    assert first_call["poll_duration_minutes"] == 60
    assert first_call["poll_options"] == dummy_quiz["options"]

    # 2回目の呼び出し（リプライ投稿）のパラメータを検証
    second_call = tweet_calls[1]
    expected_reply_text = f"{dummy_quiz['correct_answer']}\n\n{dummy_quiz['explanation']}"
    assert second_call["text"] == expected_reply_text
    assert second_call["quote_tweet_id"] == 101
