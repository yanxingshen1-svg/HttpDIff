# httpdiff

**httpdiff** 是一个命令行工具，用于对比两个环境返回的 HTTP API 响应是否一致。它会向两个 URL 分别发请求，递归对比 JSON 数据的差异，并高亮显示变化——适用于回归测试、API 迁移验证和 CI/CD 流水线。

```bash
httpdiff --base https://old-api.example.com/users \
         --target https://new-api.example.com/users \
         --ignore "timestamp,request_id"
```

## 安装

```bash
pip install httpdiff
```

或者从源码安装：

```bash
git clone https://github.com/YOUR_USERNAME/httpdiff.git
cd httpdiff
pip install -e .
```

## 使用方式

### 对比两个接口

```bash
httpdiff --base https://api-v1.example.com/users/1 \
         --target https://api-v2.example.com/users/1
```

### 自定义请求方法和请求体

```bash
httpdiff -b https://old-api.example.com/orders \
         -t https://new-api.example.com/orders \
         -m POST \
         -d '{"id": 123}'
```

### 忽略特定字段

```bash
httpdiff -b https://api.example.com/users/1 \
         -t https://api.example.com/users/2 \
         -i id -i updated_at -i "*.timestamp"
```

### 输出 HTML 报告

```bash
httpdiff -b https://api-v1.example.com/users \
         -t https://api-v2.example.com/users \
         -f html -o report.html
```

### 输出 JSON 格式（方便脚本处理）

```bash
httpdiff -b https://api-v1.example.com/users \
         -t https://api-v2.example.com/users \
         -f json
```

### 使用配置文件

```bash
httpdiff --config examples/config.json
```

## 输出格式

| 格式 | 说明 |
|------|------|
| `terminal`（默认） | 终端彩色输出（基于 `rich`） |
| `html` | 独立 HTML 报告（浏览器打开查看） |
| `json` | 结构化 JSON，供 CI/脚本调用 |

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 无差异 |
| 1 | 发现差异或发生错误 |

## 工作原理

```
┌───────────────────┐     ┌───────────────────┐
│  基线接口          │     │  目标接口          │
│  GET /users/1     │     │  GET /users/1     │
└────────┬──────────┘     └────────┬──────────┘
         │                         │
         ▼                         ▼
┌───────────────────┐     ┌───────────────────┐
│  发起 HTTP 请求   │     │  发起 HTTP 请求   │
│  (httpx)          │     │  (httpx)          │
└────────┬──────────┘     └────────┬──────────┘
         │                         │
         └──────────┬──────────────┘
                    ▼
        ┌───────────────────────┐
        │  递归 JSON 对比       │
        │  (新增 / 删除 /       │
        │   修改 / 类型变化)     │
        └──────────┬────────────┘
                   ▼
        ┌───────────────────────┐
        │  结果输出              │
        │  终端 / HTML / JSON   │
        └───────────────────────┘
```

## 差异类型

- **added**（新增）：目标接口有、基线接口没有的字段
- **removed**（删除）：基线接口有、目标接口没有的字段
- **changed**（修改）：字段值发生变化（包括 `null` ↔ 值）
- **type_changed**（类型变化）：字段类型改变（例如字符串变数字）

数组对比按索引一一对应：`items[0]` 对比 `items[0]`。

## 忽略规则

| 规则 | 匹配对象 |
|------|----------|
| `id` | 任意层级的 `id` 字段 |
| `meta.version` | 精确路径 `root.meta.version` |
| `*.updated_at` | 任意层级的 `updated_at` 字段 |

## 开发

```bash
# 运行测试
python -m pytest tests/ -v

# 运行测试并查看覆盖率
python -m pytest tests/ --cov=httpdiff -v
```
