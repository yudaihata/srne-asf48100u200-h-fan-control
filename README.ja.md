# 非公式 SRNE ASF48100U200-H ファン制御

[English](README.md)

> [!WARNING]
> これは独立した非公式の解析プロジェクトであり、SRNE Solar Co., Ltd.との
> 提携・承認・サポート関係はありません。改変ファームウェアは、機器損傷、
> 感電・火災、保証、法規上の問題を生じさせる可能性があります。

SRNE `ASF48100U200-H` のファームウェア
`ASF48100SU200_V8.16.9.bin`に含まれるファン制御を静的解析し、再現可能な
検証・候補生成・実機ログ分析ツールとしてまとめたリポジトリです。

標準ファームウェアでは、負荷・充電・放電要求に加えて、およそ45℃で開始、
42℃で停止する温度条件が使われていました。以下の最小差分プロファイルを
収録しています。

| プロファイル | 開始 | 停止 | カーブ原点 | 想定用途 |
|---|---:|---:|---:|---|
| `fan40C_off37C` | 40℃ | 37℃ | 40℃ | 標準より5℃低い設定。ファン稼働・騒音が増える可能性あり |
| `fan35C_off32C` | 35℃ | 32℃ | 35℃ | 温度低下が大きい一方、ファン稼働・騒音・摩耗も増える可能性あり |

純正BINおよび改変済みBINは配布しません。生成ツールは、利用者が用意した
原本についてSHA-256、サイズ、末尾マーカー、変更前バイトを検証し、すべて
一致した場合に限り候補を生成します。

## ブラウザパッチャー

コマンド操作なしで利用する場合は、
[ASF48100U200-Hブラウザパッチャー](https://yudaihata.github.io/srne-asf48100u200-h-fan-control/)
を使用できます。選択したBINはブラウザ外へ送信されません。原本SHA-256、
サイズ、末尾マーカー、変更前命令、変更オフセット、生成後SHA-256がすべて
一致した場合だけ候補BINをダウンロードできます。

## 使用例

Python 3.11以降を使用します。

```bash
python3 tools/build_candidate.py \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --profile fan40C_off37C \
  --output /path/to/ASF48100SU200_V8.16.9_fan40C_off37C.bin

python3 tools/verify_candidate.py \
  --candidate /path/to/ASF48100SU200_V8.16.9_fan40C_off37C.bin \
  --profile fan40C_off37C \
  --source /path/to/ASF48100SU200_V8.16.9.bin
```

対象原本のSHA-256は
`d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600`
です。それ以外のファームウェアには適用できません。

## 資料

- [`docs/static-analysis.md`](docs/static-analysis.md)：制御ロジック、命令、
  オフセット、静的解析の限界
- [`docs/runtime-validation.md`](docs/runtime-validation.md)：fan35c実機ログの
  比較方法と冷却効果
- [`docs/safety.md`](docs/safety.md)：書き込み前の確認事項と未解決リスク
- [`profiles/profiles.json`](profiles/profiles.json)：機械可読な差分定義
- [`tools/`](tools/)：候補生成、検証、HAログ比較ツール

## 重要な注意

これはメーカー資料ではなく独立した解析結果です。命令、差分、ハッシュが
正しくても、アップデータ互換性、安全な起動、別ハードウェアリビジョンとの
互換性は保証されません。ファームウェア更新には、装置使用不能、感電、火災、
保証・法規上の問題など重大なリスクがあります。実機に書き込む前に必ず
[`docs/safety.md`](docs/safety.md)を確認してください。

## ライセンス

このリポジトリで作成したツールと文書にはMIT Licenseを適用します。SRNEの
ファームウェア、製品名、商標、派生ファームウェアイメージに対する利用許諾を
与えるものではありません。詳細は[`NOTICE.md`](NOTICE.md)を参照してください。
