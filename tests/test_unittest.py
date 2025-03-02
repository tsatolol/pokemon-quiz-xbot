import json
from docker.app import (_call_bedrock, _parse_to_json, post_quiz, system_prompt, model_id, bedrock_runtime, x_client)

def test_call_bedrock(monkeypatch):
    # テスト用のユーザープロンプト
    dummy_prompt = "# Test prompt"

    # bedrock_runtime.converse を差し替えるダミー関数
    def dummy_converse(modelId, messages, system, inferenceConfig, additionalModelRequestFields):
        # _call_bedrock 内で生成されるパラメータが期待通りであることを検証
        expected_messages = [{"role": "user", "content": [{"text": dummy_prompt}]}]
        expected_system = [{"text": system_prompt}]
        expected_inference_config = {"temperature": 0.1}
        expected_additional_fields = {"top_k": 10}

        assert modelId == model_id
        assert messages == expected_messages
        assert system == expected_system
        assert inferenceConfig == expected_inference_config
        assert additionalModelRequestFields == expected_additional_fields

        # ダミーのレスポンスを返す
        dummy_response = {
            "output": {
                "message": {
                    "content": [{
                        "text": json.dumps({
                            "question": "dummy question",
                            "options": ["A", "B", "C", "D"],
                            "correct_answer": "A",
                            "explanation": "dummy explanation"
                        })
                    }]
                }
            }
        }
        return dummy_response

    # monkeypatch を使って bedrock_runtime.converse を dummy_converse に差し替える
    monkeypatch.setattr(bedrock_runtime, "converse", dummy_converse)

    # _call_bedrock を実行
    response = _call_bedrock(dummy_prompt)

    # 期待するダミーのレスポンスと一致するかを検証
    expected_response = {
        "output": {
            "message": {
                "content": [{
                    "text": json.dumps({
                        "question": "dummy question",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "dummy explanation"
                    })
                }]
            }
        }
    }
    assert response == expected_response

def test_parse_to_json():
    # _parse_to_json が正しく JSON を返すかテストする

    # ダミーのクイズ情報を定義
    dummy_quiz = {
        "question": "dummy question",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "A",
        "explanation": "dummy explanation"
    }
    # _parse_to_json の想定するレスポンス構造を模したダミーの response を作成
    dummy_response = {
        "output": {
            "message": {
                "content": [{
                    "text": json.dumps(dummy_quiz)
                }]
            }
        }
    }
    # 関数を呼び出し、結果がダミーのクイズ情報と一致するか確認
    result = _parse_to_json(dummy_response)
    assert result == dummy_quiz

def test_post_quiz(monkeypatch):
    """
    post_quiz が正しく x_client.create_tweet を呼び出すか検証します。
    1回目の呼び出しではツイートを作成し、その戻り値の id を利用して
    2回目の呼び出しでリプライツイートを作成することを確認します。
    """
    # 呼び出し内容を記録するリストを用意
    call_history = []

    # create_tweet を差し替えるダミー関数
    def dummy_create_tweet(**kwargs):
        call_history.append(kwargs)
        # 1回目の呼び出しならば、ツイートオブジェクトを返す
        if len(call_history) == 1:
            class DummyTweet:
                data = {"id": "12345"}
            return DummyTweet()
        else:
            # 2回目の呼び出しでは適当なオブジェクトを返す
            class DummyReply:
                data = {}
            return DummyReply()

    # monkeypatch で x_client.create_tweet を差し替える
    monkeypatch.setattr(x_client, "create_tweet", dummy_create_tweet)

    # ダミーの quiz 情報
    dummy_quiz = {
        "question": "Test question?",
        "options": ["opt1", "opt2", "opt3", "opt4"],
        "correct_answer": "opt1",
        "explanation": "Explanation text"
    }

    # post_quiz を実行
    post_quiz(dummy_quiz)

    # create_tweet が 2 回呼ばれていることを検証
    assert len(call_history) == 2

    # 1回目の呼び出しの引数を検証
    expected_first_call = {
        "text": dummy_quiz["question"],
        "poll_duration_minutes": 60,
        "poll_options": dummy_quiz["options"]
    }
    assert call_history[0] == expected_first_call

    # 2回目の呼び出しの引数を検証
    expected_second_call = {
        "text": f"{dummy_quiz['correct_answer']}\n\n{dummy_quiz['explanation']}",
        "quote_tweet_id": 12345
    }
    assert call_history[1] == expected_second_call
