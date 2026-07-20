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
    "history_target_label": "Open recent imports in",
    "history_target_notion": "Notion",
    "history_target_oxford": "Oxford Learner's Dictionaries",
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
    "history_target_label": "最近导入打开方式",
    "history_target_notion": "Notion",
    "history_target_oxford": "Oxford Learner's Dictionaries",
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
