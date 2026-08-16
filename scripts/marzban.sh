#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt"
if [ -z "$APP_NAME" ]; then
    APP_NAME="marzban"
fi
APP_DIR="$INSTALL_DIR/$APP_NAME"
DATA_DIR="/var/lib/$APP_NAME"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"
ENV_FILE="$APP_DIR/.env"
LAST_XRAY_CORES=10
# =============================================================================
# Fork configuration
# Override at runtime, e.g. MARZBAN_GITHUB_REPO=another-user/Marzban marzban install
# =============================================================================
MARZBAN_GITHUB_REPO="${MARZBAN_GITHUB_REPO:-smorad3363/Marzban}"
MARZBAN_GITHUB_BRANCH="${MARZBAN_GITHUB_BRANCH:-master}"
MARZBAN_SCRIPTS_PATH="${MARZBAN_SCRIPTS_PATH:-scripts/marzban.sh}"
MARZBAN_DOCKER_IMAGE="${MARZBAN_DOCKER_IMAGE:-ghcr.io/smorad3363/marzban}"
MARZBAN_FILES_URL_PREFIX="https://raw.githubusercontent.com/${MARZBAN_GITHUB_REPO}/${MARZBAN_GITHUB_BRANCH}"
MARZBAN_SCRIPT_URL="https://github.com/${MARZBAN_GITHUB_REPO}/raw/${MARZBAN_GITHUB_BRANCH}/${MARZBAN_SCRIPTS_PATH}"
MARZBAN_RELEASES_API="https://api.github.com/repos/${MARZBAN_GITHUB_REPO}/releases"

marzban_docker_image() {
    local version="${1:-latest}"
    echo "${MARZBAN_DOCKER_IMAGE}:${version}"
}

colorized_echo() {
    local color=$1
    local text=$2
    
    case $color in
        "red")
        printf "\e[91m${text}\e[0m\n";;
        "green")
        printf "\e[92m${text}\e[0m\n";;
        "yellow")
        printf "\e[93m${text}\e[0m\n";;
        "blue")
        printf "\e[94m${text}\e[0m\n";;
        "magenta")
        printf "\e[95m${text}\e[0m\n";;
        "cyan")
        printf "\e[96m${text}\e[0m\n";;
        *)
            echo "${text}"
        ;;
    esac
}

check_running_as_root() {
    if [ "$(id -u)" != "0" ]; then
        colorized_echo red "This command must be run as root."
        exit 1
    fi
}

detect_os() {
    # Detect the operating system
    if [ -f /etc/lsb-release ]; then
        OS=$(lsb_release -si)
    elif [ -f /etc/os-release ]; then
        OS=$(awk -F= '/^NAME/{print $2}' /etc/os-release | tr -d '"')
    elif [ -f /etc/redhat-release ]; then
        OS=$(cat /etc/redhat-release | awk '{print $1}')
    elif [ -f /etc/arch-release ]; then
        OS="Arch"
    else
        colorized_echo red "Unsupported operating system"
        exit 1
    fi
}


detect_and_update_package_manager() {
    colorized_echo blue "Updating package manager"
    if [[ "$OS" == "Ubuntu"* ]] || [[ "$OS" == "Debian"* ]]; then
        PKG_MANAGER="apt-get"
        $PKG_MANAGER update
    elif [[ "$OS" == "CentOS"* ]] || [[ "$OS" == "AlmaLinux"* ]]; then
        PKG_MANAGER="yum"
        $PKG_MANAGER update -y
        $PKG_MANAGER install -y epel-release
    elif [ "$OS" == "Fedora"* ]; then
        PKG_MANAGER="dnf"
        $PKG_MANAGER update
    elif [ "$OS" == "Arch" ]; then
        PKG_MANAGER="pacman"
        $PKG_MANAGER -Sy
    elif [[ "$OS" == "openSUSE"* ]]; then
        PKG_MANAGER="zypper"
        $PKG_MANAGER refresh
    else
        colorized_echo red "Unsupported operating system"
        exit 1
    fi
}

install_package () {
    if [ -z $PKG_MANAGER ]; then
        detect_and_update_package_manager
    fi
    
    PACKAGE=$1
    colorized_echo blue "Installing $PACKAGE"
    if [[ "$OS" == "Ubuntu"* ]] || [[ "$OS" == "Debian"* ]]; then
        $PKG_MANAGER -y install "$PACKAGE"
    elif [[ "$OS" == "CentOS"* ]] || [[ "$OS" == "AlmaLinux"* ]]; then
        $PKG_MANAGER install -y "$PACKAGE"
    elif [ "$OS" == "Fedora"* ]; then
        $PKG_MANAGER install -y "$PACKAGE"
    elif [ "$OS" == "Arch" ]; then
        $PKG_MANAGER -S --noconfirm "$PACKAGE"
    else
        colorized_echo red "Unsupported operating system"
        exit 1
    fi
}

install_docker() {
    # Install Docker and Docker Compose using the official installation script
    colorized_echo blue "Installing Docker"
    curl -fsSL https://get.docker.com | sh
    colorized_echo green "Docker installed successfully"
}

detect_compose() {
    # Check if docker compose command exists
    if docker compose version >/dev/null 2>&1; then
        COMPOSE='docker compose'
    elif docker-compose version >/dev/null 2>&1; then
        COMPOSE='docker-compose'
    else
        colorized_echo red "docker compose not found"
        exit 1
    fi
}

install_marzban_script_from_repo() {
    colorized_echo blue "Installing marzban script from ${MARZBAN_GITHUB_REPO}"
    curl -sSL "$MARZBAN_SCRIPT_URL" | install -m 755 /dev/stdin /usr/local/bin/marzban
    colorized_echo green "marzban script installed successfully"
}

is_marzban_installed() {
    if [ -d $APP_DIR ]; then
        return 0
    else
        return 1
    fi
}

identify_the_operating_system_and_architecture() {
    if [[ "$(uname)" == 'Linux' ]]; then
        case "$(uname -m)" in
            'i386' | 'i686')
                ARCH='32'
            ;;
            'amd64' | 'x86_64')
                ARCH='64'
            ;;
            'armv5tel')
                ARCH='arm32-v5'
            ;;
            'armv6l')
                ARCH='arm32-v6'
                grep Features /proc/cpuinfo | grep -qw 'vfp' || ARCH='arm32-v5'
            ;;
            'armv7' | 'armv7l')
                ARCH='arm32-v7a'
                grep Features /proc/cpuinfo | grep -qw 'vfp' || ARCH='arm32-v5'
            ;;
            'armv8' | 'aarch64')
                ARCH='arm64-v8a'
            ;;
            'mips')
                ARCH='mips32'
            ;;
            'mipsle')
                ARCH='mips32le'
            ;;
            'mips64')
                ARCH='mips64'
                lscpu | grep -q "Little Endian" && ARCH='mips64le'
            ;;
            'mips64le')
                ARCH='mips64le'
            ;;
            'ppc64')
                ARCH='ppc64'
            ;;
            'ppc64le')
                ARCH='ppc64le'
            ;;
            'riscv64')
                ARCH='riscv64'
            ;;
            's390x')
                ARCH='s390x'
            ;;
            *)
                echo "error: The architecture is not supported."
                exit 1
            ;;
        esac
    else
        echo "error: This operating system is not supported."
        exit 1
    fi
}

send_backup_to_telegram() {
    if [ -f "$ENV_FILE" ]; then
        while IFS='=' read -r key value; do
            if [[ -z "$key" || "$key" =~ ^# ]]; then
                continue
            fi
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
                export "$key"="$value"
            else
                colorized_echo yellow "Skipping invalid line in .env: $key=$value"
            fi
        done < "$ENV_FILE"
    else
        colorized_echo red "Environment file (.env) not found."
        exit 1
    fi

    if [ "$BACKUP_SERVICE_ENABLED" != "true" ]; then
        colorized_echo yellow "Backup service is not enabled. Skipping Telegram upload."
        return
    fi

    local server_ip=$(curl -s ifconfig.me || echo "Unknown IP")
    local latest_backup=$(ls -t "$APP_DIR/backup" | head -n 1)
    local backup_path="$APP_DIR/backup/$latest_backup"

    if [ ! -f "$backup_path" ]; then
        colorized_echo red "No backups found to send."
        return
    fi

    local backup_size=$(du -m "$backup_path" | cut -f1)
    local split_dir="/tmp/marzban_backup_split"
    local is_single_file=true

    mkdir -p "$split_dir"

    if [ "$backup_size" -gt 49 ]; then
        colorized_echo yellow "Backup is larger than 49MB. Splitting the archive..."
        split -b 49M "$backup_path" "$split_dir/part_"
        is_single_file=false
    else
        cp "$backup_path" "$split_dir/part_aa"
    fi


    local backup_time=$(date "+%Y-%m-%d %H:%M:%S %Z")


    for part in "$split_dir"/*; do
        local part_name=$(basename "$part")
        local custom_filename="backup_${part_name}.tar.gz"
        local caption="ğŸ“¦ *Backup Information*\nğŸŒ *Server IP*: \`${server_ip}\`\nğŸ“ *Backup File*: \`${custom_filename}\`\nâ° *Backup Time*: \`${backup_time}\`"
        curl -s -F chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
            -F document=@"$part;filename=$custom_filename" \
            -F caption="$(echo -e "$caption" | sed 's/-/\\-/g;s/\./\\./g;s/_/\\_/g')" \
            -F parse_mode="MarkdownV2" \
            "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendDocument" >/dev/null 2>&1 && \
        colorized_echo green "Backup part $custom_filename successfully sent to Telegram." || \
        colorized_echo red "Failed to send backup part $custom_filename to Telegram."
    done

    rm -rf "$split_dir"
}

send_backup_error_to_telegram() {
    local error_messages=$1
    local log_file=$2
    local server_ip=$(curl -s ifconfig.me || echo "Unknown IP")
    local error_time=$(date "+%Y-%m-%d %H:%M:%S %Z")
    local message="âš ï¸ *Backup Error Notification*\n"
    message+="ğŸŒ *Server IP*: \`${server_ip}\`\n"
    message+="âŒ *Errors*:\n\`${error_messages//_/\\_}\`\n"
    message+="â° *Time*: \`${error_time}\`"


    message=$(echo -e "$message" | sed 's/-/\\-/g;s/\./\\./g;s/_/\\_/g;s/(/\\(/g;s/)/\\)/g')

    local max_length=1000
    if [ ${#message} -gt $max_length ]; then
        message="${message:0:$((max_length - 50))}...\n\`[Message truncated]\`"
    fi


    curl -s -X POST "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendMessage" \
        -d chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
        -d parse_mode="MarkdownV2" \
        -d text="$message" >/dev/null 2>&1 && \
    colorized_echo green "Backup error notification sent to Telegram." || \
    colorized_echo red "Failed to send error notification to Telegram."


    if [ -f "$log_file" ]; then
        response=$(curl -s -w "%{http_code}" -o /tmp/tg_response.json \
            -F chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
            -F document=@"$log_file;filename=backup_error.log" \
            -F caption="ğŸ“œ *Backup Error Log* - ${error_time}" \
            "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendDocument")

        http_code="${response:(-3)}"
        if [ "$http_code" -eq 200 ]; then
            colorized_echo green "Backup error log sent to Telegram."
        else
            colorized_echo red "Failed to send backup error log to Telegram. HTTP code: $http_code"
            cat /tmp/tg_response.json
        fi
    else
        colorized_echo red "Log file not found: $log_file"
    fi
}





backup_service() {
    local telegram_bot_key=""
    local telegram_chat_id=""
    local cron_schedule=""
    local interval_hours=""

    colorized_echo blue "====================================="
    colorized_echo blue "      Welcome to Backup Service      "
    colorized_echo blue "====================================="

    if grep -q "BACKUP_SERVICE_ENABLED=true" "$ENV_FILE"; then
        telegram_bot_key=$(awk -F'=' '/^BACKUP_TELEGRAM_BOT_KEY=/ {print $2}' "$ENV_FILE")
        telegram_chat_id=$(awk -F'=' '/^BACKUP_TELEGRAM_CHAT_ID=/ {print $2}' "$ENV_FILE")
        cron_schedule=$(awk -F'=' '/^BACKUP_CRON_SCHEDULE=/ {print $2}' "$ENV_FILE" | tr -d '"')

        if [[ "$cron_schedule" == "0 0 * * *" ]]; then
            interval_hours=24
        else
            interval_hours=$(echo "$cron_schedule" | grep -oP '(?<=\*/)[0-9]+')
        fi

        colorized_echo green "====================================="
        colorized_echo green "Current Backup Configuration:"
        colorized_echo cyan "Telegram Bot API Key: $telegram_bot_key"
        colorized_echo cyan "Telegram Chat ID: $telegram_chat_id"
        colorized_echo cyan "Backup Interval: Every $interval_hours hour(s)"
        colorized_echo green "====================================="
        echo "Choose an option:"
        echo "1. Reconfigure Backup Service"
        echo "2. Remove Backup Service"
        echo "3. Exit"
        read -p "Enter your choice (1-3): " user_choice

        case $user_choice in
            1)
                colorized_echo yellow "Starting reconfiguration..."
                remove_backup_service
                ;;
            2)
                colorized_echo yellow "Removing Backup Service..."
                remove_backup_service
                return
                ;;
            3)
                colorized_echo yellow "Exiting..."
                return
                ;;
            *)
                colorized_echo red "Invalid choice. Exiting."
                return
                ;;
        esac
    else
        colorized_echo yellow "No backup service is currently configured."
    fi

    while true; do
        printf "Enter your Telegram bot API key: "
        read telegram_bot_key
        if [[ -n "$telegram_bot_key" ]]; then
            break
        else
            colorized_echo red "API key cannot be empty. Please try again."
        fi
    done

    while true; do
        printf "Enter your Telegram chat ID: "
        read telegram_chat_id
        if [[ -n "$telegram_chat_id" ]]; then
            break
        else
            colorized_echo red "Chat ID cannot be empty. Please try again."
        fi
    done

    while true; do
        printf "Set up the backup interval in hours (1-24):\n"
        read interval_hours

        if ! [[ "$interval_hours" =~ ^[0-9]+$ ]]; then
            colorized_echo red "Invalid input. Please enter a valid number."
            continue
        fi

        if [[ "$interval_hours" -eq 24 ]]; then
            cron_schedule="0 0 * * *"
            colorized_echo green "Setting backup to run daily at midnight."
            break
        fi

        if [[ "$interval_hours" -ge 1 && "$interval_hours" -le 23 ]]; then
            cron_schedule="0 */$interval_hours * * *"
            colorized_echo green "Setting backup to run every $interval_hours hour(s)."
            break
        else
            colorized_echo red "Invalid input. Please enter a number between 1-24."
        fi
    done

    sed -i '/^BACKUP_SERVICE_ENABLED/d' "$ENV_FILE"
    sed -i '/^BACKUP_TELEGRAM_BOT_KEY/d' "$ENV_FILE"
    sed -i '/^BACKUP_TELEGRAM_CHAT_ID/d' "$ENV_FILE"
    sed -i '/^BACKUP_CRON_SCHEDULE/d' "$ENV_FILE"

    {
        echo ""
        echo "# Backup service configuration"
        echo "BACKUP_SERVICE_ENABLED=true"
        echo "BACKUP_TELEGRAM_BOT_KEY=$telegram_bot_key"
        echo "BACKUP_TELEGRAM_CHAT_ID=$telegram_chat_id"
        echo "BACKUP_CRON_SCHEDULE=\"$cron_schedule\""
    } >> "$ENV_FILE"

    colorized_echo green "Backup service configuration saved in $ENV_FILE."
÷}|¶‰Ëkºwµç@€€™¤4(4(4(€€€¥˜½µµ…¹€µØÕÉ°€˜ø½‘•Ø½¹Õ±°ìÑ¡•¸4(€€€€€€€¥˜ÕÉ°€µ0€ˆ‘åÅ}ÕÉ°ˆ€µ¼€½ÕÍÈ½±½…°½‰¥¸½åÄìÑ¡•¸4(€€€€€€€€€€€¡µ½€­à€½ÕÍÈ½±½…°½‰¥¸½åÄ4(€€€€€€€€€€€½±½É¥é•‘}•¡¼É••¸€‰åÄ¥¹ÍÑ…±±•ÍÕ•ÍÍ™Õ±±ä„ˆ4(€€€€€€€•±Í”4(€€€€€€€€€€€½±½É¥é•‘}•¡¼É•€‰…¥±•Ñ¼‘½İ¹±½…åÄÕÍ¥¹œÕÉ°¸A±•…Í”¡•¬å½ÕÈ¥¹Ñ•É¹•Ğ½¹¹•Ñ¥½¸¸ˆ4(€€€€€€€€€€€•á¥Ğ€Ä4(€€€€€€€™¤4(€€€•±¥˜½µµ…¹€µØİ•Ğ€˜ø½‘•Ø½¹Õ±°ìÑ¡•¸4(€€€€€€€¥˜İ•Ğ€µ<€½ÕÍÈ½±½…°½‰¥¸½åÄ€ˆ‘åÅ}ÕÉ°ˆìÑ¡•¸4(€€€€€€€€€€€¡µ½€­à€½ÕÍÈ½±½…°½‰¥¸½åÄ4(€€€€€€€€€€€½±½É¥é•‘}•¡¼É••¸€‰åÄ¥¹ÍÑ…±±•ÍÕ•ÍÍ™Õ±±ä„ˆ4(€€€€€€€•±Í”4(€€€€€€€€€€€½±½É¥é•‘}•¡¼É•€‰…¥±•Ñ¼‘½İ¹±½…åÄÕÍ¥¹œİ•Ğ¸A±•…Í”¡•¬å½ÕÈ¥¹Ñ•É¹•Ğ½¹¹•Ñ¥½¸¸ˆ4(€€€€€€€€€€€•á¥Ğ€Ä4(€€€€€€€™¤4(€€€™¤4(4(4(€€€¥˜€„•¡¼€ˆ‘AQ ˆğÉ•À€µÄ€ˆ½ÕÍÈ½±½…°½‰¥¸ˆìÑ¡•¸4(€€€€€€€•áÁ½ÉĞAQ ôˆ½ÕÍÈ½±½…°½‰¥¸è‘AQ ˆ4(€€€™¤4(4(4(€€€¡…Í €µÈ4(4(€€€¥˜½µµ…¹€µØåÄ€˜ø½‘•Ø½¹Õ±°ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É••¸€‰åÄ¥ÌÉ•…‘äÑ¼ÕÍ”¸ˆ4(€€€•±¥˜l€µà€ˆ½ÕÍÈ½±½…°½‰¥¸½åÄˆtìÑ¡•¸4(4(€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰åÄ¥Ì¥¹ÍÑ…±±•…Ğ€½ÕÍÈ½±½…°½‰¥¸½åÄ‰ÕĞ¹½Ğ™½Õ¹¥¸AQ ¸ˆ4(€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰e½Ô…¸…‘€½ÕÍÈ½±½…°½‰¥¸Ñ¼å½ÕÈAQ •¹Ù¥É½¹µ•¹ĞÙ…É¥…‰±”¸ˆ4(€€€•±Í”4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰åÄ¥¹ÍÑ…±±…Ñ¥½¸™…¥±•¸A±•…Í”ÑÉä……¥¸½È¥¹ÍÑ…±°µ…¹Õ…±±ä¸ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4)ô4(4(4)‘½İ¹}µ…Éé‰…¸ ¤ì4(€€€€‘=5A=M€µ˜€‘=5A=M}%1€µÀ€ˆ‘AA}95ˆ‘½İ¸4)ô4(4(4(4)Í¡½İ}µ…Éé‰…¹}±½Ì ¤ì4(€€€€‘=5A=M€µ˜€‘=5A=M}%1€µÀ€ˆ‘AA}95ˆ±½Ì4)ô4(4)™½±±½İ}µ…Éé‰…¹}±½Ì ¤ì4(€€€€‘=5A=M€µ˜€‘=5A=M}%1€µÀ€ˆ‘AA}95ˆ±½Ì€µ˜4)ô4(4)µ…Éé‰…¹}±¤ ¤ì4(€€€€‘=5A=M€µ˜€‘=5A=M}%1€µÀ€ˆ‘AA}95ˆ•á•Œ€µ”1%}AI=}95ô‰µ…Éé‰…¸±¤ˆµ…Éé‰…¸µ…Éé‰…¸µ±¤€ˆ‘ ˆ4)ô4(4(4)¥Í}µ…Éé‰…¹}ÕÀ ¤ì4(€€€¥˜l€µè€ˆ ‘=5A=M€µ˜€‘=5A=M}%1ÁÌ€µÄ€µ„¤ˆtìÑ¡•¸4(€€€€€€€É•ÑÕÉ¸€Ä4(€€€•±Í”4(€€€€€€€É•ÑÕÉ¸€À4(€€€™¤4)ô4(4)Õ¹¥¹ÍÑ…±±}½µµ…¹ ¤ì4(€€€¡•­}ÉÕ¹¹¥¹}…Í}É½½Ğ4(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€É•…€µÀ€‰¼å½ÔÉ•…±±äİ…¹ĞÑ¼Õ¹¥¹ÍÑ…±°5…Éé‰…¸ü€¡ä½¸¤€ˆ4(€€€¥˜ml€„€‘IA1d€õøymeåtutìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰‰½ÉÑ•ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€¥˜¥Í}µ…Éé‰…¹}ÕÀìÑ¡•¸4(€€€€€€€‘½İ¹}µ…Éé‰…¸4(€€€™¤4(€€€Õ¹¥¹ÍÑ…±±}µ…Éé‰…¹}ÍÉ¥ÁĞ4(€€€Õ¹¥¹ÍÑ…±±}µ…Éé‰…¸4(€€€Õ¹¥¹ÍÑ…±±}µ…Éé‰…¹}‘½­•É}¥µ…•Ì4(€€€€4(€€€É•…€µÀ€‰¼å½Ôİ…¹ĞÑ¼É•µ½Ù”5…Éé‰…¸Ì‘…Ñ„™¥±•ÌÑ½¼€ ‘Q}%H¤ü€¡ä½¸¤€ˆ4(€€€¥˜ml€„€‘IA1d€õøymeåtutìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É••¸€‰5…Éé‰…¸Õ¹¥¹ÍÑ…±±•ÍÕ•ÍÍ™Õ±±äˆ4(€€€•±Í”4(€€€€€€€Õ¹¥¹ÍÑ…±±}µ…Éé‰…¹}‘…Ñ…}™¥±•Ì4(€€€€€€€½±½É¥é•‘}•¡¼É••¸€‰5…Éé‰…¸Õ¹¥¹ÍÑ…±±•ÍÕ•ÍÍ™Õ±±äˆ4(€€€™¤4)ô4(4)Õ¹¥¹ÍÑ…±±}µ…Éé‰…¹}ÍÉ¥ÁĞ ¤ì4(€€€¥˜l€µ˜€ˆ½ÕÍÈ½±½…°½‰¥¸½µ…Éé‰…¸ˆtìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰I•µ½Ù¥¹œµ…Éé‰…¸ÍÉ¥ÁĞˆ4(€€€€€€€É´€ˆ½ÕÍÈ½±½…°½‰¥¸½µ…Éé‰…¸ˆ4(€€€™¤4)ô4(4)Õ¹¥¹ÍÑ…±±}µ…Éé‰…¸ ¤ì4(€€€¥˜l€µ€ˆ‘AA}%HˆtìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰I•µ½Ù¥¹œ‘¥É•Ñ½Éäè€‘AA}%Hˆ4(€€€€€€€É´€µÈ€ˆ‘AA}%Hˆ4(€€€™¤4)ô4(4)Õ¹¥¹ÍÑ…±±}µ…Éé‰…¹}‘½­•É}¥µ…•Ì ¤ì4(€€€¥µ…•Ìô¡‘½­•È¥µ…•ÌğÉ•Àµ…Éé‰…¸ğ…İ¬€íÁÉ¥¹Ğ€Íôœ¤4(€€€€4(€€€¥˜l€µ¸€ˆ‘¥µ…•ÌˆtìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰I•µ½Ù¥¹œ½­•È¥µ…•Ì½˜5…Éé‰…¸ˆ4(€€€€€€€™½È¥µ…”¥¸€‘¥µ…•Ìì‘¼4(€€€€€€€€€€€¥˜‘½­•ÈÉµ¤€ˆ‘¥µ…”ˆ€ø½‘•Ø½¹Õ±°€Èø˜ÄìÑ¡•¸4(€€€€€€€€€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰%µ…”€‘¥µ…”É•µ½Ù•ˆ4(€€€€€€€€€€€™¤4(€€€€€€€‘½¹”4(€€€™¤4)ô4(4)Õ¹¥¹ÍÑ…±±}µ…Éé‰…¹}‘…Ñ…}™¥±•Ì ¤ì4(€€€¥˜l€µ€ˆ‘Q}%HˆtìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰I•µ½Ù¥¹œ‘¥É•Ñ½Éäè€‘Q}%Hˆ4(€€€€€€€É´€µÈ€ˆ‘Q}%Hˆ4(€€€™¤4)ô4(4)É•ÍÑ…ÉÑ}½µµ…¹ ¤ì4(€€€¡•±À ¤ì4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÍ…”èµ…Éé‰…¸É•ÍÑ…ÉĞm½ÁÑ¥½¹Ítˆ4(€€€€€€€•¡¼4(€€€€€€€•¡¼€‰=AQ%=9Lèˆ4(€€€€€€€•¡¼€ˆ€€µ °€´µ¡•±À€€€€€€€‘¥ÍÁ±…äÑ¡¥Ì¡•±Àµ•ÍÍ…”ˆ4(€€€€€€€•¡¼€ˆ€€µ¸°€´µ¹¼µ±½Ì€€€€‘¼¹½Ğ™½±±½Ü±½Ì…™Ñ•ÈÍÑ…ÉÑ¥¹œˆ4(€€€ô4(€€€€4(€€€±½…°¹½}±½Ìõ™…±Í”4(€€€İ¡¥±”ml€ˆŒˆ€µĞ€Àutì‘¼4(€€€€€€€…Í”€ˆÄˆ¥¸4(€€€€€€€€€€€€µ¹ğ´µ¹¼µ±½Ì¤4(€€€€€€€€€€€€€€€¹½}±½ÌõÑÉÕ”4(€€€€€€€€€€€€ìì4(€€€€€€€€€€€€µ¡ğ´µ¡•±À¤4(€€€€€€€€€€€€€€€¡•±À4(€€€€€€€€€€€€€€€•á¥Ğ€À4(€€€€€€€€€€€€ìì4(€€€€€€€€€€€€¨¤4(€€€€€€€€€€€€€€€•¡¼€‰ÉÉ½Èè%¹Ù…±¥½ÁÑ¥½¸è€Äˆ€ø˜È4(€€€€€€€€€€€€€€€¡•±À4(€€€€€€€€€€€€€€€•á¥Ğ€À4(€€€€€€€€€€€€ìì4(€€€€€€€•Í…Œ4(€€€€€€€Í¡¥™Ğ4(€€€‘½¹”4(€€€€4(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€€4(€€€‘½İ¹}µ…Éé‰…¸4(€€€ÕÁ}µ…Éé‰…¸4(€€€¥˜l€ˆ‘¹½}±½Ìˆ€ô™…±Í”tìÑ¡•¸4(€€€€€€€™½±±½İ}µ…Éé‰…¹}±½Ì4(€€€™¤4(€€€½±½É¥é•‘}•¡¼É••¸€‰5…Éé‰…¸ÍÕ•ÍÍ™Õ±±äÉ•ÍÑ…ÉÑ•„ˆ4)ô4)±½Í}½µµ…¹ ¤ì4(€€€¡•±À ¤ì4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÍ…”èµ…Éé‰…¸±½Ìm½ÁÑ¥½¹Ítˆ4(€€€€€€€•¡¼€ˆˆ4(€€€€€€€•¡¼€‰=AQ%=9Lèˆ4(€€€€€€€•¡¼€ˆ€€µ °€´µ¡•±À€€€€€€€‘¥ÍÁ±…äÑ¡¥Ì¡•±Àµ•ÍÍ…”ˆ4(€€€€€€€•¡¼€ˆ€€µ¸°€´µ¹¼µ™½±±½Ü€€‘¼¹½ĞÍ¡½Ü™½±±½Ü±½Ìˆ4(€€€ô4(€€€€4(€€€±½…°¹½}™½±±½Üõ™…±Í”4(€€€İ¡¥±”ml€ˆŒˆ€µĞ€Àutì‘¼4(€€€€€€€…Í”€ˆÄˆ¥¸4(€€€€€€€€€€€€µ¹ğ´µ¹¼µ™½±±½Ü¤4(€€€€€€€€€€€€€€€¹½}™½±±½ÜõÑÉÕ”4(€€€€€€€€€€€€ìì4(€€€€€€€€€€€€µ¡ğ´µ¡•±À¤4(€€€€€€€€€€€€€€€¡•±À4(€€€€€€€€€€€€€€€•á¥Ğ€À4(€€€€€€€€€€€€ìì4(€€€€€€€€€€€€¨¤4(€€€€€€€€€€€€€€€•¡¼€‰ÉÉ½Èè%¹Ù…±¥½ÁÑ¥½¸è€Äˆ€ø˜È4(€€€€€€€€€€€€€€€¡•±À4(€€€€€€€€€€€€€€€•á¥Ğ€À4(€€€€€€€€€€€€ìì4(€€€€€€€•Í…Œ4(€€€€€€€Í¡¥™Ğ4(€€€‘½¹”4(€€€€4(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€€4(€€€¥˜€„¥Í}µ…Éé‰…¹}ÕÀìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸¥Ì¹½ĞÕÀ¸ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€¥˜l€ˆ‘¹½}™½±±½Üˆ€ôÑÉÕ”tìÑ¡•¸4(€€€€€€€Í¡½İ}µ…Éé‰…¹}±½Ì4(€€€•±Í”4(€€€€€€€™½±±½İ}µ…Éé‰…¹}±½Ì4(€€€™¤4)ô4(4)‘½İ¹}½µµ…¹ ¤ì4(€€€€4(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€€4(€€€¥˜€„¥Í}µ…Éé‰…¹}ÕÀìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì…±É•…‘ä‘½İ¸ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘½İ¹}µ…Éé‰…¸4)ô4(4)±¥}½µµ…¹ ¤ì4(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€€4(€€€¥˜€„¥Í}µ…Éé‰…¹}ÕÀìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸¥Ì¹½ĞÕÀ¸ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€µ…Éé‰…¹}±¤€ˆ‘ ˆ4)ô4(4)ÕÁ}½µµ…¹ ¤ì4(€€€¡•±À ¤ì4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÍ…”èµ…Éé‰…¸ÕÀm½ÁÑ¥½¹Ítˆ4(€€€€€€€•¡¼€ˆˆ4(€€€€€€€•¡¼€‰=AQ%=9Lèˆ4(€€€€€€€•¡¼€ˆ€€µ °€´µ¡•±À€€€€€€€‘¥ÍÁ±…äÑ¡¥Ì¡•±Àµ•ÍÍ…”ˆ4(€€€€€€€•¡¼€ˆ€€µ¸°€´µ¹¼µ±½Ì€€€€‘¼¹½Ğ™½±±½Ü±½Ì…™Ñ•ÈÍÑ…ÉÑ¥¹œˆ4(€€€ô4(€€€€4(€€€±½…°¹½}±½Ìõ™…±Í”4(€€€İ¡¥±”ml€ˆŒˆ€µĞ€Àutì‘¼4(€€€€€€€…Í”€ˆÄˆ¥¸4(€€€€€€€€€€€€µ¹ğ´µ¹¼µ±½Ì¤4(€€€€€€€€€€€€€€€¹½}±½ÌõÑÉÕ”4(€€€€€€€€€€€€ìì4(€€€€€€€€€€€€µ¡ğ´µ¡•±À¤4(€€€€€€€€€€€€€€€¡•±À4(€€€€€€€€€€€€€€€•á¥Ğ€À4(€€€€€€€€€€€€ìì4(€€€€€€€€€€€€¨¤4(€€€€€€€€€€€€€€€•¡¼€‰ÉÉ½Èè%¹Ù…±¥½ÁÑ¥½¸è€Äˆ€ø˜È4(€€€€€€€€€€€€€€€¡•±À4(€€€€€€€€€€€€€€€•á¥Ğ€À4(€€€€€€€€€€€€ìì4(€€€€€€€•Í…Œ4(€€€€€€€Í¡¥™Ğ4(€€€‘½¹”4(€€€€4(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€€4(€€€¥˜¥Í}µ…Éé‰…¹}ÕÀìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì…±É•…‘äÕÀˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€ÕÁ}µ…Éé‰…¸4(€€€¥˜l€ˆ‘¹½}±½Ìˆ€ô™…±Í”tìÑ¡•¸4(€€€€€€€™½±±½İ}µ…Éé‰…¹}±½Ì4(€€€™¤4)ô4(4)ÕÁ‘…Ñ•}½µµ…¹ ¤ì(€€€¡•±À ¤ì(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÍ…”èµ…Éé‰…¸ÕÁ‘…Ñ”l´µÙ•ÉÍ¥½¸€ñÙ•ÉÍ¥½¸ùtˆ(€€€€€€€•¡¼€ˆˆ(€€€€€€€•¡¼€‰=AQ%=9Lèˆ(€€€€€€€•¡¼€ˆ€€µØ°€´µÙ•ÉÍ¥½¸€€€ÕÁ‘…Ñ”Ñ¼…¸•á…ĞÙ•ÉÍ¥½¸½È¥µµÕÑ…‰±”Í¡„´¨¥µ…”Ñ…œˆ(€€€€€€€•¡¼€ˆ€€µ °€´µ¡•±À€€€€€€‘¥ÍÁ±…äÑ¡¥Ì¡•±Àµ•ÍÍ…”ˆ(€€€ô((€€€±½…°É•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¸ô‰±…Ñ•ÍĞˆ(€€€İ¡¥±”ml€ˆŒˆ€µĞ€Àutì‘¼(€€€€€€€…Í”€ˆÄˆ¥¸(€€€€€€€€€€€€µÙğ´µÙ•ÉÍ¥½¸¤(€€€€€€€€€€€€€€€¥˜l€µè€ˆ‘ìÈèµôˆtìÑ¡•¸(€€€€€€€€€€€€€€€€€€€½±½É¥é•‘}•¡¼É•€‰ÉÉ½Èè€´µÙ•ÉÍ¥½¸É•ÅÕ¥É•Ì„Ù…±Õ”¸ˆ(€€€€€€€€€€€€€€€€€€€•á¥Ğ€Ä(€€€€€€€€€€€€€€€™¤(€€€€€€€€€€€€€€€É•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¸ôˆÈˆ(€€€€€€€€€€€€€€€Í¡¥™Ğ€È(€€€€€€€€€€€€ìì(€€€€€€€€€€€€µ¡ğ´µ¡•±À¤(€€€€€€€€€€€€€€€¡•±À(€€€€€€€€€€€€€€€•á¥Ğ€À(€€€€€€€€€€€€ìì(€€€€€€€€€€€€¨¤(€€€€€€€€€€€€€€€½±½É¥é•‘}•¡¼É•€‰ÉÉ½Èè%¹Ù…±¥½ÁÑ¥½¸è€Äˆ(€€€€€€€€€€€€€€€¡•±À(€€€€€€€€€€€€€€€•á¥Ğ€Ä(€€€€€€€€€€€€ìì(€€€€€€€•Í…Œ(€€€‘½¹”((€€€¥˜ml€„€ˆ‘É•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¸ˆ€õøymµi„µèÀ´ä¹|µt¬utìÑ¡•¸(€€€€€€€½±½É¥é•‘}•¡¼É•€‰ÉÉ½Èè%¹Ù…±¥Ù•ÉÍ¥½¸Ñ…œè€‘É•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¸ˆ(€€€€€€€•á¥Ğ€Ä(€€€™¤((€€€¡•­}ÉÕ¹¹¥¹}…Í}É½½Ğ(€€€€Œ¡•¬¥˜µ…Éé‰…¸¥Ì¥¹ÍÑ…±±•4(€€€¥˜€„¥Í}µ…Éé‰…¹}¥¹ÍÑ…±±•ìÑ¡•¸4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰5…Éé‰…¸Ì¹½Ğ¥¹ÍÑ…±±•„ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4(€€€€4(€€€‘•Ñ•Ñ}½µÁ½Í”4(€€€€4(€€€ÕÁ‘…Ñ•}µ…Éé‰…¹}ÍÉ¥ÁĞ(€€€¥˜€„½µµ…¹€µØåÄ€ø½‘•Ø½¹Õ±°€Èø˜ÄìÑ¡•¸(€€€€€€€¥¹ÍÑ…±±}åÄ(€€€™¤((€€€±½…°ÁÉ•Ù¥½ÕÍ}¥µ…”(€€€±½…°Ñ…É•Ñ}¥µ…”(€€€ÁÉ•Ù¥½ÕÍ}¥µ…”ô¡åÄ€µÈ€œ¹Í•ÉÙ¥•Ì¹µ…Éé‰…¸¹¥µ…”œ€ˆ‘=5A=M}%1ˆ¤(€€€Ñ…É•Ñ}¥µ…”ô¡µ…Éé‰…¹}‘½­•É}¥µ…”€ˆ‘É•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¸ˆ¤(€€€åÄ€µ¤€ˆ¹Í•ÉÙ¥•Ì¹µ…Éé‰…¸¹¥µ…”€ôpˆ‘íÑ…É•Ñ}¥µ…•õpˆˆ€ˆ‘=5A=M}%1ˆ((€€€½±½É¥é•‘}•¡¼‰±Õ”€‰AÕ±±¥¹œ5…Éé‰…¸Ù•ÉÍ¥½¸€‘íÉ•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¹ôˆ(€€€¥˜€„ÕÁ‘…Ñ•}µ…Éé‰…¸ìÑ¡•¸(€€€€€€€åÄ€µ¤€ˆ¹Í•ÉÙ¥•Ì¹µ…Éé‰…¸¹¥µ…”€ôpˆ‘íÁÉ•Ù¥½ÕÍ}¥µ…•õpˆˆ€ˆ‘=5A=M}%1ˆ(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÁ‘…Ñ”™…¥±•¸I•ÍÑ½É•ÁÉ•Ù¥½ÕÌ¥µ…”è€‘íÁÉ•Ù¥½ÕÍ}¥µ…•ôˆ(€€€€€€€•á¥Ğ€Ä(€€€™¤(€€€€4(€€€½±½É¥é•‘}•¡¼‰±Õ”€‰I•ÍÑ…ÉÑ¥¹œ5…Éé‰…¸ÌÍ•ÉÙ¥•Ìˆ(€€€‘½İ¹}µ…Éé‰…¸(€€€ÕÁ}µ…Éé‰…¸((€€€±½…°½¹Ñ…¥¹•É}¥(€€€±½…°É•…‘äô‰™…±Í”ˆ(€€€™½È|¥¸€¡Í•Ä€Ä€ÄÔ¤ì‘¼(€€€€€€€½¹Ñ…¥¹•É}¥ô ‘=5A=M€µ˜€ˆ‘=5A=M}%1ˆ€µÀ€ˆ‘AA}95ˆÁÌ€µÄµ…Éé‰…¸€Èø½‘•Ø½¹Õ±°¤(€€€€€€€¥˜l€µ¸€ˆ‘½¹Ñ…¥¹•É}¥ˆt€˜˜‘½­•È•á•Œ€ˆ‘½¹Ñ…¥¹•É}¥ˆÁåÑ¡½¸€µŒp(€€€€€€€€€€€€‰¥µÁ½ÉĞÕÉ±±¥ˆ¹É•ÅÕ•ÍĞìÕÉ±±¥ˆ¹É•ÅÕ•ÍĞ¹ÕÉ±½Á•¸ ¡ÑÑÀè¼¼ÄÈÜ¸À¸À¸ÄèàÀÀÀ½…Á¤½µ…Éé¡•±À½½µÁ…Ñ¥‰¥±¥Ñäœ°Ñ¥µ•½ÕĞôÈ¤ˆp(€€€€€€€€€€€€ø½‘•Ø½¹Õ±°€Èø˜ÄìÑ¡•¸(€€€€€€€€€€€É•…‘äô‰ÑÉÕ”ˆ(€€€€€€€€€€€‰É•…¬(€€€€€€€™¤(€€€€€€€Í±••À€Ä(€€€‘½¹”((€€€¥˜l€ˆ‘É•…‘äˆ€„ô€‰ÑÉÕ”ˆtìÑ¡•¸(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÁ‘…Ñ”¡•…±Ñ ¡•¬™…¥±•¸I•ÍÑ½É¥¹œÁÉ•Ù¥½ÕÌ¥µ…”è€‘íÁÉ•Ù¥½ÕÍ}¥µ…•ôˆ(€€€€€€€‘½İ¹}µ…Éé‰…¸(€€€€€€€åÄ€µ¤€ˆ¹Í•ÉÙ¥•Ì¹µ…Éé‰…¸¹¥µ…”€ôpˆ‘íÁÉ•Ù¥½ÕÍ}¥µ…•õpˆˆ€ˆ‘=5A=M}%1ˆ(€€€€€€€ÕÁ}µ…Éé‰…¸(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÁ‘…Ñ”™…¥±•…¹Ñ¡”ÁÉ•Ù¥½ÕÌ…ÁÁ±¥…Ñ¥½¸¥µ…”İ…ÌÉ•ÍÑ½É•¸…Ñ…‰…Í”µ¥É…Ñ¥½¹Ìİ•É”¹½Ğ‘½İ¹É…‘•¸ˆ(€€€€€€€•á¥Ğ€Ä(€€€™¤((€€€½±½É¥é•‘}•¡¼É••¸€‰5…Éé‰…¸ÕÁ‘…Ñ•ÍÕ•ÍÍ™Õ±±äÑ¼€‘íÉ•ÅÕ•ÍÑ•‘}Ù•ÉÍ¥½¹ôˆ)ô(4)ÕÁ‘…Ñ•}µ…Éé‰…¹}ÍÉ¥ÁĞ ¤ì4(€€€½±½É¥é•‘}•¡¼‰±Õ”€‰UÁ‘…Ñ¥¹œµ…Éé‰…¸ÍÉ¥ÁĞˆ4(€€€ÕÉ°€µÍM0€ˆ‘5Ii	9}MI%AQ}UI0ˆğ¥¹ÍÑ…±°€µ´€ÜÔÔ€½‘•Ø½ÍÑ‘¥¸€½ÕÍÈ½±½…°½‰¥¸½µ…Éé‰…¸4(€€€½±½É¥é•‘}•¡¼É••¸€‰µ…Éé‰…¸ÍÉ¥ÁĞÕÁ‘…Ñ•ÍÕ•ÍÍ™Õ±±äˆ4)ô4(4)ÕÁ‘…Ñ•}µ…Éé‰…¸ ¤ì(€€€€‘=5A=M€µ˜€‘=5A=M}%1€µÀ€ˆ‘AA}95ˆÁÕ±°)ô()É½±±‰…­}½µµ…¹ ¤ì(€€€¥˜l€ˆŒˆ€µ¹”€Ätñğl€ˆÄˆ€ô€ˆµ ˆtñğl€ˆÄˆ€ô€ˆ´µ¡•±ÀˆtìÑ¡•¸(€€€€€€€½±½É¥é•‘}•¡¼É•€‰UÍ…”èµ…Éé‰…¸É½±±‰…¬€ñÙ•ÉÍ¥½¸øˆ(€€€€€€€•¡¼€‰á…µÁ±”èµ…Éé‰…¸É½±±‰…¬ØĞ¸Ì¸Àˆ(€€€€€€€l€ˆŒˆ€µ•Ä€Ät€˜˜•á¥Ğ€À(€€€€€€€•á¥Ğ€Ä(€€€™¤((€€€½±½É¥é•‘}•¡¼å•±±½Ü€‰I½±±¥¹œ‰…¬Ñ¡”…ÁÁ±¥…Ñ¥½¸¥µ…”Ñ¼€Ä¸…Ñ…‰…Í”µ¥É…Ñ¥½¹Ì…É”¹½Ğ‘½İ¹É…‘•¸ˆ(€€€ÕÁ‘…Ñ•}½µµ…¹€´µÙ•ÉÍ¥½¸€ˆÄˆ)ô(4)¡•­}•‘¥Ñ½È ¤ì4(€€€¥˜l€µè€ˆ‘%Q=HˆtìÑ¡•¸4(€€€€€€€¥˜½µµ…¹€µØ¹…¹¼€ø½‘•Ø½¹Õ±°€Èø˜ÄìÑ¡•¸4(€€€€€€€€€€€%Q=Hô‰¹…¹¼ˆ4(€€€€€€€€€€€•±¥˜½µµ…¹€µØÙ¤€ø½‘•Ø½¹Õ±°€Èø˜ÄìÑ¡•¸4(€€€€€€€€€€€%Q=Hô‰Ù¤ˆ4(€€€€€€€•±Í”4(€€€€€€€€€€€‘•Ñ•Ñ}½Ì4(€€€€€€€€€€€¥¹ÍÑ…±±}Á…­…”¹…¹¼4(€€€€€€€€€€€%Q=Hô‰¹…¹¼ˆ4(€€€€€€€™¤4(€€€™¤4)ô4(4(4)•‘¥Ñ}½µµ…¹ ¤ì4(€€€‘•Ñ•Ñ}½Ì4(€€€¡•­}•‘¥Ñ½È4(€€€¥˜l€µ˜€ˆ‘=5A=M}%1ˆtìÑ¡•¸4(€€€€€€€€‘%Q=H€ˆ‘=5A=M}%1ˆ4(€€€•±Í”4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰½µÁ½Í”™¥±”¹½Ğ™½Õ¹…Ğ€‘=5A=M}%1ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4)ô4(4)•‘¥Ñ}•¹Ù}½µµ…¹ ¤ì4(€€€‘•Ñ•Ñ}½Ì4(€€€¡•­}•‘¥Ñ½È4(€€€¥˜l€µ˜€ˆ‘9Y}%1ˆtìÑ¡•¸4(€€€€€€€€‘%Q=H€ˆ‘9Y}%1ˆ4(€€€•±Í”4(€€€€€€€½±½É¥é•‘}•¡¼É•€‰¹Ù¥É½¹µ•¹Ğ™¥±”¹½Ğ™½Õ¹…Ğ€‘9Y}%1ˆ4(€€€€€€€•á¥Ğ€Ä4(€€€™¤4)ô4(4)ÕÍ…” ¤ì4(€€€±½…°ÍÉ¥ÁÑ}¹…µ”ôˆ‘ìÀŒŒ¨½ôˆ4(€€€½±½É¥é•‘}•¡¼‰±Õ”€ˆôôôôôôôôôôôôôôôôôôôôôôôôôôôôôôˆ4(€€€½±½É¥é•‘}•¡¼µ…•¹Ñ„€ˆ€€€€€€€€€€5…Éé‰…¸!•±Àˆ4(€€€½±½É¥é•‘}•¡¼‰±Õ”€ˆôôôôôôôôôôôôôôôôôôôôôôôôôôôôôôˆ4(€€€½±½É¥é•‘}•¡¼å…¸€‰UÍ…”èˆ4(€€€•¡¼€ˆ€€‘íÍÉ¥ÁÑ}¹…µ•ôm½µµ…¹‘tˆ4(€€€•¡¼4(4(€€€½±½É¥é•‘}•¡¼å…¸€‰½µµ…¹‘Ìèˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€ÕÀ€€€€€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLMÑ…ÉĞÍ•ÉÙ¥•Ìˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€‘½İ¸€€€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLMÑ½ÀÍ•ÉÙ¥•Ìˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€É•ÍÑ…ÉĞ€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLI•ÍÑ…ÉĞÍ•ÉÙ¥•Ìˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€ÍÑ…ÑÕÌ€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLM¡½ÜÍÑ…ÑÕÌˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€±½Ì€€€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLM¡½Ü±½Ìˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€±¤€€€€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠL5…Éé‰…¸1$ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€¥¹ÍÑ…±°€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠL%¹ÍÑ…±°5…Éé‰…¸ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€ÕÁ‘…Ñ”€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLUÁ‘…Ñ”Ñ¼±…Ñ•ÍĞ½È…¸•á…ĞÙ•ÉÍ¥½¸ˆ(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€É½±±‰…¬€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLI½±°‰…¬Ñ¼…¸•á…ĞÙ•ÉÍ¥½¸ˆ(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€Õ¹¥¹ÍÑ…±°€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLU¹¥¹ÍÑ…±°5…Éé‰…¸ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€¥¹ÍÑ…±°µÍÉ¥ÁĞ€€¡ÑÁÕĞÍÈÀ§ŠL%¹ÍÑ…±°5…Éé‰…¸ÍÉ¥ÁĞˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€‰…­ÕÀ€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠL5…¹Õ…°‰…­ÕÀ±…Õ¹ ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€‰…­ÕÀµÍ•ÉÙ¥”€€¡ÑÁÕĞÍÈÀ§ŠL5…Éé‰…¸	…­ÕÁÍ•ÉÙ¥”Ñ¼‰…­ÕÀÑ¼Q°…¹„¹•Ü©½ˆ¥¸É½¹Ñ…ˆˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€½É”µÕÁ‘…Ñ”€€€€€¡ÑÁÕĞÍÈÀ§ŠLUÁ‘…Ñ”½¡…¹”aÉ…ä½É”ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€•‘¥Ğ€€€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠL‘¥Ğ‘½­•Èµ½µÁ½Í”¹åµ°€¡Ù¥„¹…¹¼½ÈÙ¤•‘¥Ñ½È¤ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€•‘¥Ğµ•¹Ø€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠL‘¥Ğ•¹Ù¥É½¹µ•¹Ğ™¥±”€¡Ù¥„¹…¹¼½ÈÙ¤•‘¥Ñ½È¤ˆ4(€€€½±½É¥é•‘}•¡¼å•±±½Ü€ˆ€¡•±À€€€€€€€€€€€€¡ÑÁÕĞÍÈÀ§ŠLM¡½ÜÑ¡¥Ì¡•±Àµ•ÍÍ…”ˆ4(€€€€4(€€€€4(€€€•¡¼4(€€€½±½É¥é•‘}•¡¼å…¸€‰¥É•Ñ½É¥•Ìèˆ4(€€€½±½É¥é•‘}•¡¼µ…•¹Ñ„€ˆ€ÁÀ‘¥É•Ñ½Éäè€‘AA}%Hˆ4(€€€½±½É¥é•‘}•¡¼µ…•¹Ñ„€ˆ€…Ñ„‘¥É•Ñ½Éäè€‘Q}%Hˆ4(€€€½±½É¥é•‘}•¡¼‰±Õ”€ˆôôôôôôôôôôôôôôôôôôôôôôôôôôôôôôôôˆ4(€€€•¡¼4)ô4(4)…Í”€ˆÄˆ¥¸4(€€€ÕÀ¤4(€€€€€€€Í¡¥™ĞìÕÁ}½µµ…¹€ˆ‘ ˆìì4(€€€‘½İ¸¤4(€€€€€€€Í¡¥™Ğì‘½İ¹}½µµ…¹€ˆ‘ ˆìì4(€€€É•ÍÑ…ÉĞ¤4(€€€€€€€Í¡¥™ĞìÉ•ÍÑ…ÉÑ}½µµ…¹€ˆ‘ ˆìì4(€€€ÍÑ…ÑÕÌ¤4(€€€€€€€Í¡¥™ĞìÍÑ…ÑÕÍ}½µµ…¹€ˆ‘ ˆìì4(€€€±½Ì¤4(€€€€€€€Í¡¥™Ğì±½Í}½µµ…¹€ˆ‘ ˆìì4(€€€±¤¤4(€€€€€€€Í¡¥™Ğì±¥}½µµ…¹€ˆ‘ ˆìì4(€€€‰…­ÕÀ¤4(€€€€€€€Í¡¥™Ğì‰…­ÕÁ}½µµ…¹€ˆ‘ ˆìì4(€€€‰…­ÕÀµÍ•ÉÙ¥”¤4(€€€€€€€Í¡¥™Ğì‰…­ÕÁ}Í•ÉÙ¥”€ˆ‘ ˆìì4(€€€¥¹ÍÑ…±°¤4(€€€€€€€Í¡¥™Ğì¥¹ÍÑ…±±}½µµ…¹€ˆ‘ ˆìì4(€€€ÕÁ‘…Ñ”¤(€€€€€€€Í¡¥™ĞìÕÁ‘…Ñ•}½µµ…¹€ˆ‘ ˆìì(€€€É½±±‰…¬¤(€€€€€€€Í¡¥™ĞìÉ½±±‰…­}½µµ…¹€ˆ‘ ˆìì(€€€Õ¹¥¹ÍÑ…±°¤4(€€€€€€€Í¡¥™ĞìÕ¹¥¹ÍÑ…±±}½µµ…¹€ˆ‘ ˆìì4(€€€¥¹ÍÑ…±°µÍÉ¥ÁĞ¤4(€€€€€€€Í¡¥™Ğì¥¹ÍÑ…±±}µ…Éé‰…¹}ÍÉ¥ÁÑ}™É½µ}É•Á¼€ˆ‘ ˆìì4(€€€½É”µÕÁ‘…Ñ”¤4(€€€€€€€Í¡¥™ĞìÕÁ‘…Ñ•}½É•}½µµ…¹€ˆ‘ ˆìì4(€€€•‘¥Ğ¤4(€€€€€€€Í¡¥™Ğì•‘¥Ñ}½µµ…¹€ˆ‘ ˆìì4(€€€•‘¥Ğµ•¹Ø¤4(€€€€€€€Í¡¥™Ğì•‘¥Ñ}•¹Ù}½µµ…¹€ˆ‘ ˆìì4(€€€¡•±Áğ¨¤4(€€€€€€€ÕÍ…”ìì4)•Í…Œ4(