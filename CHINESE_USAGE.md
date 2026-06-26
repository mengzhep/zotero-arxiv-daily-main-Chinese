# 中文邮件使用说明

本项目 fork 自 [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily)，并已加入**中文邮件支持**。

## 快速开始

### 1. Fork 本仓库

点击仓库右上角的 **Fork** 按钮，把项目复制到你自己的 GitHub 账号下。

### 2. 配置 GitHub Actions Secrets

进入你 fork 的仓库 → **Settings → Secrets and variables → Actions → New repository secret**，添加以下 Secrets：

| Secret | 说明 |
|--------|------|
| `ZOTERO_ID` | Zotero 用户 ID（一串数字，不是你的用户名） |
| `ZOTERO_KEY` | Zotero API Key（只读权限即可） |
| `SENDER` | 发件邮箱，例如 `abc@qq.com` |
| `SENDER_PASSWORD` | SMTP 授权码（不是邮箱登录密码） |
| `RECEIVER` | 收件邮箱 |
| `OPENAI_API_KEY` | LLM API Key |
| `OPENAI_API_BASE` | LLM API 地址，例如 `https://api.siliconflow.cn/v1` |

### 3. 配置 CUSTOM_CONFIG 变量

进入 **Settings → Secrets and variables → Actions → Variables → New repository variable**，添加变量名 `CUSTOM_CONFIG`。

```yaml
zotero:
  user_id: ${oc.env:ZOTERO_ID}
  api_key: ${oc.env:ZOTERO_KEY}
  include_path: null

email:
  sender: ${oc.env:SENDER}
  receiver: ${oc.env:RECEIVER}
  smtp_server: smtp.qq.com
  smtp_port: 465
  sender_password: ${oc.env:SENDER_PASSWORD}

llm:
  api:
    key: ${oc.env:OPENAI_API_KEY}
    base_url: ${oc.env:OPENAI_API_BASE}
  language: Chinese   # 启用中文邮件和中文 TLDR
  generation_kwargs:
    model: gpt-4o-mini

source:
  arxiv:
    category: ["cs.AI","cs.CV","cs.LG","cs.CL"]

executor:
  source: ['arxiv']
```

如需恢复英文，将 `language` 改为 `English` 或直接删除这一行。

### 4. 手动测试

进入仓库 **Actions → Test-Workflow → Run workflow**，触发一次测试。测试会抓取 5 篇论文并发送邮件。

### 5. 等待每日自动推送

主工作流默认每天 UTC 22:00 运行，会自动抓取前一天的新论文并发送中文推荐邮件。

## 本地运行

如果你希望在本地测试：

```bash
# 1. 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 克隆仓库
git clone https://github.com/你的用户名/zotero-arxiv-daily.git
cd zotero-arxiv-daily

# 3. 设置环境变量
export ZOTERO_ID=你的ZoteroID
export ZOTERO_KEY=你的ZoteroKey
export SENDER=你的发件邮箱
export SENDER_PASSWORD=你的SMTP授权码
export RECEIVER=你的收件邮箱
export OPENAI_API_KEY=你的APIKey
export OPENAI_API_BASE=https://api.siliconflow.cn/v1

# 4. 运行
uv run src/zotero_arxiv_daily/main.py
```

## 中文邮件效果

启用中文后，邮件会显示为：

- **相关度：** 7.5
- **摘要：** LLM 生成的一句话中文摘要
- **PDF** 按钮
- 无新论文时：**今日没有新论文，休息一下！**
- 底部：**如需退订，请在 GitHub Action 设置中移除您的邮箱。**

## 常见问题

1. **LLM 没有返回中文**  
   确认 `language: Chinese` 已正确添加在 `llm` 下，且使用的模型支持中文（如 `gpt-4o-mini`）。

2. **邮件显示乱码**  
   主流邮箱（QQ、Outlook、Gmail）均支持 UTF-8。如遇乱码，请检查 SMTP 服务器设置。

3. **如何切换回英文**  
   把 `custom.yaml` 中的 `language: Chinese` 改为 `language: English`。

4. **同步上游更新**  
   原仓库更新时，可以在 GitHub 页面点击 Sync fork。注意 `config/custom.yaml` 可能会被覆盖，需要重新设置 `language: Chinese`。
