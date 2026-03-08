# 工具管理说明

## 目录结构

```
tools/
├── builtin/              # 内置工具目录
│   ├── linux/           # Linux 版本工具
│   │   ├── x86_64/      # x86_64 架构
│   │   └── arm64/       # ARM64 架构
│   ├── darwin/          # macOS 版本工具
│   │   ├── x86_64/      # Intel Mac
│   │   └── arm64/       # Apple Silicon (M1/M2)
│   └── windows/          # Windows 版本工具
│       └── x86_64/      # x86_64 架构
├── plugins/             # 用户上传的自定义工具（按租户ID分目录）
│   └── {tenant_id}/
└── README.md            # 本文件
```

## 内置工具推荐版本

### 1. Nmap
- **Linux**: 从 [nmap.org](https://nmap.org/download.html) 下载预编译二进制文件
  - x86_64: `nmap-7.94-x86_64-linux.tar.bz2`
  - arm64: `nmap-7.94-aarch64-linux.tar.bz2`
- **macOS**: 使用 Homebrew 安装或下载预编译版本
  - `brew install nmap` 或下载 macOS 版本
- **Windows**: 下载 Windows 安装包或便携版

### 2. Subfinder
- **GitHub**: https://github.com/projectdiscovery/subfinder/releases
- **推荐版本**: 最新稳定版
- **下载**: 根据平台下载对应的二进制文件
  - Linux: `subfinder_*_linux_amd64.tar.gz` 或 `subfinder_*_linux_arm64.tar.gz`
  - macOS: `subfinder_*_darwin_amd64.tar.gz` 或 `subfinder_*_darwin_arm64.tar.gz`
  - Windows: `subfinder_*_windows_amd64.zip`

### 3. HTTPX
- **GitHub**: https://github.com/projectdiscovery/httpx/releases
- **推荐版本**: 最新稳定版
- **下载**: 根据平台下载对应的二进制文件

### 4. Nuclei
- **GitHub**: https://github.com/projectdiscovery/nuclei/releases
- **推荐版本**: 最新稳定版
- **下载**: 根据平台下载对应的二进制文件

## 安装步骤

### Linux (推荐使用 Linux 版本)

1. 下载工具到对应目录：
```bash
# 创建目录
mkdir -p tools/builtin/linux/x86_64
mkdir -p tools/builtin/linux/arm64

# 下载 nmap (示例)
cd tools/builtin/linux/x86_64
wget https://nmap.org/dist/nmap-7.94-x86_64-linux.tar.bz2
tar -xjf nmap-7.94-x86_64-linux.tar.bz2
# 将 nmap 二进制文件复制到当前目录
cp nmap-7.94/bin/nmap .
chmod +x nmap

# 下载 subfinder
wget https://github.com/projectdiscovery/subfinder/releases/latest/download/subfinder_*_linux_amd64.tar.gz
tar -xzf subfinder_*_linux_amd64.tar.gz
chmod +x subfinder
```

### macOS

1. 使用 Homebrew（推荐）：
```bash
brew install nmap subfinder httpx nuclei
```

2. 或手动下载到目录：
```bash
mkdir -p tools/builtin/darwin/arm64  # Apple Silicon
# 或
mkdir -p tools/builtin/darwin/x86_64  # Intel Mac
```

### Windows

1. 下载工具到：
```
tools/builtin/windows/x86_64/
```

## 工具执行优先级

系统会按以下顺序查找工具：

1. **数据库配置的工具路径**（用户上传的自定义工具）
2. **内置工具目录**（根据当前平台和架构自动选择）
3. **系统 PATH**（如果前两者都找不到，尝试系统命令）

## 注意事项

- 确保工具文件有执行权限（Linux/macOS）
- Windows 工具需要 `.exe` 扩展名
- 建议使用最新稳定版本的工具
- 定期更新工具以获得最新功能和安全修复

