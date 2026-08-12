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
42℃で停止する温度条件が使われていました。静的検証済みの14通りから選択
できます。

- ファン開始温度：35、40、45℃
- ファン最大温度：50、55、60、65、70℃
- ファン停止温度：開始温度−3℃
- 開始温度から最大温度までの最小幅：10℃

「ファン最大温度」は温度由来のファン要求が約100%に達する温度であり、
過熱保護温度ではありません。45/70/42℃は純正相当です。低い設定ほど、
ファン稼働時間、騒音、吸塵、摩耗が増える可能性があります。

純正BINおよび改変済みBINは配布しません。生成ツールは、利用者が用意した
原本についてSHA-256、サイズ、末尾マーカー、変更前バイトを検証し、すべて
一致した場合に限り候補を生成します。

## ブラウザパッチャー

コマンド操作なしで利用する場合は、
[ASF48100U200-Hブラウザパッチャー](https://yudaihata.github.io/srne-asf48100u200-h-fan-control/)
を使用できます。選択したBINはブラウザ外へ送信されません。原本SHA-256、
サイズ、末尾マーカー、変更前命令、変更オフセット、生成後SHA-256がすべて
一致した場合だけ候補BINをダウンロードできます。

## Quick start：手動CLI

Python 3.11以降を使用します。

可能な場合は、事前検証済みプロファイルを指定します。

```bash
python3 tools/build_candidate.py \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --profile fan40C_max65C_off37C \
  --output /path/to/ASF48100SU200_V8.16.9_fan40C_max65C_off37C.bin

python3 tools/verify_candidate.py \
  --candidate /path/to/ASF48100SU200_V8.16.9_fan40C_max65C_off37C.bin \
  --profile fan40C_max65C_off37C \
  --source /path/to/ASF48100SU200_V8.16.9.bin
```

従来名の`fan35C_off32C`と`fan40C_off37C`も、それぞれ同一内容の
35/60/32℃候補と40/65/37℃候補への別名として引き続き利用できます。

技術的に詳しい利用者は、Browser Patcherの14通りに含まれない整数℃の温度も
指定できます。`--stop-c`を省略した場合は開始温度−3℃になります。

```bash
python3 tools/build_candidate.py \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --start-c 38 --max-c 58 --stop-c 35 \
  --acknowledge-unreviewed \
  --output /path/to/ASF48100SU200_V8.16.9_custom_38_58_35.bin

python3 tools/verify_candidate.py \
  --candidate /path/to/ASF48100SU200_V8.16.9_custom_38_58_35.bin \
  --source /path/to/ASF48100SU200_V8.16.9.bin \
  --start-c 38 --max-c 58 --stop-c 35 \
  --acknowledge-unreviewed
```

カスタムモードの範囲は`1 <= 開始 <= 50℃`、`開始 < 最大 <= 100℃`、
`0 <= 停止 < 開始℃`です。開始温度の上限は、すべての整数℃のカーブ原点を
C28x即値で正確に表現するためのものです。Browser Patcherの最小温度幅10℃は意図的に適用
しません。カスタム候補には事前検証済みの出力ハッシュや実機検証結果は
ありません。ツールはC28x命令を生成して正確な変更バイトと候補ハッシュを
表示し、検証時には同じ温度指定と原本BINを要求します。上級者向け経路の
誤使用を避けるため、確認フラグを必須にしています。

対象原本のSHA-256は
`d4b4f4590689ae2effedf40e3999da8d4b9dfdcac7a1eff4635d0eca6d644600`
です。それ以外のファームウェアには適用できません。

## 資料

- [`docs/static-analysis.md`](docs/static-analysis.md)：制御ロジック、命令、
  オフセット、静的解析の限界
- [`docs/porting-to-other-firmware.md`](docs/porting-to-other-firmware.md)：
  別ファームウェアをAIエージェントまたは人間が再解析するための証拠ベース手順
- [`analysis/v8.16.9-fan-control.annotated.asm`](analysis/v8.16.9-fan-control.annotated.asm)：
  V8.16.9の解析結果を裏付ける必要最小限の注釈付き逆アセンブル断片
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
