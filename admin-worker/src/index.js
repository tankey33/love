const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const VIDEO_TYPES = new Set(["video/quicktime", "video/mp4", "video/x-m4v"]);
const MAX_FILE_BYTES = 40 * 1024 * 1024;
const API_VERSION = "2022-11-28";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(request);

    try {
      const email = requireAdmin(request, env);
      if (request.method === "GET" && url.pathname === "/api/status") {
        return json({ ok: true, email, repository: env.GITHUB_REPO });
      }
      if (request.method === "GET" && url.pathname === "/api/photos") {
        return json(await listContent(env, "photo/", true));
      }
      if (request.method === "POST" && url.pathname === "/api/photos") {
        return json(await uploadPhotos(request, env));
      }
      if (request.method === "DELETE" && url.pathname === "/api/photos") {
        return json(await deletePaths(request, env, "photo/"));
      }
      if (request.method === "GET" && url.pathname === "/api/posts") {
        return json(await listContent(env, "blog/posts/", false));
      }
      if (request.method === "GET" && url.pathname === "/api/post") {
        const path = safePath(url.searchParams.get("path"), "blog/posts/");
        const file = await github(env, `/contents/${encodePath(path)}?ref=${encodeURIComponent(branch(env))}`);
        return json({ path, sha: file.sha, content: decodeBase64(file.content) });
      }
      if (request.method === "POST" && url.pathname === "/api/posts") {
        return json(await savePost(request, env));
      }
      if (request.method === "DELETE" && url.pathname === "/api/posts") {
        return json(await deletePaths(request, env, "blog/posts/"));
      }
      return json({ error: "接口不存在" }, 404);
    } catch (error) {
      const status = Number(error.status) || 500;
      return json({ error: error.message || "操作失败" }, status);
    }
  },
};

function requireAdmin(request, env) {
  const email = (request.headers.get("cf-access-authenticated-user-email") || "").toLowerCase();
  const allowed = String(env.ADMIN_EMAILS || "").split(",").map(v => v.trim().toLowerCase()).filter(Boolean);
  if (!email || !allowed.includes(email)) throw httpError(403, "当前账号没有管理权限");
  return email;
}

async function uploadPhotos(request, env) {
  const form = await request.formData();
  const files = form.getAll("photos").filter(value => value instanceof File && value.size);
  let metadata = [];
  try { metadata = JSON.parse(String(form.get("metadata") || "[]")); } catch { metadata = []; }
  if (!files.length) throw httpError(400, "请选择照片");
  if (files.length > 50) throw httpError(400, "每次最多上传 50 张照片");
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
  if (totalBytes > 80 * 1024 * 1024) throw httpError(400, "单次上传总大小不能超过 80MB，请分批上传");

  const existing = await listContent(env, "photo/", true);
  const used = new Set(existing.map(item => item.path.toLowerCase()));
  const changes = [];
  const numericNames = existing.map(item => Number((item.name.match(/^(\d+)\./) || [])[1])).filter(Number.isFinite);
  let sequence = Math.max(0, ...numericNames) + 1;
  const numberWidth = Math.max(2, String(sequence + files.length - 1).length);
  const groups = new Map();

  for (const [index, file] of files.entries()) {
    if (!IMAGE_TYPES.has(file.type) && !VIDEO_TYPES.has(file.type)) throw httpError(400, `${file.name} 不是支持的照片或实况视频格式`);
    if (file.size > MAX_FILE_BYTES) throw httpError(400, `${file.name} 超过 40MB`);
    const extension = extensionFor(file);
    const meta = metadata[index] && typeof metadata[index] === "object" ? metadata[index] : {};
    const originalBase = String(meta.originalName || file.name).replace(/\.[^.]+$/, "").toLowerCase();
    let stem = groups.get(originalBase);
    if (!stem) { stem = String(sequence++).padStart(numberWidth, "0"); groups.set(originalBase, stem); }
    let path = `photo/${stem}.${extension}`;
    while (used.has(path.toLowerCase())) { stem = String(sequence++).padStart(numberWidth, "0"); groups.set(originalBase, stem); path = `photo/${stem}.${extension}`; }
    used.add(path.toLowerCase());
    changes.push({ path, content: arrayBufferToBase64(await file.arrayBuffer()), encoding: "base64" });
    if (IMAGE_TYPES.has(file.type)) changes.push({ path: path.replace(/\.[^.]+$/, ".json"), content: JSON.stringify({ ...meta, uploadedAt: meta.uploadedAt || new Date().toISOString() }, null, 2) + "\n", encoding: "utf-8" });
  }

  const commit = await commitChanges(env, changes, `后台上传 ${files.length} 张照片`);
  return { ok: true, count: files.length, commit: commit.sha };
}

async function savePost(request, env) {
  const data = await request.json();
  const title = cleanText(data.title, 120);
  const date = /^\d{4}-\d{2}-\d{2}$/.test(data.date || "") ? data.date : new Date().toISOString().slice(0, 10);
  const summary = cleanText(data.summary, 300);
  const body = String(data.body || "").trim();
  const slug = cleanSlug(data.slug || title);
  if (!title || !slug || !body) throw httpError(400, "标题、文章地址和正文不能为空");

  const path = `blog/posts/${slug}.md`;
  if (data.originalPath && safePath(data.originalPath, "blog/posts/") !== path) {
    throw httpError(400, "编辑文章时不能修改文章地址；如需修改请新建文章");
  }
  const frontMatter = [
    "---",
    `title: ${title.replace(/\n/g, " ")}`,
    `date: ${date}`,
    `summary: ${summary.replace(/\n/g, " ")}`,
    `pinned: ${data.pinned ? "true" : "false"}`,
    `cover: ${cleanText(data.cover, 300)}`,
    "---",
    "",
  ].join("\n");
  const commit = await commitChanges(env, [{ path, content: frontMatter + body + "\n", encoding: "utf-8" }], `后台发布文章：${title}`);
  return { ok: true, path, commit: commit.sha };
}

async function deletePaths(request, env, prefix) {
  const data = await request.json();
  let paths = Array.isArray(data.paths) ? data.paths.map(p => safePath(p, prefix)) : [];
  if (!paths.length || paths.length > 50) throw httpError(400, "请选择要删除的内容");
  if (prefix === "photo/") {
    const ref = await github(env, `/git/ref/heads/${encodeURIComponent(branch(env))}`);
    const tree = await github(env, `/git/trees/${ref.object.sha}?recursive=1`);
    const existing = new Set((tree.tree || []).map(item => item.path));
    const sidecars = paths.map(path => path.replace(/\.[^.]+$/, ".json")).filter(path => existing.has(path));
    paths = [...paths, ...sidecars];
  }
  const commit = await commitChanges(env, paths.map(path => ({ path, sha: null })), `后台删除 ${paths.length} 项内容`);
  return { ok: true, count: paths.length, commit: commit.sha };
}

async function listContent(env, prefix, imagesOnly) {
  const ref = await github(env, `/git/ref/heads/${encodeURIComponent(branch(env))}`);
  const tree = await github(env, `/git/trees/${ref.object.sha}?recursive=1`);
  const imagePattern = /\.(?:jpe?g|png|webp|gif)$/i;
  return (tree.tree || [])
    .filter(item => item.type === "blob" && item.path.startsWith(prefix))
    .filter(item => !imagesOnly || imagePattern.test(item.path))
    .filter(item => imagesOnly || (/\.md$/i.test(item.path) && !/\/README\.md$/i.test(item.path)))
    .map(item => ({ path: item.path, name: item.path.split("/").pop(), size: item.size, sha: item.sha }))
    .sort((a, b) => b.name.localeCompare(a.name, "zh-CN", { numeric: true }));
}

async function commitChanges(env, changes, message) {
  if (!env.GITHUB_TOKEN) throw httpError(500, "后台尚未配置 GITHUB_TOKEN");
  const refName = encodeURIComponent(branch(env));
  const ref = await github(env, `/git/ref/heads/${refName}`);
  const parent = await github(env, `/git/commits/${ref.object.sha}`);
  const tree = [];

  for (const change of changes) {
    if (change.sha === null) {
      tree.push({ path: change.path, mode: "100644", type: "blob", sha: null });
      continue;
    }
    const content = change.encoding === "base64" ? change.content : utf8ToBase64(change.content);
    const blob = await github(env, "/git/blobs", { method: "POST", body: { content, encoding: "base64" } });
    tree.push({ path: change.path, mode: "100644", type: "blob", sha: blob.sha });
  }

  const newTree = await github(env, "/git/trees", { method: "POST", body: { base_tree: parent.tree.sha, tree } });
  const commit = await github(env, "/git/commits", { method: "POST", body: { message, tree: newTree.sha, parents: [ref.object.sha] } });
  await github(env, `/git/refs/heads/${refName}`, { method: "PATCH", body: { sha: commit.sha, force: false } });
  try {
    await github(env, "/dispatches", { method: "POST", body: { event_type: "content-updated", client_payload: { commit: commit.sha } } });
  } catch (error) {
    console.error("Unable to trigger deployment", error.message);
  }
  return commit;
}

async function github(env, path, options = {}) {
  const response = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}${path}`, {
    method: options.method || "GET",
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${env.GITHUB_TOKEN || ""}`,
      "x-github-api-version": API_VERSION,
      "user-agent": "love-admin-worker",
      ...(options.body ? { "content-type": "application/json" } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw httpError(response.status, payload.message || `GitHub 请求失败 (${response.status})`);
  return payload;
}

function branch(env) { return env.GITHUB_BRANCH || "main"; }
function safePath(value, prefix) {
  const path = String(value || "");
  if (!path.startsWith(prefix) || path.includes("..") || path.includes("\\")) throw httpError(400, "文件路径不正确");
  return path;
}
function cleanSlug(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9\u4e00-\u9fff_-]/g, "").replace(/-+/g, "-").slice(0, 100);
}
function cleanName(value) { return String(value || "").trim().replace(/\s+/g, "-").replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]/g, "").slice(0, 80); }
function cleanText(value, max) { return String(value || "").trim().slice(0, max); }
function extensionFor(file) { return ({ "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif", "video/quicktime": "mov", "video/mp4": "mp4", "video/x-m4v": "m4v" })[file.type] || file.name.split('.').pop().toLowerCase(); }
function encodePath(path) { return path.split("/").map(encodeURIComponent).join("/"); }
function json(data, status = 200) { return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS }); }
function httpError(status, message) { const error = new Error(message); error.status = status; return error; }
function utf8ToBase64(value) { return arrayBufferToBase64(new TextEncoder().encode(value)); }
function decodeBase64(value) { const bytes = Uint8Array.from(atob(String(value || "").replace(/\s/g, "")), c => c.charCodeAt(0)); return new TextDecoder().decode(bytes); }
function arrayBufferToBase64(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
}
