# Love 内容管理后台

这是 `admin.itestv.com` 的 Cloudflare Worker。它通过 GitHub API 管理现有仓库内容，不改变前台的数据生成方式：

- 批量上传图片到 `photo/`
- 查看、删除照片
- 新建、编辑、删除 `blog/posts/*.md`
- 每次操作创建一个 GitHub 提交，现有 Pages 工作流随后自动更新网站

## 首次部署

1. 在 GitHub 创建 fine-grained personal access token：只授权 `tankey33/love`，Repository permissions 中 `Contents` 设为 `Read and write`。
2. 在本目录执行 `npm install`。
3. 执行 `npx wrangler login` 登录正确的 Cloudflare 账户。
4. 修改 `wrangler.toml` 中的 `ADMIN_EMAILS`，多个邮箱用英文逗号分隔。
5. 执行 `npx wrangler secret put GITHUB_TOKEN`，粘贴第 1 步的 token。
6. 执行 `npm run deploy`。

## 登录保护（必须）

在 Cloudflare Zero Trust 中打开 **Access controls → Applications**，创建 Self-hosted 应用：

- Hostname：`admin.itestv.com`
- Policy：Allow
- Include：只填写管理员邮箱
- 登录方式：Google 或邮箱一次性验证码

后台接口会再次检查 Cloudflare Access 注入的登录邮箱，并与 `ADMIN_EMAILS` 对比。`workers_dev = false` 用于避免绕过自定义域名直接访问 Worker。

## 本地检查

```bash
npm install
npm run check
```

本地预览默认没有 Cloudflare Access 邮箱头，因此 API 会返回 403；静态后台界面仍可查看。
