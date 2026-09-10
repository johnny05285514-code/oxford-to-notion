import locale
import re
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    native_name: str


SUPPORTED_LANGUAGES = (
    Language("zh-CN", "简体中文"),
    Language("en", "English"),
)
SUPPORTED_LANGUAGE_CODES = frozenset(language.code for language in SUPPORTED_LANGUAGES)


ENGLISH_MESSAGES = {
    "about_updates": "About and updates",
    "current_version": "Current version: v{version}",
    "check_updates": "Check for updates",
    "update_checking": "Checking for updates…",
    "update_current": "You're using the latest version.",
    "update_idle": "Updates are checked once a day. Downloads start only when you choose.",
    "download_update": "Download update",
    "update_downloading": "Downloading update… {percent}%",
    "update_verified": "Download verified. Ready to install.",
    "install_update": "Install now",
    "open_installer": "Open installer",
    "update_error_check": "Could not check for updates. Check your network and try again.",
    "update_error_network": "Download failed. Check your network and try again.",
    "update_error_integrity": "The download could not be verified. Please download it again.",
    "update_error_size": "The download size is unexpected. Please try again or view the release page.",
    "update_error_storage": "Could not save the update. Check free disk space and folder permissions.",
    "update_error_cancelled": "Download cancelled.",
    "update_error_launch": "Could not open the installer. Try again or open the download folder.",
    "update_wait_import": "Wait for the current import to finish before installing.",
    "update_mac_replace": "Drag Oxford to Notion into Applications and choose Replace. Quit this app before replacing it, then reopen it from Applications.",
    "update_signing_note": "The installer is not commercially signed. Windows may show Unknown Publisher; macOS may require System Settings → Privacy & Security → Open Anyway.",
    "retry_update": "Retry",
    "open_download_folder": "Open download folder",
    "nav_import": "Import",
    "nav_recent": "Recent",
    "page_import": "Import a word",
    "import_heading": "Build your vocabulary, one word at a time.",
    "recent_subtitle": "Your 100 most recent imports are synced through Notion and cached on this device.",
    "recent_sync_cached": "Sync is temporarily unavailable. Showing cached history.",
    "error_settings_save": "Settings could not be saved. Check folder permissions and available disk space, then try again.",
    "recent_cache_failed": "History is shown, but could not be saved on this device. Check available disk space and folder permissions.",
    "recent_empty": "No imported words yet.",
    "recent_search_placeholder": "Search imported words",
    "recent_no_match": "No matching imported words.",
    "connection_heading": "Notion connection",
    "preferences_heading": "Preferences",
    "help_heading": "Help",
    "performance_note": "Show Oxford and Notion timing after each successful import.",
    "cancel": "Cancel",
    "history_target_label": "Open recent imports in",
    "history_target_notion": "Notion",
    "history_target_oxford": "Oxford Learner's Dictionaries",
    "performance_diagnostics": "Show import performance details",
    "open_history_item_notion": "Open {word} in Notion",
    "open_history_item_oxford": "Open {word} in Oxford Learner's Dictionaries",
    "language_button": "🌐 English",
    "language_tooltip": "Language",
    "settings": "Settings",
    "subtitle": "Enter an English word and save it to your Notion vocabulary database",
    "word_placeholder": "For example: brutality",
    "import": "Import to Notion",
    "ready": "Ready",
    "open_notion": "Open in Notion",
    "footer": "Personal, low-frequency learning use",
    "settings_title": "Notion Settings",
    "settings_note": "Your configuration is stored only in this computer's .env file and is never uploaded to GitHub.",
    "token_label": "Notion Integration Token",
    "show_token": "Show Token",
    "database_label": "Notion database URL or Database ID",
    "open_wizard": "Open step-by-step setup",
    "back": "Back",
    "test_connection": "Test connection",
    "save_settings": "Save settings",
    "setup_complete": "Setup complete. You can start importing words.",
    "enter_word": "Please enter one English word.",
    "importing": "Importing…",
    "querying": "Looking up {word}…",
    "import_success": "{word} was imported successfully",
    "import_success_with_timing": "{word} was imported successfully\nOxford {oxford:.1f}s · Notion check {check:.1f}s · Save {save:.1f}s · Total {total:.1f}s",
    "settings_incomplete": "Please enter both the Token and database link.",
    "testing": "Testing…",
    "checking_connection": "Checking the Token, database access, and property structure…",
    "retest": "Test again",
    "connection_success": "Connection successful: the Token, database access, and properties are correct.",
    "settings_saved": "Settings saved. You can start importing words.",
    "unexpected_error": "Something unexpected happened. Please try again.",
    "language_save_warning": "The language changed for this session, but the preference could not be saved.",
    "recently_imported": "Recently imported",
    "open_history_item": "Open {word} in Notion",
    "update_available": "A new version is available: v{version}",
    "view_update": "View update",
    "wizard_title": "Set up Notion",
    "exit_wizard": "Exit setup",
    "step_progress": "Step {current} of {total}",
    "previous": "Previous",
    "next": "Next",
    "template_title": "Copy the Notion database template",
    "template_description": "The template already contains every property the app needs. Open it and choose Duplicate to copy it into your workspace.",
    "open_template": "Open Notion template",
    "integration_title": "Create and connect a Notion Integration",
    "integration_description": "Create an Internal Integration, copy its Token, then connect that Integration to the database you copied.",
    "open_integrations": "Open Notion Integrations",
    "open_notion_help": "View Notion's official guide",
    "token_title": "Paste the Integration Token",
    "token_description": "The Token is stored only on your computer. Do not share it or upload it to GitHub.",
    "token_placeholder": "Paste the Notion Integration Token",
    "database_title": "Paste the Notion database link",
    "database_description": "Open the database you copied and copy its full page URL. The app will detect the Database ID automatically.",
    "connection_title": "Test the Notion connection",
    "connection_description": "The test does not write a word. It only checks the Token, database access, and property structure.",
    "save_and_start": "Save and start",
    "token_required": "Please enter the Notion Integration Token first.",
    "database_required": "Please enter the Notion database URL first.",
    "complete_previous_steps": "Please return to the previous step and enter both the Token and database link.",
    "connection_changed": "The configuration changed. Please test the connection again.",
    "error_oxford_network": "Cannot connect to Oxford. Check your internet connection and try again.",
    "error_word_not_found": "Oxford could not find “{word}”. Check the spelling and try again.",
    "error_word_not_found_generic": "Oxford could not find that word. Check the spelling and try again.",
    "error_oxford_blocked": "Oxford refused the request. Please wait a while and try again.",
    "error_oxford_structure": "Oxford's page format has changed, so this word cannot be read right now.",
    "error_invalid_word": "Enter one English word using letters, apostrophes, or hyphens only.",
    "error_notion_token": "The Notion Token is invalid or has expired. Copy the Integration Token again.",
    "error_notion_access": "Notion denied access. Make sure your Integration is connected to this database.",
    "error_examples_property": "The database is missing the “Examples” property. Copy the template again or add that property.",
    "error_notion_schema": "The database properties do not match the template. Copy the template again or correct the properties.",
    "error_notion_rate": "Notion is receiving too many requests. Wait a moment and try again.",
    "error_notion_database": "The database link is invalid. Copy the complete Notion database URL again.",
    "error_notion_network": "Cannot connect to Notion. Check your internet connection and try again.",
    "error_configuration": "Notion setup is incomplete. Open Settings and enter the Token and database link.",
}

CHINESE_MESSAGES = {
    "about_updates": "关于与更新",
    "current_version": "当前版本：v{version}",
    "check_updates": "检查更新",
    "update_checking": "正在检查更新…",
    "update_current": "你正在使用最新版本。",
    "update_idle": "每天自动检查一次更新，点击下载后才会下载安装包。",
    "download_update": "下载更新",
    "update_downloading": "正在下载更新… {percent}%",
    "update_verified": "下载已校验，可以安装。",
    "install_update": "立即安装",
    "open_installer": "打开安装包",
    "update_error_check": "无法检查更新，请检查网络后重试。",
    "update_error_network": "下载失败，请检查网络后重试。",
    "update_error_integrity": "安装包未通过校验，请重新下载。",
    "update_error_size": "安装包大小异常，请重试或查看更新页面。",
    "update_error_storage": "无法保存更新，请检查剩余磁盘空间和文件夹权限。",
    "update_error_cancelled": "下载已取消。",
    "update_error_launch": "无法打开安装包，请重试或打开下载文件夹。",
    "update_wait_import": "请等待当前单词导入完成后再安装。",
    "update_mac_replace": "将 Oxford to Notion 拖入 Applications 并选择“替换”。替换前先退出本应用，完成后从 Applications 重新打开。",
    "update_signing_note": "安装包尚未购买商业签名。Windows 可能提示“未知发布者”；macOS 可能需要在“系统设置 → 隐私与安全性”中选择“仍要打开”。",
    "retry_update": "重试",
    "open_download_folder": "打开下载文件夹",
    "nav_import": "导入",
    "nav_recent": "最近导入",
    "page_import": "导入单词",
    "import_heading": "一次一个单词，建立你的词汇库。",
    "recent_subtitle": "最近导入的 100 个单词会通过 Notion 同步，并缓存在这台设备上。",
    "recent_sync_cached": "暂时无法同步，正在显示本机记录。",
    "error_settings_save": "无法保存设置。请检查文件夹写入权限和剩余磁盘空间，然后重试。",
    "recent_cache_failed": "记录已显示，但未能保存到本机。请检查磁盘空间和文件夹权限。",
    "recent_empty": "还没有导入过单词。",
    "recent_search_placeholder": "搜索已导入的单词",
    "recent_no_match": "没有匹配的导入单词。",
    "connection_heading": "Notion 连接",
    "preferences_heading": "使用偏好",
    "help_heading": "帮助",
    "performance_note": "每次成功导入后显示 Oxford 和 Notion 的耗时。",
    "cancel": "取消",
    "history_target_label": "最近导入打开方式",
    "history_target_notion": "Notion",
    "history_target_oxford": "Oxford Learner's Dictionaries",
    "performance_diagnostics": "显示导入性能详情",
    "open_history_item_notion": "在 Notion 中打开 {word}",
    "open_history_item_oxford": "在 Oxford Learner's Dictionaries 中打开 {word}",
    "language_button": "🌐 中文",
    "language_tooltip": "切换语言",
    "settings": "设置",
    "subtitle": "输入一个英文单词，自动保存到你的 Notion 单词库",
    "word_placeholder": "例如：brutality",
    "import": "导入到 Notion",
    "ready": "准备就绪",
    "open_notion": "在 Notion 中打开",
    "footer": "个人低频学习用途",
    "settings_title": "Notion 设置",
    "settings_note": "配置只保存在这台电脑的 .env 文件中，不会上传到 GitHub。",
    "token_label": "Notion Integration Token",
    "show_token": "显示 Token",
    "database_label": "Notion 数据库 URL 或 Database ID",
    "open_wizard": "打开分步配置向导",
    "back": "返回",
    "test_connection": "测试连接",
    "save_settings": "保存设置",
    "setup_complete": "配置完成，可以开始导入单词。",
    "enter_word": "请输入一个英文单词。",
    "importing": "正在导入…",
    "querying": "正在查询 {word}…",
    "import_success": "{word} 已成功导入",
    "import_success_with_timing": "{word} 已成功导入\nOxford 查询 {oxford:.1f} 秒 · Notion 检查 {check:.1f} 秒 · 保存 {save:.1f} 秒 · 共 {total:.1f} 秒",
    "settings_incomplete": "请先填写完整的 Token 和数据库链接。",
    "testing": "正在测试…",
    "checking_connection": "正在检查 Token、数据库权限和字段结构…",
    "retest": "重新测试",
    "connection_success": "连接成功：Token、数据库权限和字段结构都正确。",
    "settings_saved": "设置已保存，可以开始导入单词。",
    "unexpected_error": "发生了意外错误，请稍后重试。",
    "language_save_warning": "语言已在本次使用中切换，但无法保存语言偏好。",
    "recently_imported": "最近导入",
    "open_history_item": "在 Notion 中打开 {word}",
    "update_available": "发现新版本 v{version}",
    "view_update": "查看更新",
    "wizard_title": "首次配置 Notion",
    "exit_wizard": "退出向导",
    "step_progress": "第 {current} / {total} 步",
    "previous": "上一步",
    "next": "下一步",
    "template_title": "复制 Notion 数据库模板",
    "template_description": "模板已经包含程序需要的全部字段。打开模板后，点击右上角 Duplicate，复制到你自己的 workspace。",
    "open_template": "打开 Notion 模板",
    "integration_title": "创建并连接 Notion Integration",
    "integration_description": "创建 Internal Integration，复制它的 Token，然后在 Notion 中把这个 Integration 连接到刚才复制的数据库。",
    "open_integrations": "打开 Notion Integrations",
    "open_notion_help": "查看 Notion 官方说明",
    "token_title": "粘贴 Integration Token",
    "token_description": "Token 只会保存在你的电脑中。不要把它发送给别人，也不要上传到 GitHub。",
    "token_placeholder": "粘贴 Notion Integration Token",
    "database_title": "粘贴 Notion 数据库链接",
    "database_description": "打开刚才复制的数据库，复制完整页面 URL。程序会自动从 URL 中识别 Database ID。",
    "connection_title": "测试 Notion 连接",
    "connection_description": "测试不会写入单词。它只检查 Token、数据库权限和字段结构是否正确。",
    "save_and_start": "保存并开始使用",
    "token_required": "请先填写 Notion Integration Token。",
    "database_required": "请先填写 Notion 数据库 URL。",
    "complete_previous_steps": "请返回上一步，填写完整的 Token 和数据库链接。",
    "connection_changed": "配置已经更改，请重新测试连接。",
    "error_oxford_network": "无法连接 Oxford，请检查网络后重试。",
    "error_word_not_found": "Oxford 没有找到“{word}”，请检查拼写后重试。",
    "error_word_not_found_generic": "Oxford 没有找到这个单词，请检查拼写后重试。",
    "error_oxford_blocked": "Oxford 拒绝了这次请求，请稍等一会儿后重试。",
    "error_oxford_structure": "Oxford 的网页结构可能已经变化，程序暂时无法读取这个单词。",
    "error_invalid_word": "请输入一个英文单词，只能包含字母、撇号或连字符。",
    "error_notion_token": "Notion Token 无效或已失效，请重新复制 Integration Token。",
    "error_notion_access": "Notion 拒绝访问。请确认 Integration 已连接到这个数据库。",
    "error_examples_property": "数据库缺少“Examples”字段，请重新复制模板或补充该字段。",
    "error_notion_schema": "数据库字段与模板不一致，请重新复制模板或修正字段。",
    "error_notion_rate": "Notion 请求过于频繁，请稍等片刻后重试。",
    "error_notion_database": "数据库链接无效，请重新复制完整的 Notion 数据库 URL。",
    "error_notion_network": "无法连接 Notion，请检查网络后重试。",
    "error_configuration": "Notion 配置不完整，请打开设置并填写 Token 和数据库链接。",
}

CATALOGS: Mapping[str, Mapping[str, str]] = {
    "en": ENGLISH_MESSAGES,
    "zh-CN": CHINESE_MESSAGES,
}


def detect_system_language(locale_name: str | None = None) -> str:
    if locale_name is None:
        locale_name = locale.getlocale()[0] or ""
    normalized = locale_name.lower().replace("_", "-")
    return "zh-CN" if normalized == "zh" or normalized.startswith("zh-") else "en"


class Translator:
    def __init__(
        self,
        language: str,
        *,
        catalogs: Mapping[str, Mapping[str, str]] = CATALOGS,
    ) -> None:
        self.catalogs = catalogs
        self.language = language if language in SUPPORTED_LANGUAGE_CODES else "en"

    def text(self, key: str, **values: object) -> str:
        active = self.catalogs.get(self.language, {})
        english = self.catalogs.get("en", {})
        template = active.get(key) or english.get(key) or key
        return template.format(**values)


def localize_error(message: str, translator: Translator) -> str:
    raw = message.strip()
    lowered = raw.lower()
    if "could not save settings" in lowered:
        return translator.text("error_settings_save")

    if "has no entry" in lowered or "no exact matches" in lowered:
        match = re.search(r"for ['\"]([^'\"]+)['\"]", raw, re.IGNORECASE)
        if match:
            return translator.text("error_word_not_found", word=match.group(1))
        return translator.text("error_word_not_found_generic")
    if "letters, apostrophes" in lowered or "enter one english word" in lowered:
        return translator.text("error_invalid_word")
    if "refused the request" in lowered or "access challenge" in lowered:
        return translator.text("error_oxford_blocked")
    if "oxford" in lowered and (
        "request failed" in lowered
        or "returned http" in lowered
        or "unexpected http" in lowered
    ):
        return translator.text("error_oxford_network")
    if "structure" in lowered or "definition" in lowered:
        return translator.text("error_oxford_structure")
    if "examples" in lowered and (
        "missing" in lowered or "字段" in raw or "property" in lowered
    ):
        return translator.text("error_examples_property")
    if "token" in lowered and (
        "invalid" in lowered or "unauthorized" in lowered or "无效" in raw
    ):
        return translator.text("error_notion_token")
    if (
        "找不到这个数据库" in raw
        or "连接到这个数据库" in raw
        or "objectnotfound" in lowered
        or "restrictedresource" in lowered
        or "denied access" in lowered
    ):
        return translator.text("error_notion_access")
    if "字段不符合" in raw or "schema" in lowered or "properties do not" in lowered:
        return translator.text("error_notion_schema")
    if "rate" in lowered or "过于频繁" in raw:
        return translator.text("error_notion_rate")
    if "database" in lowered and (
        "invalid" in lowered or "无效" in raw or "url" in lowered
    ):
        return translator.text("error_notion_database")
    if "notion" in lowered and (
        "timeout" in lowered
        or "超时" in raw
        or "无法连接" in raw
        or "connection failed" in lowered
    ):
        return translator.text("error_notion_network")
    if "missing required" in lowered or "missing notion_" in lowered:
        return translator.text("error_configuration")
    return translator.text("unexpected_error")
