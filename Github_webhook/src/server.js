const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const axios = require('axios');
const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 3000;

app.use(bodyParser.json());

app.post('/github',async (req, res) => {
    console.log('GitHubからのWebhook受信');
    console.log('ヘッダー:', req.headers);
    console.log('ボディ:', JSON.stringify(req.body, null, 2));
    const event = req.headers['x-github-event'];
    const action = req.body.action;
  
    try {
      if (event === 'issue_comment' && action === 'created') {
        const comment = req.body.comment;
        const issue = req.body.issue;
        const user = comment.user.login;
        const body = comment.body;
  
        const discordMessage = {
          content: `💬 **${user}** が [${issue.title}](${issue.html_url}) にコメントしました：\n> ${body}`
        };
  
        await axios.post(DISCORD_WEBHOOK_URL, discordMessage);
      }
    res.status(200).send('Webhook受信成功');
    } catch (err) {
      console.error('Discord送信エラー:', err);
      res.status(500).send('Error');
    }
});
app.listen(PORT, () => {
  console.log(`Webhookサーバー起動：ポート番号 ${PORT}`);
});
