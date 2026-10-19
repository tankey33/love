const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const VIDEO_TYPES = new Set(["video/quicktime", "video/mp4", "video/x-m4v"]);
const IMAGE_EXTENSIONS = new Set(["jpg", "jpeg", "png", "webp", "gif"]);
const VIDEO_EXTENSIONS = new Set(["mov", "mp4", "m4v"]);
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

  const existing = await listBlobs(env, "photo/");
  const media = existing.filter(item => mediaKindFromName(item.name));
  const used = new Set(existing.map(item => item.path.toLowerCase()));
  const existingBySha = new Map(media.map(item => [item.sha, item]));
  const uploadIndex = await readUploadIndex(env);
  const existingByOriginal = new Map(Object.entries(uploadIndex).map(([sha, path]) => [sha, media.find(item => item.path === path)]).filter(([, item]) => item));
  const changes = [];
  const skipped = [];
  const numericNames = media.map(item => Number((item.name.match(/^(\d+)\./) || [])[1])).filter(Number.isFinite);
  let sequence = Math.max(0, ...numericNames) + 1;
  const numberWidth = Math.max(2, String(sequence + files.length - 1).length);
  const grouped = new Map();

  for (const [index, file] of files.entries()) {
    const kind = mediaKind(file);
    if (!kind) throw httpError(400, `${file.name} 不是支持的照片或实况视频格式`);
    if (file.size > MAX_FILE_BYTES) throw httpError(400, `${file.name} 超过 40MB`);
    const meta = sanitizePhotoMetadata(metadata[index]);
    const originalBase = String(meta.originalName || file.name).replace(/\.[^.]+$/, "").toLowerCase();
    if (!grouped.has(originalBase)) grouped.set(originalBase, []);
    grouped.get(originalBase).push({ file, meta, kind });
  }

  for (const group of grouped.values()) {
    const prepared = [];
    for (const entry of group) {
      const originalBytes = new Uint8Array(await entry.file.arrayBuffer());
      const originalSha = entry.meta.originalSha || await gitBlobSha(originalBytes);
      const embedded = entry.kind === "image" ? readEmbeddedExif(originalBytes) : {};
      const meta = sanitizePhotoMetadata({ ...entry.meta, ...embedded, originalSha });
      const bytes = entry.kind === "image" ? sanitizeImageBytes(originalBytes, extensionFor(entry.file), meta.orientation) : sanitizeVideoBytes(originalBytes);
      prepared.push({ ...entry, meta, originalSha, bytes, sha: await gitBlobSha(bytes) });
    }
    const matched = prepared.map(item => existingBySha.get(item.sha) || existingByOriginal.get(item.originalSha) || existingByOriginal.get(item.sha)).find(Boolean);
    let stem = matched ? matched.name.replace(/\.[^.]+$/, "") : String(sequence++).padStart(numberWidth, "0");
    for (const item of prepared) {
      if (existingBySha.has(item.sha) || existingByOriginal.has(item.originalSha) || existingByOriginal.has(item.sha)) {
        skipped.push(item.file.name);
        continue;
      }
      const extension = extensionFor(item.file);
      let path = `photo/${stem}.${extension}`;
      if (used.has(path.toLowerCase())) {
        if (matched) {
          skipped.push(item.file.name);
          continue;
        }
        do { stem = String(sequence++).padStart(numberWidth, "0"); path = `photo/${stem}.${extension}`; } while (used.has(path.toLowerCase()));
      }
      used.add(path.toLowerCase());
      existingBySha.set(item.sha, { path, name: path.split("/").pop(), sha: item.sha });
      existingByOriginal.set(item.originalSha, { path, name: path.split("/").pop(), sha: item.sha });
      uploadIndex[item.originalSha] = path;
      uploadIndex[item.sha] = path;
      changes.push({ path, content: arrayBufferToBase64(item.bytes), encoding: "base64" });
      if (item.kind === "image") changes.push({ path: path.replace(/\.[^.]+$/, ".json"), content: JSON.stringify({ ...item.meta, uploadedAt: item.meta.uploadedAt || new Date().toISOString() }, null, 2) + "\n", encoding: "utf-8" });
    }
  }

  if (!changes.length) return { ok: true, count: 0, skipped: skipped.length, duplicates: skipped };
  const uploadedCount = changes.filter(change => mediaKindFromName(change.path)).length;
  changes.push({ path: "photo/_upload-index.json", content: JSON.stringify(uploadIndex) + "\n", encoding: "utf-8" });
  const commit = await commitChanges(env, changes, `后台上传 ${uploadedCount} 个文件`);
  return { ok: true, count: uploadedCount, skipped: skipped.length, duplicates: skipped, commit: commit.sha };
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
    const companions = paths.flatMap(path => {
      const stem = path.replace(/\.[^.]+$/, "");
      return [`${stem}.json`, ...[...VIDEO_EXTENSIONS].map(ext => `${stem}.${ext}`)];
    }).filter(path => existing.has(path));
    paths = [...new Set([...paths, ...companions])];
  }
  const commit = await commitChanges(env, paths.map(path => ({ path, sha: null })), `后台删除 ${paths.length} 项内容`);
  return { ok: true, count: paths.length, commit: commit.sha };
}

async function listContent(env, prefix, imagesOnly) {
  const items = await listBlobs(env, prefix);
  const originals = imagesOnly ? await readUploadIndex(env) : {};
  const byPath = new Map();
  for (const [sha, path] of Object.entries(originals)) byPath.set(path, [...(byPath.get(path) || []), sha]);
  const imagePattern = /\.(?:jpe?g|png|webp|gif)$/i;
  return items
    .filter(item => !imagesOnly || imagePattern.test(item.path))
    .filter(item => imagesOnly || (/\.md$/i.test(item.path) && !/\/README\.md$/i.test(item.path)))
    .map(item => imagesOnly ? { ...item, originalSha: (byPath.get(item.path) || [])[0] || "", originalShas: byPath.get(item.path) || [] } : item)
    .sort((a, b) => b.name.localeCompare(a.name, "zh-CN", { numeric: true }));
}

async function readUploadIndex(env) {
  try {
    const file = await github(env, `/contents/photo/_upload-index.json?ref=${encodeURIComponent(branch(env))}`);
    const parsed = JSON.parse(decodeBase64(file.content));
    return Object.fromEntries(Object.entries(parsed).filter(([sha, path]) => /^[a-f0-9]{40}$/.test(sha) && /^photo\/[^/]+\.(?:jpe?g|png|webp|gif|mov|mp4|m4v)$/i.test(path)));
  } catch (error) {
    if (error.status === 404 || error instanceof SyntaxError) return {};
    throw error;
  }
}

async function listBlobs(env, prefix) {
  const ref = await github(env, `/git/ref/heads/${encodeURIComponent(branch(env))}`);
  const tree = await github(env, `/git/trees/${ref.object.sha}?recursive=1`);
  return (tree.tree || [])
    .filter(item => item.type === "blob" && item.path.startsWith(prefix))
    .map(item => ({ path: item.path, name: item.path.split("/").pop(), size: item.size, sha: item.sha }));
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

const PHOTO_TEXT_FIELDS = new Set(["make", "camera", "lens", "software", "description", "title", "artist", "copyright", "timeZone", "originalName", "city", "country", "aperture", "shutter", "focalLength", "focalLength35", "exposureCompensation", "flash", "whiteBalance", "colorSpace", "exposureProgram", "exposureMode", "meteringMode", "sceneCaptureType", "contrast", "saturation", "sharpness"]);
const PHOTO_NUMBER_RANGES = { aperture: [.1, 256], shutterSeconds: [.000001, 86400], iso: [1, 10000000], focalLength: [.1, 20000], focalLength35: [.1, 40000], exposureCompensation: [-30, 30], flash: [0, 65535], whiteBalance: [0, 10], colorSpace: [0, 65535], orientation: [1, 8], exposureProgram: [0, 100], exposureMode: [0, 100], meteringMode: [0, 255], sceneCaptureType: [0, 100], contrast: [0, 10], saturation: [0, 10], sharpness: [0, 10], brightnessValue: [-100, 100], subjectDistance: [0, 1000000], digitalZoom: [0, 1000], originalSize: [0, 1000000000], originalLastModified: [0, 9000000000000] };
function validPhotoDate(value) {
  const text = String(value || "").replace(/^(\d{4}):(\d{2}):(\d{2})/, "$1-$2-$3");
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$/);
  if (!match) return "";
  const [, y, m, d, h = "00", minute = "00", second = "00"] = match;
  const date = new Date(Date.UTC(+y, +m - 1, +d, +h, +minute, +second));
  if (+y < 1900 || +y > new Date().getFullYear() + 2 || date.getUTCFullYear() !== +y || date.getUTCMonth() !== +m - 1 || date.getUTCDate() !== +d || +h > 23 || +minute > 59 || +second > 59) return "";
  return text.replace(" ", "T");
}
function sanitizePhotoMetadata(source) {
  if (!source || typeof source !== "object" || Array.isArray(source)) return {};
  const out = {};
  for (const field of PHOTO_TEXT_FIELDS) {
    const value = typeof source[field] === "string" ? source[field].normalize("NFKC").trim() : "";
    if (!value || value.length > 300 || /[\u0000-\u001f\u007f-\u009f\ufffd]/.test(value)) continue;
    if (["make", "camera", "lens", "software"].includes(field) && (value.length < 2 || /[^\x20-\x7e]/.test(value) || /^\d{4}[:/-]\d{2}/.test(value))) continue;
    out[field] = value;
  }
  for (const [field, [minimum, maximum]] of Object.entries(PHOTO_NUMBER_RANGES)) if (typeof source[field] === "number" && Number.isFinite(source[field]) && source[field] >= minimum && source[field] <= maximum) out[field] = source[field];
  for (const field of ["takenAt", "uploadedAt"]) { const value = validPhotoDate(source[field]); if (value) out[field] = value; }
  if (/^[a-f0-9]{40}$/.test(source.originalSha || "")) out.originalSha = source.originalSha;
  if (source.hideLocation === true) out.hideLocation = true;
  else if ((source.isTravel === true && source.shareLocation === true) || source.locationPrivacy === "city") {
    Object.assign(out, { isTravel: true, shareLocation: true, locationPrivacy: "city" });
    if (typeof source.latitude === "number" && typeof source.longitude === "number" && Number.isFinite(source.latitude) && Number.isFinite(source.longitude) && Math.abs(source.latitude) <= 90 && Math.abs(source.longitude) <= 180) Object.assign(out, { latitude: Math.round(source.latitude * 10) / 10, longitude: Math.round(source.longitude * 10) / 10 });
  }
  if (out.locationPrivacy !== "city") { delete out.city; delete out.country; }
  return out;
}

function concatBytes(parts) { const out = new Uint8Array(parts.reduce((total, part) => total + part.length, 0)); let offset = 0; for (const part of parts) { out.set(part, offset); offset += part.length; } return out; }
function orientationExif(orientation) {
  if (!Number.isInteger(orientation) || orientation < 2 || orientation > 8) return new Uint8Array();
  return new Uint8Array([69,120,105,102,0,0,73,73,42,0,8,0,0,0,1,0,18,1,3,0,1,0,0,0,orientation,0,0,0,0,0,0,0]);
}
function readEmbeddedExif(bytes) {
  let tiff;
  if (bytes[0] === 255 && bytes[1] === 216) {
    for (let at = 2; at + 4 <= bytes.length;) {
      const marker = bytes[at + 1], length = bytes[at + 2] * 256 + bytes[at + 3];
      if (marker === 218 || marker === 217 || length < 2 || at + length + 2 > bytes.length) break;
      if (marker === 225 && new TextDecoder().decode(bytes.subarray(at + 4, at + 10)) === "Exif\0\0") { tiff = bytes.subarray(at + 10, at + 2 + length); break; }
      at += length + 2;
    }
  } else if (bytes[0] === 137 && bytes[1] === 80) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let at = 8; at + 12 <= bytes.length;) { const length = view.getUint32(at), kind = new TextDecoder().decode(bytes.subarray(at + 4, at + 8)); if (at + length + 12 > bytes.length) break; if (kind === "eXIf") { tiff = bytes.subarray(at + 8, at + 8 + length); break; } at += length + 12; }
  } else if (new TextDecoder().decode(bytes.subarray(0, 4)) === "RIFF") {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let at = 12; at + 8 <= bytes.length;) { const length = view.getUint32(at + 4, true), kind = new TextDecoder().decode(bytes.subarray(at, at + 4)); if (at + length + 8 > bytes.length) break; if (kind === "EXIF") { tiff = bytes.subarray(at + 8, at + length + 8); if (new TextDecoder().decode(tiff.subarray(0, 6)) === "Exif\0\0") tiff = tiff.subarray(6); break; } at += length + 8 + (length & 1); }
  }
  if (!tiff || tiff.length < 8) return {};
  try {
    const view = new DataView(tiff.buffer, tiff.byteOffset, tiff.byteLength), little = view.getUint16(0) === 0x4949;
    if (!little && view.getUint16(0) !== 0x4d4d) return {};
    const u16 = at => view.getUint16(at, little), u32 = at => view.getUint32(at, little);
    const directory = at => {
      const result = {}; if (!at || at + 2 > tiff.length) return result;
      const count = Math.min(u16(at), 256);
      for (let index = 0; index < count; index++) {
        const entry = at + 2 + index * 12; if (entry + 12 > tiff.length) break;
        const tag = u16(entry), type = u16(entry + 2), n = u32(entry + 4), unit = ({1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8})[type];
        if (!unit || n > 10000) continue;
        const length = unit * n, start = length <= 4 ? entry + 8 : u32(entry + 8); if (start + length > tiff.length) continue;
        if (type === 2) { try { result[tag] = new TextDecoder("utf-8", { fatal: true }).decode(tiff.subarray(start, start + length)).replace(/\0.*$/, "").trim(); } catch { continue; } }
        else if (type === 3) result[tag] = u16(start);
        else if (type === 4) result[tag] = u32(start);
        else if (type === 9) result[tag] = view.getInt32(start, little);
        else if (type === 5 || type === 10) { const numerator = type === 10 ? view.getInt32(start, little) : u32(start), denominator = type === 10 ? view.getInt32(start + 4, little) : u32(start + 4); if (denominator) result[tag] = numerator / denominator; }
      }
      return result;
    };
    const root = directory(u32(4)), exif = directory(root[0x8769]);
    const fields = { takenAt: exif[0x9003] || exif[0x9004] || root[0x0132], make: root[0x010f], camera: root[0x0110], software: root[0x0131], artist: root[0x013b], copyright: root[0x8298], orientation: root[0x0112], lens: exif[0xa434], aperture: exif[0x829d], shutterSeconds: exif[0x829a], iso: exif[0x8827], focalLength: exif[0x920a], focalLength35: exif[0xa405], exposureCompensation: exif[0x9204], flash: exif[0x9209], whiteBalance: exif[0xa403], colorSpace: exif[0xa001], exposureProgram: exif[0x8822], exposureMode: exif[0xa402], meteringMode: exif[0x9207], sceneCaptureType: exif[0xa406], contrast: exif[0xa408], saturation: exif[0xa409], sharpness: exif[0xa40a], brightnessValue: exif[0x9203], subjectDistance: exif[0x9206], digitalZoom: exif[0xa404], timeZone: exif[0x9011] };
    return sanitizePhotoMetadata(fields);
  } catch { return {}; }
}

function sanitizeImageBytes(bytes, extension, orientation) {
  const exif = orientationExif(orientation);
  if (["jpg", "jpeg"].includes(extension)) {
    if (bytes[0] !== 255 || bytes[1] !== 216) throw httpError(400, "照片的 JPEG 数据无效");
    const parts = [bytes.subarray(0, 2)];
    if (exif.length) parts.push(new Uint8Array([255, 225, 0, exif.length + 2]), exif);
    let at = 2;
    while (at < bytes.length) {
      const start = at; if (bytes[at++] !== 255) throw httpError(400, "照片的 JPEG 标记无效");
      while (bytes[at] === 255) at++;
      const marker = bytes[at++];
      if (marker === 218 || marker === 217) { let end = bytes.length; for (let p = at; p + 1 < bytes.length; p++) if (bytes[p] === 255 && bytes[p + 1] === 217) { end = p + 2; break; } parts.push(bytes.subarray(start, end)); break; }
      if (marker === 1 || (marker >= 208 && marker <= 216)) { parts.push(bytes.subarray(start, at)); continue; }
      const length = bytes[at] * 256 + bytes[at + 1], end = at + length;
      if (length < 2 || end > bytes.length) throw httpError(400, "照片的 JPEG 片段无效");
      const prefix = new TextDecoder().decode(bytes.subarray(at + 2, Math.min(end, at + 15))), renderApp = (marker === 224 && /^(?:JFIF|JFXX)\0/.test(prefix)) || (marker === 226 && prefix.startsWith("ICC_PROFILE\0")) || (marker === 238 && prefix.startsWith("Adobe"));
      if (marker !== 254 && (!(marker >= 224 && marker <= 239) || renderApp)) parts.push(bytes.subarray(start, end));
      at = end;
    }
    return concatBytes(parts);
  }
  if (extension === "png") {
    if (new TextDecoder().decode(bytes.subarray(1, 4)) !== "PNG") throw httpError(400, "照片的 PNG 格式无效");
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), parts = [bytes.subarray(0, 8)];
    for (let at = 8; at + 12 <= bytes.length;) {
      const length = view.getUint32(at), end = at + length + 12, kind = new TextDecoder().decode(bytes.subarray(at + 4, at + 8));
      if (end > bytes.length) throw httpError(400, "照片的 PNG 数据无效");
      if (["IHDR", "PLTE", "IDAT", "IEND", "tRNS", "gAMA", "cHRM", "sRGB", "iCCP", "sBIT", "bKGD", "pHYs", "hIST", "sPLT", "acTL", "fcTL", "fdAT"].includes(kind)) parts.push(bytes.subarray(at, end));
      if (kind === "IHDR" && exif.length) parts.push(pngExifChunk(exif.subarray(6)));
      at = end; if (kind === "IEND") break;
    }
    return concatBytes(parts);
  }
  if (extension === "webp") {
    if (new TextDecoder().decode(bytes.subarray(0, 4)) !== "RIFF" || new TextDecoder().decode(bytes.subarray(8, 12)) !== "WEBP") throw httpError(400, "照片的 WebP 格式无效");
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), parts = []; let hasExtended = false;
    for (let at = 12; at + 8 <= bytes.length;) {
      const length = view.getUint32(at + 4, true), end = at + 8 + length + (length & 1), kind = new TextDecoder().decode(bytes.subarray(at, at + 4));
      if (end > bytes.length) throw httpError(400, "照片的 WebP 数据无效");
      if (["VP8X", "VP8 ", "VP8L", "ALPH", "ANIM", "ANMF", "ICCP"].includes(kind)) { const chunk = bytes.slice(at, end); if (kind === "VP8X") { hasExtended = true; chunk[8] &= ~12; if (exif.length) chunk[8] |= 8; } parts.push(chunk); }
      at = end;
    }
    if (exif.length && hasExtended) { const header = new Uint8Array(8); header.set(new TextEncoder().encode("EXIF")); new DataView(header.buffer).setUint32(4, exif.length, true); parts.push(header, exif); }
    const payload = concatBytes([new TextEncoder().encode("WEBP"), ...parts]), header = new Uint8Array(8); header.set(new TextEncoder().encode("RIFF")); new DataView(header.buffer).setUint32(4, payload.length, true); return concatBytes([header, payload]);
  }
  if (extension === "gif") {
    if (new TextDecoder().decode(bytes.subarray(0, 3)) !== "GIF") throw httpError(400, "照片的 GIF 格式无效");
    let at = 13 + ((bytes[10] & 128) ? 3 * (2 ** ((bytes[10] & 7) + 1)) : 0); const parts = [bytes.subarray(0, at)];
    const subblocks = start => { while (start < bytes.length) { const length = bytes[start]; start += length + 1; if (!length) return start; } throw httpError(400, "照片的 GIF 数据无效"); };
    while (at < bytes.length) { const start = at, marker = bytes[at]; if (marker === 59) { parts.push(bytes.subarray(at, at + 1)); break; } if (marker === 33) { const label = bytes[at + 1], app = new TextDecoder().decode(bytes.subarray(at + 3, at + 14)); at = subblocks(at + 2); if (label === 249 || (label === 255 && ["NETSCAPE2.0", "ANIMEXTS1.0"].includes(app))) parts.push(bytes.subarray(start, at)); } else if (marker === 44) { const packed = bytes[at + 9]; at += 10 + ((packed & 128) ? 3 * (2 ** ((packed & 7) + 1)) : 0); at = subblocks(at + 1); parts.push(bytes.subarray(start, at)); } else throw httpError(400, "照片的 GIF 区块无效"); }
    return concatBytes(parts);
  }
  throw httpError(400, "照片格式不支持安全处理，请先转为 JPEG、PNG 或 WebP");
}
function pngExifChunk(payload) {
  const out = new Uint8Array(payload.length + 12), view = new DataView(out.buffer); view.setUint32(0, payload.length); out.set(new TextEncoder().encode("eXIf"), 4); out.set(payload, 8);
  let crc = 0xffffffff; for (const byte of out.subarray(4, out.length - 4)) { crc ^= byte; for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); } view.setUint32(out.length - 4, (crc ^ 0xffffffff) >>> 0); return out;
}
function sanitizeVideoBytes(bytes) {
  const out = bytes.slice(), view = new DataView(out.buffer), containers = new Set(["moov", "trak", "mdia", "minf", "stbl", "edts", "dinf", "mvex", "moof", "traf"]);
  const atoms = (start, limit, depth = 0) => { if (depth > 12) throw httpError(400, "实况视频的结构过深"); for (let at = start; at + 8 <= limit;) { let length = view.getUint32(at), header = 8; const kind = new TextDecoder().decode(out.subarray(at + 4, at + 8)); if (length === 1) { length = Number(view.getBigUint64(at + 8)); header = 16; } else if (!length) length = limit - at; if (length < header || at + length > limit) throw httpError(400, "实况视频的数据结构无效"); if (["udta", "meta", "uuid", "XMP_"].includes(kind)) { out.set(new TextEncoder().encode("free"), at + 4); out.fill(0, at + header, at + length); } else if (containers.has(kind)) atoms(at + header, at + length, depth + 1); at += length; } };
  atoms(0, out.length); return out;
}
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
function fileExtension(name) { return String(name || "").split(".").pop().toLowerCase(); }
function mediaKindFromName(name) { const ext = fileExtension(name); return IMAGE_EXTENSIONS.has(ext) ? "image" : VIDEO_EXTENSIONS.has(ext) ? "video" : ""; }
function mediaKind(file) { return IMAGE_TYPES.has(file.type) || IMAGE_EXTENSIONS.has(fileExtension(file.name)) ? "image" : VIDEO_TYPES.has(file.type) || VIDEO_EXTENSIONS.has(fileExtension(file.name)) ? "video" : ""; }
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
async function gitBlobSha(bytes) {
  const header = new TextEncoder().encode(`blob ${bytes.byteLength}\0`);
  const payload = new Uint8Array(header.byteLength + bytes.byteLength);
  payload.set(header); payload.set(bytes, header.byteLength);
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-1", payload));
  return [...digest].map(value => value.toString(16).padStart(2, "0")).join("");
}
