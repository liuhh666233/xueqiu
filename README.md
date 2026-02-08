# Xueqiu Article Scraper

下载雪球用户的原创文章及作者补充说明，以 Markdown 格式按日期归档，支持增量同步。

## 目录结构

```
scraper/                 # 主程序包
  cli.py                 # CLI 入口 (sync / status / check-auth)
  config.py              # 配置加载 (YAML + 环境变量)
  models.py              # 数据模型 (pydantic v2)
  client.py              # HTTP 客户端
  api.py                 # 雪球 API 封装
  content.py             # 文章内容提取与 Markdown 转换
  crawler.py             # 爬取调度
  storage.py             # 文件写入与同步清单管理
tests/                   # 单元测试
config.example.yaml      # 配置模板
systemd/                 # systemd 定时任务
data/articles/           # 文章存储目录 (自动创建，已 gitignore)
```

## 环境准备

```bash
nix develop
```

## 获取 Cookie

scraper 需要浏览器的完整 Cookie 字符串来访问 API（雪球使用 WAF 防护，仅 `xq_a_token` 不够）。获取步骤：

1. 用浏览器登录 [雪球](https://xueqiu.com/)
2. 按 `F12` 打开开发者工具，切换到 **Network**（网络）标签页
3. 刷新页面，点击任意一个请求
4. 在 **Request Headers** 中找到 `Cookie` 字段，复制其**完整值**

复制出来的内容类似：`acw_tc=...; xq_a_token=...; u=...; ...`

> cookie 有效期有限，过期后需要重新获取。可以用 `check-auth` 命令验证是否有效。

## 使用方法

### 同步文章

首次运行会下载全部原创文章，后续运行只下载新文章（增量同步）。

```bash
# 通过命令行参数传入 cookie
python -m scraper sync --cookie "your_xq_a_token"

# 或通过环境变量
export XUEQIU_COOKIE="your_xq_a_token"
python -m scraper sync

# 或写入配置文件（参考 config.example.yaml）
cp config.example.yaml config.yaml
# 编辑 config.yaml 填入 cookie
python -m scraper sync
```

### 验证 Cookie

```bash
python -m scraper check-auth --cookie "your_xq_a_token"
```

### 查看同步状态

```bash
python -m scraper status
```

## 配置文件

复制 `config.example.yaml` 为 `config.yaml` 并根据需要修改：

```yaml
cookie: "your_xq_a_token"    # 必填
user_id: 2426670165           # 目标用户 ID
data_dir: "data/articles"     # 文章存储路径
request_delay: 2.0            # 请求间隔（秒）
page_size: 10                 # 每页文章数
max_pages: 0                  # 最大页数，0 表示全部
```

优先级：命令行参数 > 环境变量 > 配置文件。

## 输出格式

文章保存为 `data/articles/YYYY/YYYY-MM-DD_标题_ID.md`，格式如下：

```markdown
---
title: "文章标题"
date: 2024-01-15T10:30:00+08:00
article_id: 123456789
url: https://xueqiu.com/2426670165/123456789
view_count: 1500
like_count: 42
---

# 文章标题

（正文内容）

---

## 补充说明

### 2024-01-16 09:15

（作者的补充说明内容）
```

## 自动定时同步

项目提供了 systemd service 和 timer，可设置每天自动同步：

```bash
# 复制 service 和 timer 到 systemd 用户目录
cp systemd/xueqiu-scraper.service ~/.config/systemd/user/
cp systemd/xueqiu-scraper.timer ~/.config/systemd/user/

# 根据实际情况编辑 service 中的路径和 cookie 配置
# 然后启用定时器
systemctl --user enable --now xueqiu-scraper.timer

# 查看定时器状态
systemctl --user status xueqiu-scraper.timer
```

## 运行测试

```bash
python -m unittest discover -s tests -v
```
