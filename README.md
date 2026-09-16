# 曲爸爸动画资产库

一个可部署到 GitHub Pages 的个人 GLB 动画资产库，界面参考 `G:\自制软件\TTS音频库`：每个动画是一张横向卡片，左侧为方形 WEBP 动图预览，右侧显示名称、固定性别标签和可增减的其他标签。

## 目录结构

```text
index.html
style.css
app.js
data.json
assets/
└── <性别>/<动画名称>/
    ├── <动画名称>.glb
    ├── preview.webp
    └── meta.json
```

## 本地 WebUI 上传

安装 Flask 后双击 `start.bat`，或运行：

```bash
pip install flask
python app.py
```

打开 `http://127.0.0.1:5000`，输入密码 `********`，再通过「上传动画」保存到本地 `assets/` 并自动更新 `data.json`。GLB 文件会按动画名称保存，例如 `挥手待机.glb`。

不要直接双击 `index.html`。直接打开会使用 `file://` 协议，浏览器会拦截页面访问本地上传 API；请使用 `start.bat`，它会启动服务并自动打开正确的网址。

## GitHub Pages 部署

1. 将本目录内容放入 GitHub 仓库根目录。
2. 在仓库 Settings → Pages 中选择 `Deploy from a branch`、`main`、`/ (root)`。
3. 将本地的 `index.html`、`style.css`、`app.js`、`data.json` 和 `assets/` 手动提交到 GitHub。
4. Pages 页面只提供密码门槛、浏览、筛选和下载，不提供上传功能。

下载需要先输入密码，直接点击卡片右上角的下载按钮即可。密码是前端基础门槛，不是服务器级权限控制；如果需要真正私密，应使用私有仓库或带鉴权的后端。GitHub Pages 对大文件和仓库容量有限制，超大 GLB 建议改用 Git LFS 或 Release 附件。
"# Glb_Animation" 
