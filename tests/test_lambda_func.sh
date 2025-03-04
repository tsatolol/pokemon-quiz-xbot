#!/bin/bash

# Lambda関数の名前
LAMBDA_FUNCTION_NAME="pokemon-quiz-bot"

# リージョン
REGION="us-east-1"

# 結果を保存するファイル
RESULT_FILE="result_lambda_test.txt"

# Lambda関数を呼び出す
aws lambda invoke \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --region "$REGION" \
  "$RESULT_FILE"

# ステータスコードを抽出
STATUS_CODE=$(jq -r '.StatusCode' "$RESULT_FILE")

# ステータスコードを出力
echo "取得したステータスコード: $STATUS_CODE"

# テスト結果の判定
if [ "$STATUS_CODE" -eq 200 ]; then
  echo "テスト成功: ステータスコード $STATUS_CODE"
  exit 0
else
  echo "テスト失敗: ステータスコード $STATUS_CODE"
  exit 1
fi
