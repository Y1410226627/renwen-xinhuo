# deploy/ —— 部署配置模板

> 完整说明见 **`../部署方案.md`**。这里只放可直接照抄的配置文件。

| 文件 | 用途 |
| --- | --- |
| `nginx-cilv.conf` | 反向代理：主应用走 `/`，本引擎走 `/engine/`（含 SSE 关缓冲、前缀剥离） |
| `cilv-engine.service` | systemd 常驻服务（openEuler / 麒麟 / Ubuntu 通用） |

## 三步起服务（主从式）

```bash
# 1) 引擎只绑回环（交给反向代理）
cd <项目目录>
python3 web/serve.py --host 127.0.0.1 --port 8010 --no-open

# 2) 装反向代理配置（按实际路径改 server_name / 主应用端口）
sudo cp deploy/nginx-cilv.conf /etc/nginx/conf.d/cilv.conf
sudo nginx -t && sudo systemctl reload nginx

仓库中的 nginx 示例仅监听 HTTP/80。远程写请求会被拒绝；要开放写操作，需增加与引擎同机的 HTTPS/TLS 站点，
并传递 `X-Forwarded-For` 与 `X-Forwarded-Proto: https`。引擎只信任本机回环地址的代理连接，不能由远程客户端伪造这些头。写令牌由 `/etc/cilv-engine.env` 提供。
启用 systemd 前，先创建仅管理员可读的 `/etc/cilv-engine.env`，写入 `LVC_WRITE_TOKEN=<随机令牌>`，
并执行 `chmod 600 /etc/cilv-engine.env`。

# 3) 常驻（可选；把 Unit 里的路径与 User 改成实际值）
sudo cp deploy/cilv-engine.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cilv-engine
```

## 三个最容易改错的点

1. **`proxy_pass` 末尾的 `/`** —— 少了它，引擎会收到 `/engine/api/...` → 全部 404。
2. **`proxy_buffering off;`** —— 不关，问答页的流式（SSE）会看起来「卡死」。
3. **端口别撞** —— 本引擎默认 8000；主从式下**显式用 8010**。

## 信创自检（部署后先跑）

```bash
python3 -V                                                    # ≥ 3.10
python3 -c "import sqlite3;c=sqlite3.connect(':memory:');c.execute('CREATE VIRTUAL TABLE t USING fts5(x)');print('FTS5 OK')"
python3 tools/check_all.py --fast                             # 交付答案 SHA256 + 自检
curl -s http://127.0.0.1:8010/api/examples | head -c 120      # 起服务后
```
