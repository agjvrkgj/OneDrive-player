#!/bin/bash
#
# OneDrive Player - 一键安装/卸载脚本
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/onedrive-player"
SERVICE_NAME="onedrive-player"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PLAYER_APP_FILE="player_app.py" # Assuming this script is in the same directory as player_app.py
REPO_URL="https://github.com/agjvrkgj/OneDrive-player.git"
RAW_URL="https://raw.githubusercontent.com/agjvrkgj/OneDrive-player/main"

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════╗"
    echo "║        OneDrive Player Setup         ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
}

# ── 配置 Azure OneDrive ──────────────────────────────────

setup_azure_onedrive() {
    echo ""
    echo -e "${YELLOW}以下信息在 Azure Portal (portal.azure.com) 获取：${NC}"
    echo -e "${YELLOW}Azure Portal → Azure Active Directory → 应用注册 → 你的应用${NC}"
    echo ""
    read -p "Azure 租户 ID (概述页面的 '目录(租户) ID'): " AZ_TENANT
    read -p "Azure 应用(客户端) ID (概述页面的 '应用程序(客户端) ID'): " AZ_CLIENT_ID
    read -p "Azure 客户端密钥 (证书和密钥 → 客户端密钥的 '值'): " AZ_CLIENT_SECRET
    echo ""
    read -p "OneDrive 用户邮箱 (用于指定播放哪个用户的网盘视频): " DRIVE_USER_EMAIL

    cat > "${INSTALL_DIR}/azure_config.json" << CFGEOF
{
    "tenant_id": "${AZ_TENANT}",
    "client_id": "${AZ_CLIENT_ID}",
    "client_secret": "${AZ_CLIENT_SECRET}",
    "grant_mode": "client_credentials",
    "drive_user": "${DRIVE_USER_EMAIL}"
}
CFGEOF

    chmod 600 "${INSTALL_DIR}/azure_config.json"
    log_info "Azure OneDrive 配置已保存到 azure_config.json"
}

# ── 安装 ──────────────────────────────────────────────────

install() {
    print_banner
    check_root
    echo -e "${GREEN}开始安装 OneDrive Player...${NC}\n"

    if ! command -v apt-get &>/dev/null; then
        log_error "仅支持 Debian/Ubuntu 系统"
        exit 1
    fi

    # 1. 安装系统依赖
    log_info "安装系统依赖..."
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip git > /dev/null 2>&1
    log_info "系统依赖安装完成"

    # 2. 安装 Python 依赖
    log_info "安装 Python 依赖..."
    pip3 install --break-system-packages -q flask requests > /dev/null 2>&1 || \
    pip3 install -q flask requests
    log_info "Python 依赖安装完成"

    # 3. 创建安装目录
    mkdir -p "${INSTALL_DIR}"

    # 4. 复制应用文件
    log_info "复制应用文件..."
    cp "${PLAYER_APP_FILE}" "${INSTALL_DIR}/"
    cp "onedrive-player.service" "${INSTALL_DIR}/"

    # 5. 配置 Azure OneDrive
    setup_azure_onedrive

    # 6. 安装 systemd 服务
    log_info "安装 systemd 服务..."
    cp "${INSTALL_DIR}/onedrive-player.service" "$SERVICE_FILE"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME" > /dev/null 2>&1
    systemctl start "$SERVICE_NAME"
    log_info "OneDrive Player 服务已启动"

    # 7. 显示访问地址
    echo ""
    log_info "✅ 安装完成！"
    log_info "访问地址: http://$(hostname -I | awk '{print $1}'):8090"
    echo ""
    echo "  服务状态: systemctl status ${SERVICE_NAME}"
    echo "  查看日志: journalctl -u ${SERVICE_NAME} -f"
    echo ""
}

# ── 卸载 ──────────────────────────────────────────────────

uninstall() {
    print_banner
    check_root
    echo -e "${YELLOW}开始卸载 OneDrive Player...${NC}\n"

    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "停止服务..."
        systemctl stop "$SERVICE_NAME"
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "禁用服务..."
        systemctl disable "$SERVICE_NAME"
    fi

    if [ -f "$SERVICE_FILE" ]; then
        log_info "删除 systemd 服务文件..."
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
    fi

    if [ -d "$INSTALL_DIR" ]; then
        echo ""
        read -p "是否删除安装目录 ${INSTALL_DIR} (包含配置)？[y/N]: " del_dir
        if [[ "$del_dir" =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            log_info "已删除 ${INSTALL_DIR}"
        else
            log_info "保留 ${INSTALL_DIR}"
        fi
    fi

    echo ""
    log_info "✅ 卸载完成！"
}

# ── 入口 ──────────────────────────────────────────────────

case "${1:-}" in
    install)
        install
        ;;
    uninstall|remove|delete)
        uninstall
        ;;
    *)
        print_banner
        echo "请选择操作:"
        echo ""
        echo "  1) 安装 OneDrive Player"
        echo "  2) 卸载 OneDrive Player"
        echo ""
        read -p "输入选项 [1/2]: " choice
        case "$choice" in
            1) install ;;
            2) uninstall ;;
            *) echo "无效选项"; exit 1 ;;
        esac
        ;;
esac