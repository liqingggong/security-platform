# 内置工具安装指南

## 工具存储位置

### 推荐目录结构

```
security_platform/
└── tools/
    ├── builtin/              # 内置工具目录（推荐）
    │   ├── linux/
    │   │   ├── x86_64/      # Linux x86_64 架构
    │   │   │   ├── nmap
    │   │   │   ├── subfinder
    │   │   │   ├── httpx
    │   │   │   └── nuclei
    │   │   └── arm64/       # Linux ARM64 架构
    │   │       ├── nmap
    │   │       ├── subfinder
    │   │       ├── httpx
    │   │       └── nuclei
    │   ├── darwin/          # macOS
    │   │   ├── x86_64/      # Intel Mac
    │   │   └── arm64/       # Apple Silicon (M1/M2/M3)
    │   └── windows/         # Windows
    │       └── x86_64/
    │           ├── nmap.exe
    │           ├── subfinder.exe
    │           ├── httpx.exe
    │           └── nuclei.exe
    └── plugins/             # 用户上传的自定义工具
        └── {tenant_id}/
```

## 安装方式说明

系统支持两种工具安装方式：

### 方式一：系统安装（推荐，最简单）

**优点**：
- ✅ 最简单，一条命令搞定
- ✅ 自动处理依赖关系
- ✅ 自动更新和维护
- ✅ 系统统一管理

**安装方法**：

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install nmap subfinder httpx nuclei
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install nmap
# subfinder, httpx, nuclei 需要从 GitHub 下载或使用其他方式安装
```

**macOS**:
```bash
brew install nmap subfinder httpx nuclei
```

**Windows**:
```bash
# 使用 Chocolatey
choco install nmap

# 或使用 Scoop
scoop install nmap
```

安装完成后，系统会自动从 PATH 中找到这些工具，**无需任何额外配置**！

### 方式二：项目目录安装（适合需要特定版本或离线环境）

**优点**：
- ✅ 版本可控
- ✅ 不依赖系统环境
- ✅ 适合 Docker 容器化部署

**安装步骤（Linux x86_64）**:
```bash
# 创建目录
mkdir -p tools/builtin/linux/x86_64

# 下载并解压 nmap
cd tools/builtin/linux/x86_64
wget https://nmap.org/dist/nmap-7.94-x86_64-linux.tar.bz2
tar -xjf nmap-7.94-x86_64-linux.tar.bz2

# 复制二进制文件
cp nmap-7.94/bin/nmap .
chmod +x nmap

# 清理
rm -rf nmap-7.94 nmap-7.94-x86_64-linux.tar.bz2
```

## 版本选择建议

### 1. **Nmap** - 端口扫描工具

**推荐版本**: 最新稳定版（当前推荐 7.94+）

**推荐安装方式**: 
- **Linux/macOS**: 使用系统包管理器（`apt`, `yum`, `brew`）**最简单**
- **Windows**: 下载安装包或使用包管理器

**如果使用系统安装**：
```bash
# Linux
sudo apt install nmap

# macOS  
brew install nmap

# 验证安装
nmap --version
```

**如果使用项目目录安装**：
- 下载预编译二进制文件到 `tools/builtin/{platform}/{arch}/nmap`
- 确保文件有执行权限：`chmod +x nmap`

### 2. **Subfinder** - 子域名枚举工具

**推荐版本**: 最新稳定版

**下载地址**: https://github.com/projectdiscovery/subfinder/releases

**安装步骤（Linux x86_64）**:
```bash
cd tools/builtin/linux/x86_64
wget https://github.com/projectdiscovery/subfinder/releases/latest/download/subfinder_*_linux_amd64.tar.gz
tar -xzf subfinder_*_linux_amd64.tar.gz
chmod +x subfinder
rm subfinder_*_linux_amd64.tar.gz
```

### 3. **HTTPX** - HTTP 存活检测工具

**推荐版本**: 最新稳定版

**下载地址**: https://github.com/projectdiscovery/httpx/releases

**安装步骤（Linux x86_64）**:
```bash
cd tools/builtin/linux/x86_64
wget https://github.com/projectdiscovery/httpx/releases/latest/download/httpx_*_linux_amd64.zip
unzip httpx_*_linux_amd64.zip
chmod +x httpx
rm httpx_*_linux_amd64.zip
```

### 4. **Nuclei** - 漏洞扫描工具

**推荐版本**: 最新稳定版

**下载地址**: wget

**安装步骤（Linux x86_64）**:
```bash
cd tools/builtin/linux/x86_64
wget https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_*_linux_amd64.zip
unzip nuclei_*_linux_amd64.zip
chmod +x nuclei
rm nuclei_*_linux_amd64.zip
```

## 工具查找优先级

系统会按以下顺序查找工具：

1. **用户上传的自定义工具**（`tools/plugins/{tenant_id}/`）
2. **项目内置工具目录**（`tools/builtin/{platform}/{arch}/`）
3. **系统 PATH**（如果前两者都找不到，自动使用系统安装的工具）✅

**这意味着**：如果你使用系统包管理器安装了工具（如 `apt install nmap` 或 `brew install nmap`），系统会自动找到并使用，**无需任何额外配置**！

## 推荐安装方案

### 生产环境（Linux 服务器）

**方案一：系统安装（推荐）**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nmap

# 其他工具需要从 GitHub 下载或使用其他方式
```

**方案二：项目目录安装**
- 适合需要特定版本
- 适合 Docker 容器化部署
- 下载预编译二进制文件到项目目录

### 开发环境（macOS）

**强烈推荐使用 Homebrew**：
```bash
brew install nmap subfinder httpx nuclei
```

安装完成后，系统会自动从 PATH 中找到这些工具，无需任何配置！

## 快速安装脚本

### macOS（使用 Homebrew，推荐）

```bash
# 一键安装所有工具
brew install nmap subfinder httpx nuclei

# 验证安装
nmap --version
subfinder -version
httpx -version
nuclei -version
```

### Linux（系统安装 + 手动下载）

```bash
# 安装 nmap（系统包管理器）
sudo apt install nmap  # Ubuntu/Debian
# 或
sudo yum install nmap  # CentOS/RHEL

# 其他工具需要从 GitHub 下载（见下方脚本）
```

### Linux（项目目录安装脚本）

创建 `tools/install_builtin_tools.sh`:

```bash
#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_DIR="$BASE_DIR/tools/builtin/linux/x86_64"
mkdir -p "$TOOLS_DIR"
cd "$TOOLS_DIR"

echo "正在下载 Nmap..."
wget -q https://nmap.org/dist/nmap-7.94-x86_64-linux.tar.bz2
tar -xjf nmap-7.94-x86_64-linux.tar.bz2
cp nmap-7.94/bin/nmap .
chmod +x nmap
rm -rf nmap-7.94 nmap-7.94-x86_64-linux.tar.bz2

echo "正在下载 Subfinder..."
wget -q https://github.com/projectdiscovery/subfinder/releases/latest/download/subfinder_*_linux_amd64.tar.gz
tar -xzf subfinder_*_linux_amd64.tar.gz
chmod +x subfinder
rm subfinder_*_linux_amd64.tar.gz

echo "正在下载 HTTPX..."
wget -q https://github.com/projectdiscovery/httpx/releases/latest/download/httpx_*_linux_amd64.zip
unzip -q httpx_*_linux_amd64.zip
chmod +x httpx
rm httpx_*_linux_amd64.zip

echo "正在下载 Nuclei..."
wget -q https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_*_linux_amd64.zip
unzip -q nuclei_*_linux_amd64.zip
chmod +x nuclei
rm nuclei_*_linux_amd64.zip

echo "所有工具安装完成！"
```

## 验证安装

### 如果使用系统安装

```bash
# 直接验证（工具在 PATH 中）
nmap --version
subfinder -version
httpx -version
nuclei -version
```

### 如果使用项目目录安装

```bash
# 检查工具是否可执行
cd tools/builtin/linux/x86_64
./nmap --version
./subfinder -version
./httpx -version
./nuclei -version
```

## 注意事项

1. **系统安装（推荐）**：
   - ✅ 最简单，一条命令搞定
   - ✅ 自动处理依赖关系
   - ✅ 系统会自动从 PATH 中找到工具
   - ⚠️ 需要系统管理员权限

2. **项目目录安装**：
   - ✅ 版本可控
   - ✅ 不依赖系统环境
   - ✅ 适合 Docker 容器化部署
   - ⚠️ 需要手动下载和管理
   - ⚠️ 需要确保文件有执行权限（`chmod +x`）

3. **依赖关系**：
   - nmap 可能需要系统库（如 libpcap）
   - 使用系统包管理器安装会自动处理依赖
   - 手动安装需要确保所有依赖都已安装

4. **更新维护**：
   - 系统安装：使用包管理器更新（`apt upgrade`, `brew upgrade`）
   - 项目目录：手动下载新版本替换

## 总结

**对于大多数用户，推荐使用系统包管理器安装**：
- macOS: `brew install nmap subfinder httpx nuclei`
- Linux: `sudo apt install nmap` + 手动下载其他工具

系统会自动从 PATH 中找到这些工具，**无需任何额外配置**！

