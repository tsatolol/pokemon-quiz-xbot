import json
import logging
import os
import time
import boto3
import pandas as pd
import tweepy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BEARER_TOKEN        = os.environ.get("X_BEARER_TOKEN", "for_test")
API_KEY             = os.environ.get("X_API_KEY", "for_test")
API_KEY_SECRET      = os.environ.get("X_API_KEY_SECRET", "for_test")
ACCESS_TOKEN        = os.environ.get("X_ACCESS_TOKEN", "for_test")
ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "for_test")

csv_path = "./data/pokemon_zukan.csv"
# model_id = "anthropic.claude-3-7-sonnet-20250219-v1:0"
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',
)

x_client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

system_prompt = """
# 役割
あなたはクイズを生成する言語モデルです。

# 指示
以下の条件でクイズを生成してください。

# 条件
    - 与えられたポケモン図鑑に従ってクイズを生成してください。
    - クイズは4択問題にしてください。
    - 下記のガイドラインにできるだけ従ってください。
    - それぞれの選択肢は25字以内にしてください。
    - 選択肢はランダムな順序で並べ替えて提示してください。
    - 日本語でクイズを作成してください。
    - 丁寧で親しみやすい口調にしてください。
    - クイズの生成形式は JSON とし、下記を参考にしてください。
    - 最終応答は、"{"で始まり"}"で終わる JSON のみを出力し、JSON以外の文字は一切応答に含めないでください。

    # クイズ作成のガイドライン
    **問題の内容**
    1. 問いたいことは何か、問題を解くために必要な能力は何かが明確であること
    2. 重要な事柄を問うこと。些末なことや一般的過ぎる問いにならないこと
    3. 正解が問題作成者の価値観に左右されるような問いにならないこと
    4. 特定の個人や集団に有利または不利な内容にならないこと
    5. ひっかけ問題にならないこと
    6. 高次の能力を測る問題では、受検者にとって新奇な素材を用いること

    **問題の形式**
    7. 測りたい能力に見合った問題形式を用いること
    8. 前の問題に対する解答が、後の問題の正誤に影響しないこと
    9. "あてはまるものをすべて選べ"という設問は避けること。使う場合は部分点を与えること
    10. 読解力や思考力を測る記述式問題では字数制限を設けないこと

    **問題の記述**
    11. 言語レベルを受検者集団に合わせること
    12. 教示文・本文・設問・選択枝・図表等の記述量を必要最小限にすること
    13. 教示文・本文・設問・選択枝・図表等の文言をよく校正すること。他の人にも確認してもらうのが望ましい
    14. 教示文・本文・設問・選択枝・図表・解答欄等のレイアウトや大きさを適切にすること
    15.とくに低学年の児童に対して、選択枝は行を変えて1つずつ並べること
    16. 空所補充問題について、文意が分からなくなるほどの空所を設けないこと

    **設問部分**
    17. 問いたいことは何か、どのような形式で解答したらよいかを明確・簡潔に書くこと
    18. 本文や選択枝など他の部分を読まなくても、設問部分だけで何を問われているかが分かること
    19. 否定表現を使わないこと。もし使う場合は、太字やアンダーラインで強調すること
    20. 一部の受検者にしか分からないような暗黙の前提を用いないこと

    **選択枝**
    21. いずれの選択枝ももっともらしいこと
    22. 高得点者と低得点者をよく区別できるような、識別力の高い選択枝を用いること
    23. 正答枝と誤答枝が明確に区別できること
    24. 不必要に選択枝を増やさないこと
    25. 明らかな誤答枝やお遊びの選択枝など、余計な選択枝を入れないこと
    26. 五十音順、数量の大きさ順など、何らかの法則に従って選択枝を並べること
    27. 正答枝の位置をランダムにばらつかせること
    28. "上記のいずれでもない" "上記すべてあてはまる"などの選択枝を用いないこと
    29. "～でない" "～以外である"など否定表現を用いないこと
    30. "絶対に" "常に" "決して" "完全に"など、強意語を用いないこと
    31. 選択枝は互いに独立であること。内容に重なりがないこと
    32. 一方が正答枝であれば他方は誤答枝であると分かるような、両立しない選択枝を入れないこと
    33. 選択枝の長さをおおむね揃えること
    34. 選択枝の内容や形式などの構造を揃えること

# クイズ生成の JSON 形式
{{
  "question": "{{question}}",
  "options": [
    "{{option_a}}",
    "{{option_b}}",
    "{{option_c}}",
    "{{option_d}}"
    ],
  "correct_answer": "{{correct_answer}}",
  "explanation": "{{explanation}}"
}}
"""


def load_data():
    logging.info("CSVファイルからデータを読み込んでいます。")
    return pd.read_csv(csv_path)


def generate_user_prompt(df):
    logging.info("データからユーザープロンプトを生成しています。")
    random_record = df.sample(n=1).iloc[0]
    random_pokemon = random_record.to_markdown(index=False)
    return f"# ポケモン図鑑\n{random_pokemon}"


def _call_bedrock(user_prompt):
    logging.info("ユーザープロンプトを使用してBedrock APIを呼び出しています。")
    # システムプロンプトの作成
    message = {
        "role": "user",
        "content": [{"text": user_prompt}]
    }
    messages = [message]
    system_prompts = [{"text": system_prompt}]

    # 推論パラメータの設定
    temperature = 0.1
    top_k = 10

    inference_config = {"temperature": temperature}
    additional_model_fields = {"top_k": top_k}

    # API 呼び出し
    response = bedrock_runtime.converse(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
        additionalModelRequestFields=additional_model_fields
    )

    logging.info("Bedrock APIからの応答を受信しました。")
    return response


def _parse_to_json(response):
    response_text = response["output"]["message"]["content"][0]["text"]
    return json.loads(response_text)


def generate_quiz(user_prompt, max_retry=3):
    logging.info("クイズを生成しています。")
    for i in range(max_retry):
        try:
            response = _call_bedrock(user_prompt)
            response_json = _parse_to_json(response)
            logging.info("クイズの生成に成功しました。")
            return response_json
        except Exception as e:
            last_exception = e
            logging.error(f"クイズ生成中にエラーが発生しました: {e}")
            time.sleep(2**i)
            continue
        break
    logging.error(f"{max_retry}回の試行後にクイズの生成に失敗しました。")
    raise Exception(f"クイズの生成は {max_retry} の試行のあと失敗\n最終エラー：{last_exception}")


def post_quiz(quiz):
    logging.info("クイズをTwitterに投稿しています。")
    question = quiz["question"]
    options = quiz["options"]
    correct_answer = quiz["correct_answer"]
    explanation = quiz["explanation"]

    # 2025-03-04 時点では、Free プランのレートリミットは17リクエスト/24時間
    # https://docs.x.com/x-api/fundamentals/rate-limits
    tweet = x_client.create_tweet(
        text=question,
        poll_duration_minutes=60,
        poll_options=options
    )

    time.sleep(1)

    tweet_id = int(tweet.data["id"])

    reply = x_client.create_tweet(
        text=f"{correct_answer}\n\n{explanation}",
        quote_tweet_id=tweet_id
    )
    logging.info("クイズの投稿に成功しました。")


def main():
    logging.info("メインプロセスを開始します。")
    df = load_data()
    user_prompt = generate_user_prompt(df)
    quiz = generate_quiz(user_prompt)
    print(quiz)
    post_quiz(quiz)
    logging.info("メインプロセスが完了しました。")


def lambda_handler(event, context):
    main()


if __name__ == "__main__":
    main()
