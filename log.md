# Voice Chat 開始通知アプリ

## 背景

　普段使っているのはLINEだが、ボイスチャットはDiscordで行っている。ボイスチャットを開始するにもいちいちチャットするのが大変でした。(自由に入って、自由に終わりたい。)

## 要件

　Discordでボイスチャットが始まった時に、開始通知をライングループに送信する。

## 基本設計　仕様

- Discordのボイスチャットが開始されると、Lineグループに通知される。
- Lineグループは不特定多数とする。(個人チャット等への活用も検討中)
- セキュリティを考慮して自宅サーバへのリクエスト送受信は行わない。

## 詳細設計　設計

1. Discordのボイスチャット開始を検知
   Discord APIを使って、特定のサーバー（ギルド）のボイスチャンネルでユーザーが接続したことを検知する。(切断は優先度低とする。)
2. VPSのWebhookサーバーがリクエストを送受信する。
   KonohaVPS上でPythonのFlaskやFastAPIを使ってWebhookサーバーを立ち上げる。
3. LINEグループチャットへ通知
   LINE Notify API を使用して、Webhookを通じてLINEグループにメッセージを送信する。送信内容は誰がどこでVoiceチャットを開始しました。程度。

ただし、自宅のグローバルIP以外NGにしているため、通知用のポートが決定したら、そのポートを開ける。

## 実装(Discord監視)

### Discord

Noti_VC_appでDiscord新規アプリを作成。トークンを発行し、OAuth2 URLをボットとして発行。Threadに参加させた。

### VPS(Discord分)

ローカル環境で2ファイル作成。
.env :環境変数ファイル
webhook_server.py :webhookサーバプログラム 全部合わせて24行

## デプロイ(Discord監視)

### VPSにファイルをコピー

```shell
cd C:\GitHub\Discord\Noti_VC_startapp\
# -rを指定しないと隠しファイルが送信できない。
scp -r .\ konoha:/home/kimura01/Noti_VC
```

### VPSでモジュールインストール

```bash
sudo apt update && sudo apt install python3-venv -y
python3 -m venv discord_webhook_env
source discord_webhook_env/bin/activate
pip install discord.py python-dotenv
```

## テスト(Discord監視)

### VPSがDiscordイベントを検知出来るか確認

VPSにてpythonプログラムをまずコマンドで動かす。

```bash
source ./discord_webhook_env/bin/activate
python3 webhook_server.py
```

```log
2025-03-02 16:48:32 INFO     discord.client logging in using static token
2025-03-02 16:48:33 INFO     discord.gateway Shard ID None has connected to Gateway (Session ID: cad2169b800c0434a8c7f64866903fea).
Bot is ready.
```

起動確認OK。
参加すると表示された。OK
ボイスチャットの名前が気に入らないので変える。
Discordの監視は出来た。OK

## 実装(LINE通知まで)

### LINE

LINE公式アカウントを作成。Messageing APIの登録を完了させた。
ボットをグループチャットに招待

### VPS(LINE分)

.envファイルに設定追加
しようと思ったけどよくわからない。
先に公式アカウントへのAPIをリクエストしてみる
リクエスト出来るようにするためにはSSL/TLS認証を使ってhttps通信出来るようにする。
自己証明書がダメなのでNginxを使う。と思ったけど年額でドメインを借りないといけない。テストなのでCloudFlareに変更する。
CloudFlareもゼロトラスト以外はドメインの登録が必要。年額900円ぐらいなのでいっそ勉強用として登録してしまう。
conohaでドメインを1年契約

```bash
sudo apt update
sudo apt install nginx
sudo apt install certbot python3-certbot-nginx
# このあたりはアンインストール
sudo apt remove nginx
sudo apt remove certbot python3-certbot-nginx
# キャッシュクリア等が必要なら実行

# Cloudflare Tunnel 用のCLIツールをインストール
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared noble main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt update
sudo apt install -y cloudflared
#こいつもやっぱり使えなかったのでアンインストール。もっとうまくできるようになったら使う。
sudo apt remove --purge -y cloudflared
sudo rm -f /etc/apt/sources.list.d/cloudflared.list
sudo rm -f /usr/share/keyrings/cloudflare-main.gpg
```

まずconohaでドメイン取得、年額900円。勉強代として捻出出来る。毎月1万円も本を買っていればいいか。

```bash
#結局舞い戻ってnginxインストール
sudo apt update
sudo apt install nginx -y
sudo apt install certbot python3-certbot-nginx -y
# LINE公式アカウント認証用のプログラムをデプロイしてテスト
source ./discord_webhook_env/bin/activate
python3 ./webhook_test/line_test.py
curl -X POST http://localhost:40001/webhook -H "Content-Type: application/json" -d '{"message": "テスト"}'
```

```log
サーバ側
Webhook受信: {'message': 'テスト'}
127.0.0.1 - - [02/Mar/2025 18:22:07] "POST /webhook HTTP/1.1" 200 -
リクエストクライアント(ローカルホスト送信分)
{
  "status": "ok"
}
OK
```

ドメイン取得完了まで待つ!!
ドメインにセットされたネームサーバが古くてつながらなかった。修正。2時間ぐらいロス。
教訓: ドメインに設定されたネームサーバとVPSの名前解決先に設定したネームサーバは同一のものになっていることを確認する！
VPS側の80番ポートを一時的に許可

```bash
sudo certbot certonly --nginx -d devteam-oni.top
sudo nano /etc/nginx/sites-available/devteam-oni.top

sudo nano /etc/systemd/system/flask-webhook.service
sudo systemctl daemon-reload
sudo systemctl start flask-webhook
sudo systemctl enable flask-webhook
```

webhookサーバを同じプロジェクトフォルダで動かすとクラッシュ！分ける。

```bash
sudo apt install tree -y
tree /home/kimura01/Noti_VC
```

---

```shell
curl -X POST -H 'Authorization: Bearer ***' -H 'Content-Type:application/json' -d '{}' https://api.line.me/v2/bot/channel/webhook/test
# OK　このコマンドは非常に重要メンテするときはこれでチェックする。LINEの開発者画面から、トークンはコピーてくること。
```

次はグループIDの特定
webhookからしか特定できない。めんどくさかった。

threadのgroup_id を環境ファイルに設定。
最後に通知を送信する処理を作る。これはdiscord監視側への実装になる。まず、監視プログラムをサービス化する。

## デプロイ(LINE通知まで)

## 総合試運転

送信がうまくいかない。

```shell
curl -v -X POST https://api.line.me/v2/bot/message/push `
-H "Content-Type: application/json" `
-H "Authorization: Bearer ****" `
-d '{
    "to": "C5f396abd888e124bd91fc8a72ac17ad4",
    "messages": [
        {
            "type": "text",
            "text": "LINE APIテストメッセージ"
        }
    ]
}'
```

単純にグループ参加させてなかっただけ。とりあえず、最低限の実装はできた。
ここからカスタム機能を追加していく。
## フォルダ名変更

webhook-oniに変更

## ここまでやった。
