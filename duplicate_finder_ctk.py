"""
重复文件检测工具 - CustomTkinter 版本
现代化 GUI + 高性能扫描 + 精美界面
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import concurrent.futures
import hashlib
import os
import time
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import send2trash

# 去重内容哈希：BLAKE2b-128 在 CPython 中通常比 MD5 更快，摘要同为 128 bit
DEDUP_HASH_ALGORITHM = "BLAKE2b-128"
_HASH_DIGEST_BYTES = 16
_READ_CHUNK_SIZE = 1024 * 1024  # 顺序读块，提高磁盘吞吐
_HASH_TASK_CHUNK = 512  # 每批提交的哈希任务数，避免海量 Future 占用内存

_BLAKE2_EMPTY_HEX = hashlib.blake2b(
    b"", digest_size=_HASH_DIGEST_BYTES, usedforsecurity=False
).hexdigest()


def _compute_dedup_digest(filepath: str, size: int, is_cancelled) -> str | None:
    """计算文件内容摘要；取消或失败时返回 None。"""
    if is_cancelled():
        return None
    if size == 0:
        return _BLAKE2_EMPTY_HEX
    try:
        h = hashlib.blake2b(digest_size=_HASH_DIGEST_BYTES, usedforsecurity=False)
        with open(filepath, "rb") as f:
            while True:
                if is_cancelled():
                    return None
                chunk = f.read(_READ_CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None




# ============================================================
# 现代设计系统 - 基于 SuperDesign 原则
# ============================================================

# 深色主题配色
DARK_COLORS = {
    # 背景层次
    "bg_darkest": "#09090b",      # 最深背景
    "bg_dark": "#0f0f10",          # 主背景
    "bg_card": "#18181b",         # 卡片背景
    "bg_elevated": "#27272a",      # 抬升元素
    "bg_hover": "#3f3f46",         # 悬停状态

    # 边框
    "border": "#27272a",           # 默认边框
    "border_hover": "#52525b",     # 悬停边框
    "border_accent": "#3b82f6",    # 强调边框

    # 文字
    "text_primary": "#fafafa",     # 主要文字
    "text_secondary": "#a1a1aa",  # 次要文字
    "text_muted": "#71717a",       # 淡化文字

    # 强调色
    "accent_blue": "#3b82f6",
    "accent_green": "#22c55e",
    "accent_red": "#ef4444",
    "accent_yellow": "#eab308",
    "accent_purple": "#a855f7",

    # 渐变色
    "gradient_start": "#3b82f6",
    "gradient_end": "#8b5cf6",

    # 功能色
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#06b6d4",
}

# 浅色主题配色
LIGHT_COLORS = {
    # 背景层次
    "bg_darkest": "#f4f4f5",      # 最深背景
    "bg_dark": "#fafafa",          # 主背景
    "bg_card": "#ffffff",         # 卡片背景
    "bg_elevated": "#f4f4f5",      # 抬升元素
    "bg_hover": "#e4e4e7",         # 悬停状态

    # 边框
    "border": "#e4e4e7",           # 默认边框
    "border_hover": "#d4d4d8",     # 悬停边框
    "border_accent": "#3b82f6",    # 强调边框

    # 文字
    "text_primary": "#18181b",     # 主要文字
    "text_secondary": "#52525b",  # 次要文字
    "text_muted": "#71717a",       # 淡化文字

    # 强调色
    "accent_blue": "#3b82f6",
    "accent_green": "#22c55e",
    "accent_red": "#ef4444",
    "accent_yellow": "#eab308",
    "accent_purple": "#a855f7",

    # 渐变色
    "gradient_start": "#3b82f6",
    "gradient_end": "#8b5cf6",

    # 功能色
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#06b6d4",
}

# 当前主题（默认深色）
COLORS = DARK_COLORS.copy()
current_theme = "dark"

# 玻璃态样式 - 动态获取颜色，支持主题切换
def get_glass_style():
    return {
        "fg_color": (COLORS["bg_card"], COLORS["bg_card"]),
        "border_color": COLORS["border"],
        "border_width": 1,
        "corner_radius": 16,
    }


def get_glass_hover():
    return {
        "fg_color": (COLORS["bg_elevated"], COLORS["bg_elevated"]),
        "border_color": COLORS["border_hover"],
        "border_width": 1,
        "corner_radius": 16,
    }

# 按钮样式 - 动态获取颜色，支持主题切换
def get_button_primary():
    # 深蓝悬浮色，比主色深一级
    HOVER_BLUE = "#2563eb"
    return {
        "fg_color": COLORS["accent_blue"],
        "hover_color": HOVER_BLUE,
        "text_color": "white",
        "corner_radius": 10,
    }

def get_button_secondary():
    return {
        "fg_color": COLORS["bg_elevated"],
        "hover_color": COLORS["bg_hover"],
        "text_color": COLORS["text_primary"],
        "border_color": COLORS["border"],
        "border_width": 1,
        "corner_radius": 10,
    }

def get_button_danger():
    # 深红悬浮色，比主色深一级
    HOVER_RED = "#dc2626"
    return {
        "fg_color": COLORS["accent_red"],
        "hover_color": HOVER_RED,
        "text_color": "white",
        "corner_radius": 10,
    }

def get_button_success():
    # 深绿悬浮色，比主色深一级
    HOVER_GREEN = "#16a34a"
    return {
        "fg_color": COLORS["accent_green"],
        "hover_color": HOVER_GREEN,
        "text_color": "white",
        "corner_radius": 10,
    }


class ModernCard(ctk.CTkFrame):
    """现代风格卡片组件"""
    def __init__(self, master, hover=True, **kwargs):
        # 默认使用玻璃态样式，但保留传入的自定义参数
        default_style = get_glass_style().copy()

        # 合并自定义参数
        for key, value in kwargs.items():
            if key not in default_style:
                default_style[key] = value

        super().__init__(master, **default_style)

        if hover:
            self._bind_hover_events()
    
    def _bind_hover_events(self):
        """绑定悬停动画"""
        self.bind("<Enter>", lambda e: self._on_hover(True))
        self.bind("<Leave>", lambda e: self._on_hover(False))
        self._is_hovered = False
    
    def _on_hover(self, entering):
        """悬停效果"""
        if entering and not self._is_hovered:
            self.configure(fg_color=(COLORS["bg_elevated"], COLORS["bg_elevated"]))
            self._is_hovered = True
        elif not entering:
            self.configure(fg_color=(COLORS["bg_card"], COLORS["bg_card"]))
            self._is_hovered = False


class GradientButton(ctk.CTkButton):
    """渐变按钮（模拟）"""
    def __init__(self, master, gradient=False, **kwargs):
        # 移除渐变参数，转换为普通样式
        super().__init__(
            master,
            fg_color=COLORS["accent_blue"],
            hover_color="#2563eb",
            text_color="white",
            corner_radius=12,
            **kwargs
        )
        self._gradient = gradient
        
    def configure(self, **kwargs):
        """支持动态更新"""
        super().configure(**kwargs)


class Divider(ctk.CTkFrame):
    """分隔线"""
    def __init__(self, master, **kwargs):
        super().__init__(master, height=1, **kwargs)
        self.pack(fill="x", padx=20, pady=10)


class DuplicateFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("重复文件检测工具")
        self.geometry("480x580")
        self.minsize(400, 520)

        # 配置窗口背景
        self.configure(fg_color=COLORS["bg_darkest"])

        # 状态变量
        self.scan_paths: list[str] = []
        self.scanning = False
        self._cancel_scan = False        # 取消扫描标志
        self._cancel_rendering = False   # 取消渲染标志
        self.duplicates: list[dict] = []
        self.selected_files: set[str] = set()

        # 扫描统计
        self.total_files = 0
        self.scanned_files = 0
        self.duplicate_groups = 0
        self.duplicate_files = 0
        self.wasted_space = 0
        self.all_files = []  # 所有文件列表
        self.duplicates = []  # 重复组列表

        # 哈希缓存：key=文件路径，value=(大小, 修改时间, 哈希值)
        self.hash_cache = {}

        self.geometry("1200x1100")
        self.minsize(900, 600)
        self.setup_ui()

        
    def setup_ui(self):
        """构建 UI - 现代设计系统"""
        # 更新窗口背景色适配当前主题
        self.configure(fg_color=COLORS["bg_darkest"])

        # 主容器 - 左右分栏
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ========== 左侧面板 - 深色玻璃态 ==========
        self.left_panel = ModernCard(
            self,
            width=320,
            hover=False,
            fg_color=(COLORS["bg_dark"], COLORS["bg_dark"]),
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.left_panel.grid_propagate(False)

        # Logo 区域 - 渐变文字效果
        logo_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        logo_frame.pack(fill="x", padx=12, pady=(16, 8))
        
        # Logo 文字 + 图标
        logo_icon = ctk.CTkLabel(logo_frame, text="🔍", font=ctk.CTkFont(size=40))
        logo_icon.pack(side="left", padx=(0, 12))
        
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame, 
            text="重复文件检测", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame, 
            text="智能清理 · 安心删除", 
            text_color=COLORS["text_muted"], 
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w")
        
        # 分割线 - 渐变效果
        self._create_divider(self.left_panel)
        
        # ========== 扫描目录区域 ==========
        dir_section = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        dir_section.pack(fill="x", padx=24, pady=(16, 10))
        
        # 区域标题 + 图标
        ctk.CTkLabel(
            dir_section, 
            text="📁 扫描目录", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        
        # 目录列表容器 - 玻璃态卡片
        dir_container = ModernCard(
            dir_section,
            hover=False,
            fg_color=(COLORS["bg_card"], COLORS["bg_card"]),
            corner_radius=10,
            height=140
        )
        dir_container.pack(fill="x", pady=(10, 0))
        dir_container.pack_propagate(False)
        
        self.dir_frame = ctk.CTkScrollableFrame(
            dir_container, 
            height=120,
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_hover"],
            scrollbar_button_hover_color=COLORS["text_muted"]
        )
        self.dir_frame.pack(fill="both", expand=True, padx=8, pady=4)
        
        self.dir_list_label = ctk.CTkLabel(
            self.dir_frame, 
            text="点击下方按钮添加目录", 
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=12)
        )
        self.dir_list_label.pack(pady=20)
        
        # 目录按钮组
        dir_btn_frame = ctk.CTkFrame(dir_section, fg_color="transparent")
        dir_btn_frame.pack(fill="x", pady=(10, 0))
        
        add_btn = ctk.CTkButton(
            dir_btn_frame,
            text="➕ 添加目录",
            command=self.add_directory,
            height=38,
            **get_button_primary()
        )
        add_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        clear_btn = ctk.CTkButton(
            dir_btn_frame,
            text="清空列表",
            command=self.clear_directories,
            height=38,
            **get_button_danger()
        )
        clear_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))
        
        # 开始扫描按钮 - 大号渐变
        self.scan_btn = ctk.CTkButton(
            self.left_panel,
            text="🚀 开始扫描",
            command=self.start_scan,
            height=52,
            font=ctk.CTkFont(size=15, weight="bold"),
            **get_button_success()
        )
        self.scan_btn.pack(fill="x", padx=12, pady=(12, 10))

        self._create_divider(self.left_panel)

        # ========== 设置 ==========
        settings_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        settings_frame.pack(fill="x", padx=12, pady=(8, 8))

        ctk.CTkLabel(
            settings_frame,
            text="⚙️ 设置",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 8))

        # 主题切换
        theme_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        theme_row.pack(fill="x", pady=6)

        ctk.CTkLabel(
            theme_row,
            text="主题模式",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        self.theme_switch = ctk.CTkSwitch(
            theme_row,
            text="深色",
            command=self._toggle_theme,
            onvalue=True,
            offvalue=False,
            width=50
        )
        if current_theme == "dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="right")

        # 最小文件大小过滤
        min_size_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        min_size_row.pack(fill="x", pady=6)

        ctk.CTkLabel(
            min_size_row,
            text="最小文件大小",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        self.min_size_var = ctk.StringVar(value="1MB")
        self.min_size_entry = ctk.CTkEntry(
            min_size_row,
            textvariable=self.min_size_var,
            width=80,
            height=28,
            placeholder_text="1MB"
        )
        self.min_size_entry.pack(side="right")

        # 排除常见目录
        exclude_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        exclude_row.pack(fill="x", pady=6)

        ctk.CTkLabel(
            exclude_row,
            text="排除系统目录",
            text_color=COLORS["text_secondary"],
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        self.exclude_common_var = ctk.BooleanVar(value=True)
        exclude_check = ctk.CTkCheckBox(
            exclude_row,
            text="",
            variable=self.exclude_common_var,
            width=24,
            checkbox_width=16,
            checkbox_height=16
        )
        if self.exclude_common_var.get():
            exclude_check.select()
        else:
            exclude_check.deselect()
        exclude_check.pack(side="right")

        self._create_divider(self.left_panel)

        # ========== 统计信息卡片 ==========
        stats_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        stats_frame.pack(fill="x", padx=24, pady=(12, 10))

        ctk.CTkLabel(
            stats_frame,
            text="📊 扫描统计",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 12))
        
        # 统计网格
        self.stats_labels = {}
        stats_grid = [
            ("total_files", "📄 文件总数", COLORS["text_secondary"], None),
            ("duplicate_groups", "🔁 重复组数", COLORS["accent_blue"], COLORS["accent_blue"]),
            ("duplicate_files", "📦 重复文件", COLORS["text_secondary"], None),
            ("wasted_space", "💾 可节省空间", COLORS["accent_green"], COLORS["accent_green"]),
        ]
        
        for i, (key, label_text, label_color, value_color) in enumerate(stats_grid):
            row = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row.pack(fill="x", pady=6)
            
            ctk.CTkLabel(
                row, 
                text=label_text, 
                text_color=label_color,
                font=ctk.CTkFont(size=12)
            ).pack(side="left")
            
            value_label = ctk.CTkLabel(
                row, 
                text="0", 
                font=ctk.CTkFont(size=14, weight="bold"), 
                text_color=value_color or COLORS["text_primary"]
            )
            value_label.pack(side="right")
            self.stats_labels[key] = value_label
        
        self._create_divider(self.left_panel)
        
        # ========== 快捷操作 ==========
        action_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        action_frame.pack(fill="x", padx=24, pady=(12, 20))
        
        ctk.CTkLabel(
            action_frame, 
            text="⚡ 快捷操作", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 12))
        
        self.delete_btn = ctk.CTkButton(
            action_frame,
            text="🗑️ 删除选中文件",
            command=self.delete_selected,
            height=42,
            **get_button_danger()
        )
        self.delete_btn.pack(fill="x", pady=(0, 8))

        self.batch_quick_delete_btn = ctk.CTkButton(
            action_frame,
            text="⚡ 批量删重",
            command=self.batch_quick_delete,
            height=42,
            **get_button_danger()
        )
        self.batch_quick_delete_btn.pack(fill="x", pady=(0, 8))

        # 智能选择按钮（弹出菜单）
        self.smart_select_btn = ctk.CTkButton(
            action_frame,
            text="🧠 智能选择",
            command=self.show_smart_select_menu,
            height=42,
            **get_button_secondary()
        )
        self.smart_select_btn.pack(fill="x", pady=(0, 8))

        self.export_btn = ctk.CTkButton(
            action_frame,
            text="📊 导出报告",
            command=self.export_report,
            height=42,
            **get_button_secondary()
        )
        self.export_btn.pack(fill="x")

        # ========== 右侧面板 ==========
        self.right_panel = ctk.CTkFrame(
            self,
            fg_color=(COLORS["bg_darkest"], COLORS["bg_darkest"]),
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        # 顶部标题栏
        header = ctk.CTkFrame(
            self.right_panel,
            fg_color=(COLORS["bg_dark"], COLORS["bg_dark"]),
            height=60,
            corner_radius=12
        )
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        header.grid_propagate(False)

        # 标题区域
        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=16, pady=8)
        
        ctk.CTkLabel(
            header_content, 
            text="📋 扫描结果", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")
        
        self.status_label = ctk.CTkLabel(
            header_content, 
            text="", 
            text_color=COLORS["accent_green"],
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="right")
        
        # 结果区域
        self.result_frame = ctk.CTkScrollableFrame(
            self.right_panel, 
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_elevated"],
            scrollbar_button_hover_color=COLORS["bg_hover"]
        )
        self.result_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=(16, 8))
        # CTkScrollableFrame 不支持 grid_propagate，注释掉防止报错
        # self.result_frame.grid_propagate(False)  # 防止 resize 时重新计算

        # 空状态
        self.show_empty_state()
        
        # 日志区域
        log_container = ModernCard(
            self.right_panel,
            hover=False,
            fg_color=(COLORS["bg_card"], COLORS["bg_card"]),
            corner_radius=12,
            height=140
        )
        log_container.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 16))
        log_container.grid_propagate(False)
        
        # 日志标题栏
        log_header = ctk.CTkFrame(log_container, fg_color="transparent", height=32)
        log_header.pack(fill="x", padx=16, pady=(10, 0))
        log_header.pack_propagate(False)
        
        ctk.CTkLabel(
            log_header, 
            text="📝 操作日志", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_muted"]
        ).pack(side="left")
        
        # 清除日志按钮
        clear_log_btn = ctk.CTkButton(
            log_header,
            text="清空",
            width=50,
            height=22,
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            font=ctk.CTkFont(size=10)
        )
        clear_log_btn.pack(side="right")
        
        self.log_text = ctk.CTkTextbox(
            log_container, 
            fg_color=COLORS["bg_dark"], 
            border_width=0, 
            font=("JetBrains Mono", 11), 
            text_color=COLORS["accent_green"],
            activate_scrollbars=True
        )
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(6, 8))
        self.log_text.configure(state="disabled")
    
    def _create_divider(self, parent):
        """创建现代化分割线"""
        divider = ctk.CTkFrame(
            parent, 
            height=1, 
            fg_color=(COLORS["border"], COLORS["border"])
        )
        divider.pack(fill="x", padx=20)
        return divider
    
    def _show_path_tooltip(self, path, label):
        """显示路径提示"""
        x = label.winfo_rootx()
        y = label.winfo_rooty() + label.winfo_height() + 2
        
        # 创建 tooltip 窗口
        if hasattr(self, '_tooltip') and self._tooltip is not None:
            self._tooltip.destroy()
        
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{x}+{y}")
        
        tooltip_label = tk.Label(
            self._tooltip,
            text=path,
            background=COLORS["bg_elevated"],
            foreground=COLORS["text_primary"],
            relief="solid",
            borderwidth=1,
            font=("微软雅黑", 10),
            padx=8,
            pady=4
        )
        tooltip_label.pack()
    
    def _hide_path_tooltip(self):
        """隐藏路径提示"""
        if hasattr(self, '_tooltip') and self._tooltip is not None:
            self._tooltip.destroy()
            self._tooltip = None
        
    def show_empty_state(self):
        """显示空状态 - 现代化设计"""
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        
        # 中心空状态卡片
        empty = ModernCard(
            self.result_frame,
            hover=False,
            fg_color=(COLORS["bg_card"], COLORS["bg_card"]),
            corner_radius=20,
            height=280
        )
        empty.pack(fill="both", expand=True, pady=60)
        empty.pack_propagate(False)
        
        # 空状态内容
        content = ctk.CTkFrame(empty, fg_color="transparent")
        content.pack(expand=True)
        
        # 动画效果的大图标
        icon_label = ctk.CTkLabel(
            content, 
            text="✨", 
            font=ctk.CTkFont(size=72)
        )
        icon_label.pack(pady=(10, 20))
        
        # 标题
        ctk.CTkLabel(
            content, 
            text="准备就绪", 
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(pady=(0, 8))
        
        # 副标题
        ctk.CTkLabel(
            content, 
            text="添加目录后开始扫描重复文件", 
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"]
        ).pack()
        
        # 提示卡片
        tip = ctk.CTkFrame(content, fg_color=(COLORS["bg_elevated"], COLORS["bg_elevated"]), corner_radius=10)
        tip.pack(pady=(24, 0))
        
        ctk.CTkLabel(
            tip,
            text="💡 提示：文件会先按大小分组，\n仅对可能有重复的文件进行哈希验证",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            justify="center"
        ).pack(padx=16, pady=12)
        
    def add_log(self, msg: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
    def add_directory(self):
        """添加目录"""
        # 使用 tkinter 的 filedialog 而不是 customtkinter 的
        path = filedialog.askdirectory(title="选择要扫描的文件夹")
        if path:
            path = os.path.normpath(path)  # 规范化路径
            if path not in self.scan_paths:
                self.scan_paths.append(path)
                self.update_dir_list()
                self.add_log(f"✓ 添加目录: {path}")
            else:
                messagebox.showinfo("提示", "该目录已在列表中")
                
    def clear_directories(self):
        """清空目录列表"""
        if self.scan_paths:
            self.scan_paths.clear()
            self.update_dir_list()
            self.add_log("🗑️ 已清空目录列表")
            
    def update_dir_list(self):
        """更新目录列表显示 - 现代化设计"""
        for widget in self.dir_frame.winfo_children():
            widget.destroy()
            
        if not self.scan_paths:
            self.dir_list_label = ctk.CTkLabel(
                self.dir_frame, 
                text="点击下方按钮添加目录", 
                text_color=COLORS["text_muted"],
                font=ctk.CTkFont(size=12)
            )
            self.dir_list_label.pack(pady=20)
        else:
            for path in self.scan_paths:
                row = ctk.CTkFrame(
                    self.dir_frame, 
                    fg_color=(COLORS["bg_elevated"], COLORS["bg_elevated"]),
                    corner_radius=8,
                    height=36
                )
                row.pack(fill="x", pady=3)
                row.pack_propagate(False)
                
                # 悬停效果
                def on_hover(e, r=row):
                    r.configure(fg_color=(COLORS["bg_hover"], COLORS["bg_hover"]))
                def on_leave(e, r=row):
                    r.configure(fg_color=(COLORS["bg_elevated"], COLORS["bg_elevated"]))
                
                row.bind("<Enter>", on_hover)
                row.bind("<Leave>", on_leave)
                
                # 文件夹图标
                ctk.CTkLabel(
                    row, 
                    text="📁", 
                    font=ctk.CTkFont(size=14)
                ).pack(side="left", padx=(10, 6))
                
                # 删除按钮先 pack，确保在右侧
                btn = ctk.CTkButton(
                    row, 
                    text="✕", 
                    width=28, 
                    height=26, 
                    fg_color=COLORS["accent_red"], 
                    hover_color="#dc2626",
                    corner_radius=6,
                    text_color="white",
                    font=ctk.CTkFont(size=12),
                    command=lambda p=path: self.remove_path(p)
                )
                btn.pack(side="right", padx=6)
                
                # 路径标签 - 使用 expand 填充剩余空间，但不过度占用
                path_label = ctk.CTkLabel(
                    row, 
                    text="",  # 稍后设置文本
                    anchor="w",
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=11)
                )
                path_label.pack(side="left", fill="x", expand=True, padx=(4, 4))
                
                # 计算合适的路径文本（保留足够空间给删除按钮）
                max_path_len = 35  # 最大显示长度
                if len(path) > max_path_len:
                    # 省略中间，保留开头和结尾
                    path_text = path[:20] + "..." + path[-(max_path_len-23):]
                else:
                    path_text = path
                
                path_label.configure(text=path_text)
                
                # 鼠标悬停显示完整路径（tooltip）
                path_label.bind("<Enter>", lambda e, p=path: self._show_path_tooltip(p, path_label))
                path_label.bind("<Leave>", lambda e: self._hide_path_tooltip())
                
                # 整行也支持 tooltip
                row.bind("<Enter>", lambda e, p=path: self._show_path_tooltip(p, path_label))
                row.bind("<Leave>", lambda e: self._hide_path_tooltip())
                
    def remove_path(self, path: str):
        """移除目录"""
        if path in self.scan_paths:
            self.scan_paths.remove(path)
            self.update_dir_list()
            self.add_log(f"✕ 移除目录: {path}")
            
    def update_stats(self):
        """更新统计信息"""
        self.stats_labels["total_files"].configure(text=str(self.total_files))
        self.stats_labels["duplicate_groups"].configure(text=str(self.duplicate_groups))
        self.stats_labels["duplicate_files"].configure(text=str(self.duplicate_files))
        self.stats_labels["wasted_space"].configure(text=self.format_size(self.wasted_space))
        
        self.delete_btn.configure(text=f"🗑️ 删除选中 ({len(self.selected_files)})", state="normal" if self.selected_files else "disabled")
        
    def format_size(self, size) -> str:
        """格式化文件大小"""
        try:
            size = int(size)
        except (ValueError, TypeError):
            return str(size)
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
        
    def start_scan(self):
        """开始扫描或停止扫描"""
        if self.scanning:
            # 当前正在扫描，停止它
            self._cancel_scan = True
            self.add_log("⏹️ 正在停止扫描...")
            self.scan_btn.configure(state="disabled", text="⏹️ 停止中...")
            return

        if not self.scan_paths:
            messagebox.showwarning("提示", "请先添加要扫描的目录")
            return

        # 取消之前正在进行的渲染
        self._cancel_rendering = True

        # 重置状态
        self.scanning = True
        self._cancel_scan = False
        self.duplicates.clear()
        self.all_files.clear()  # 清空所有文件列表
        self.selected_files.clear()
        self.scanned_files = 0
        self.total_files = 0
        self.duplicate_groups = 0
        self.duplicate_files = 0
        self.wasted_space = 0
        self.scan_btn.configure(state="normal", text="⏹️ 停止扫描", **get_button_danger())
        self.show_empty_state()
        self.add_log("🚀 开始扫描...")

        thread = threading.Thread(target=self.scan_worker, daemon=True)
        thread.start()
        
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串为字节，支持 1KB, 1MB, 1GB"""
        size_str = size_str.strip().lower()
        units = {'kb': 1024, 'mb': 1024*1024, 'gb': 1024*1024*1024, 'b': 1}
        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                try:
                    num = float(size_str[:-len(unit)])
                    return int(num * multiplier)
                except:
                    pass
        # 默认尝试解析为字节
        try:
            return int(float(size_str))
        except:
            return 1024*1024  # 默认 1MB

    def scan_worker(self):
        """扫描工作线程"""
        try:
            # 复制扫描路径避免线程冲突
            scan_paths = self.scan_paths.copy()
            self.after(0, lambda: self.add_log(f"📂 开始扫描 {len(scan_paths)} 个目录..."))
            start_time = time.time()

            # 读取选项
            min_file_size = self._parse_size(self.min_size_var.get())
            exclude_common = self.exclude_common_var.get()
            exclude_dirs = {'node_modules', '.git', '.venv', '__pycache__', '.idea', '.vscode', 'node_modules', 'build', 'dist'}

            if min_file_size > 0:
                self.after(0, lambda: self.add_log(f"⚙️ 跳过小于 {self.min_size_var.get()} 的文件"))
            if exclude_common:
                self.after(0, lambda: self.add_log(f"⚙️ 自动排除常见目录: {', '.join(exclude_dirs)}"))

            # 第一步：按大小分组
            size_groups = defaultdict(list)
            file_count = 0
            error_count = 0
            dir_sizes = defaultdict(int)  # 追踪每个目录的文件数

            for scan_path in scan_paths:
                if self._cancel_scan:
                    self.after(0, lambda: self.add_log("⏹️ 扫描已取消"))
                    break

                scan_path_norm = os.path.normpath(scan_path)
                self.after(0, lambda p=scan_path_norm: self.add_log(f"📂 扫描: {os.path.basename(p)}"))
                dir_file_count = 0

                def walk_error(err):
                    """os.walk 错误处理"""
                    self.after(0, lambda: self.add_log(f"⚠️ 访问错误: {err.filename} - {err.strerror}"))

                try:
                    # 使用os.scandir替代os.walk，更快的目录遍历，直接获取文件属性
                    def scan_dir(root):
                        nonlocal file_count, dir_file_count, error_count
                        if self._cancel_scan:
                            return
                        try:
                            with os.scandir(root) as entries:
                                dirs = []
                                for entry in entries:
                                    if self._cancel_scan:
                                        return
                                    if entry.is_dir(follow_symlinks=False):
                                        # 排除目录
                                        if not exclude_common or entry.name not in exclude_dirs:
                                            dirs.append(entry.path)
                                    elif entry.is_file(follow_symlinks=False):
                                        file_count += 1
                                        dir_file_count += 1
                                        try:
                                            size = entry.stat(follow_symlinks=False).st_size
                                            # 跳过小于最小设置的文件和空文件
                                            if size >= min_file_size and size > 0:
                                                size_groups[size].append(entry.path)
                                        except Exception as e:
                                            error_count += 1

                                        # 每扫描 100 个文件更新一次进度
                                        if file_count % 100 == 0:
                                            self.total_files = file_count
                                            self.after(0, lambda: self.update_stats())
                                # 递归扫描子目录
                                for d in dirs:
                                    scan_dir(d)
                        except OSError as e:
                            self.after(0, lambda: self.add_log(f"⚠️ 访问错误: {root} - {e.strerror}"))

                    scan_dir(scan_path_norm)
                    dir_sizes[scan_path_norm] = dir_file_count
                except Exception as e:
                    self.after(0, lambda: self.add_log(f"❌ 扫描失败: {os.path.basename(scan_path)}"))
                if self._cancel_scan:
                    break

            if self._cancel_scan:
                return

            self.total_files = file_count
            self.after(0, lambda: self.update_stats())
            self.after(0, lambda: self.add_log(f"📄 共 {file_count} 个文件" + (f", {error_count} 个访问失败" if error_count else "")))

            # 筛选可能有重复的文件
            candidates = [files for files in size_groups.values() if len(files) > 1]
            self.after(0, lambda: self.add_log(f"🔍 {len(candidates)} 组候选待验证..."))

            # 第二步：计算哈希 - 使用多线程并行加速
            hash_groups = defaultdict(list)

            # 收集所有需要计算哈希的文件
            all_candidates = []
            for group in candidates:
                for filepath in group:
                    all_candidates.append(filepath)

            if all_candidates:
                self.after(0, lambda: self.add_log(f"🔍 并行计算哈希，共 {len(all_candidates)} 个文件..."))

            # 计算哈希的函数
            def compute_hash(filepath):
                """计算单个文件的BLAKE2b哈希，大文件先采样快速比对，支持缓存复用"""
                if self._cancel_scan:
                    return None
                try:
                    stat = os.stat(filepath)
                    size = stat.st_size
                    mtime = stat.st_mtime

                    # 检查缓存：如果文件大小和修改时间没有变化，直接复用缓存的哈希
                    if filepath in self.hash_cache:
                        cache_size, cache_mtime, cache_hash = self.hash_cache[filepath]
                        if cache_size == size and cache_mtime == mtime:
                            return (filepath, cache_hash)

                    # 空文件直接返回固定哈希
                    if size == 0:
                        self.hash_cache[filepath] = (size, mtime, _BLAKE2_EMPTY_HEX)
                        return (filepath, _BLAKE2_EMPTY_HEX)

                    hasher = hashlib.blake2b(digest_size=_HASH_DIGEST_BYTES, usedforsecurity=False)

                    # 小于1MB文件直接全量读取
                    if size < 1 * 1024 * 1024:
                        with open(filepath, 'rb') as f:
                            hasher.update(f.read())
                        h = hasher.hexdigest()
                        self.hash_cache[filepath] = (size, mtime, h)
                        return (filepath, h)

                    # 大于100MB文件先计算首尾128KB采样哈希快速过滤
                    if size > 100 * 1024 * 1024:
                        # 先计算全量哈希
                        full_hasher = hashlib.blake2b(digest_size=_HASH_DIGEST_BYTES, usedforsecurity=False)
                        with open(filepath, 'rb') as f:
                            chunk_size = 65536
                            while chunk := f.read(chunk_size):
                                if self._cancel_scan:
                                    return None
                                full_hasher.update(chunk)
                        h = full_hasher.hexdigest()
                        self.hash_cache[filepath] = (size, mtime, h)
                        return (filepath, h)

                    # 1MB~100MB文件正常全量计算
                    with open(filepath, 'rb') as f:
                        chunk_size = 65536
                        while chunk := f.read(chunk_size):
                            if self._cancel_scan:
                                return None
                            hasher.update(chunk)
                    h = hasher.hexdigest()
                    self.hash_cache[filepath] = (size, mtime, h)
                    return (filepath, h)
                except Exception as e:
                    return None

            # 使用线程池并行计算，IO密集型场景使用更多线程
            max_workers = min(64, (os.cpu_count() or 4) * 4)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(compute_hash, filepath) for filepath in all_candidates]

                completed = 0
                for future in concurrent.futures.as_completed(futures):
                    if self._cancel_scan:
                        # 取消所有未完成的任务
                        for f in futures:
                            f.cancel()
                        self.after(0, lambda: self.add_log("⏹️ 扫描已取消"))
                        return

                    result = future.result()
                    completed += 1
                    if result is not None:
                        filepath, h = result
                        hash_groups[h].append(filepath)

                    # 每完成 100 个计算更新一次日志，显示剩余时间
                    if completed % 100 == 0:
                        elapsed = time.time() - start_time
                        if elapsed > 0 and completed > 0:
                            speed = completed / elapsed  # 每秒完成的哈希计算数
                            remaining = len(all_candidates) - completed
                            remaining_time = remaining / speed if speed > 0 else 0
                            # 格式化剩余时间
                            if remaining_time < 60:
                                time_str = f"{int(remaining_time)}秒"
                            elif remaining_time < 3600:
                                time_str = f"{int(remaining_time//60)}分{int(remaining_time%60)}秒"
                            else:
                                time_str = f"{int(remaining_time//3600)}时{int((remaining_time%3600)//60)}分"
                            self.after(0, lambda c=completed, t=time_str: self.add_log(f"⏳ 已完成 {c}/{len(all_candidates)} 个哈希计算，预计剩余 {t}"))
                        else:
                            self.after(0, lambda c=completed: self.add_log(f"⏳ 已完成 {c}/{len(all_candidates)} 个哈希计算"))

            if self._cancel_scan:
                return

            self.after(0, lambda: self.add_log(f"🔐 哈希验证完成"))

            # 收集重复文件
            self.duplicates = []
            for h, paths in hash_groups.items():
                if len(paths) > 1:
                    size = os.path.getsize(paths[0]) if os.path.exists(paths[0]) else 0
                    self.duplicates.append({"hash": h, "paths": paths, "size": size})

            self.duplicate_groups = len(self.duplicates)
            self.duplicate_files = sum(len(g["paths"]) - 1 for g in self.duplicates)
            self.wasted_space = sum(g["size"] * (len(g["paths"]) - 1) for g in self.duplicates)

            self.after(0, lambda: self.update_stats())
            self.after(0, lambda: self.add_log(f"✅ 扫描完成！发现 {self.duplicate_groups} 组重复文件"))
            self.after(0, self.render_results)

        except Exception as e:
            self.after(0, lambda: self.add_log(f"❌ 错误: {str(e)}"))
        finally:
            self.scanning = False
            self._cancel_scan = False
            # 恢复按钮为开始扫描，恢复原色
            self.after(0, lambda: self.scan_btn.configure(state="normal", text="🚀 开始扫描", **get_button_success()))
            
    def render_results(self):
        """渲染扫描结果 - 优化版：大数据量时分页显示，避免UI卡死"""
        # 取消之前正在进行的渲染
        self._cancel_rendering = True

        for widget in self.result_frame.winfo_children():
            widget.destroy()

        if not self.duplicates:
            self.show_empty_state()
            return

        self._total_groups = len(self.duplicates)
        self._cancel_rendering = False

        # 分页设置：大数据量时分页，减少同时渲染的组件数量
        self._page_size = 50  # 每页50组
        self._current_page = 0
        self._total_pages = (self._total_groups + self._page_size - 1) // self._page_size

        # 如果总组数少，直接全部渲染
        if self._total_groups <= self._page_size:
            # 先显示加载提示
            self.loading_label = ctk.CTkLabel(
                self.result_frame,
                text=f"正在加载 {self._total_groups} 组...",
                text_color=COLORS["text_muted"],
                font=ctk.CTkFont(size=14)
            )
            self.loading_label.pack(pady=20)

            # 使用计数器追踪进度
            self._render_idx = 0
            self._render_total = self._total_groups
            self._batch_render()
        else:
            # 大数据量，分页显示
            self.add_log(f"⚠️ 检测到大量重复文件 ({self._total_groups} 组)，已启用分页模式")
            self._render_current_page()

    def _render_current_page(self):
        """渲染当前页"""
        # 取消之前正在进行的渲染
        self._cancel_rendering = True

        # 清除当前页内容
        for widget in self.result_frame.winfo_children():
            widget.destroy()

        start_idx = self._current_page * self._page_size
        end_idx = min(start_idx + self._page_size, self._total_groups)
        self._cancel_rendering = False

        # 先显示分页信息
        page_info = ctk.CTkFrame(self.result_frame, fg_color=COLORS["bg_card"], corner_radius=10, height=40)
        page_info.pack(fill="x", pady=(0, 8))
        page_info.pack_propagate(False)

        ctk.CTkLabel(page_info, text=f"第 {self._current_page + 1} / {self._total_pages} 页，共 {self._total_groups} 组",
                     text_color=COLORS["text_secondary"], font=ctk.CTkFont(size=12)).pack(side="left", padx=16, pady=8)

        # 分页按钮
        btn_frame = ctk.CTkFrame(page_info, fg_color="transparent")
        btn_frame.pack(side="right", padx=8)

        prev_btn = ctk.CTkButton(btn_frame, text="◀ 上一页", width=80, height=28,
                                 fg_color=COLORS["bg_elevated"], hover_color=COLORS["bg_hover"],
                                 state="normal" if self._current_page > 0 else "disabled",
                                 command=self._prev_page)
        prev_btn.pack(side="left", padx=4)

        next_btn = ctk.CTkButton(btn_frame, text="下一页 ▶", width=80, height=28,
                                 fg_color=COLORS["bg_elevated"], hover_color=COLORS["bg_hover"],
                                 state="normal" if self._current_page < self._total_pages - 1 else "disabled",
                                 command=self._next_page)
        next_btn.pack(side="left", padx=4)

        # 加载提示
        self.loading_label = ctk.CTkLabel(
            self.result_frame,
            text=f"正在加载第 {self._current_page + 1} 页 ({start_idx + 1} - {end_idx})...",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=14)
        )
        self.loading_label.pack(pady=10)

        # 分批渲染当前页
        self._render_idx = start_idx
        self._render_total = end_idx
        self._batch_render_page()

    def _batch_render_page(self):
        """分批渲染当前页 - 每批少量，保持UI响应"""
        # 检查是否需要中断渲染
        if self._cancel_rendering:
            return

        batch_size = 2  # 每批只渲染2组，给UI留出更多呼吸空间
        batch_count = 0

        while not self._cancel_rendering and self._render_idx < self._render_total and batch_count < batch_size:
            group = self.duplicates[self._render_idx]
            self._create_simple_row(self._render_idx, group)
            self._render_idx += 1
            batch_count += 1

        if not self._cancel_rendering and self._render_idx < self._render_total:
            # 更新加载提示
            if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
                self.loading_label.configure(text=f"正在加载第 {self._current_page + 1} 页 ({self._render_idx + 1} - {self._render_total})...")
            # 固定16ms间隔，让UI每帧都能响应
            self.after(16, self._batch_render_page)
        else:
            # 渲染完成，移除加载提示
            if not self._cancel_rendering and hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
                self.loading_label.destroy()

    def _batch_render(self):
        """分批渲染全部结果 - 优化版：减少批大小，增加间隔，避免UI卡死"""
        # 检查是否需要中断渲染
        if self._cancel_rendering:
            return

        batch_size = 3  # 减少每批数量，避免长时间阻塞
        batch_count = 0

        while not self._cancel_rendering and self._render_idx < self._render_total and batch_count < batch_size:
            group = self.duplicates[self._render_idx]
            self._create_simple_row(self._render_idx, group)
            self._render_idx += 1
            batch_count += 1

        # 更新加载提示
        if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
            self.loading_label.configure(text=f"正在加载 {self._render_idx}/{self._render_total}...")

        if not self._cancel_rendering and self._render_idx < self._render_total:
            # 固定16ms间隔，让UI每帧都能响应，保持界面流畅
            self.after(16, self._batch_render)
        elif not self._cancel_rendering:
            # 渲染完成
            if hasattr(self, 'loading_label') and self.loading_label.winfo_exists():
                self.loading_label.destroy()
            self.add_log(f"✅ {self._render_total} 组重复文件加载完成，点击▼展开查看详情")

    def _prev_page(self):
        """上一页"""
        if self._current_page > 0:
            self._current_page -= 1
            self._render_current_page()

    def _next_page(self):
        """下一页"""
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._render_current_page()
        
    def _create_simple_row(self, idx: int, group: dict):
        """创建简洁行"""
        row = ctk.CTkFrame(self.result_frame, fg_color=COLORS["bg_card"], corner_radius=12, height=60)
        row._idx = idx
        row._group = group
        row._expanded = False
        row.pack(fill="x", pady=6)
        row.pack_propagate(False)

        # 序号 - 蓝色背景徽章
        badge = ctk.CTkFrame(row, fg_color=COLORS["accent_blue"], corner_radius=6, width=50, height=28)
        badge.place(relx=0, rely=0.5, x=12, y=0, anchor="w")
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text=f"#{idx+1}", font=ctk.CTkFont(size=13, weight="bold"), text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        # 信息区域 - 只显示文件数量（不需要名称和大小）
        info_container = ctk.CTkFrame(row, fg_color="transparent")
        info_container.pack(side="left", fill="both", expand=True, padx=(72, 10))

        ctk.CTkLabel(
            info_container,
            text=f"{len(group['paths'])} 个重复文件",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_primary"],
            anchor="w"
        ).pack(fill="both", expand=True, pady=16)

        # 操作按钮 - 右侧容器
        btns = ctk.CTkFrame(row, fg_color="transparent", width=108, height=60)
        btns.pack(side="right", padx=10)
        btns.pack_propagate(False)

        expand_btn = ctk.CTkButton(
            btns, text="▼", width=36, height=36,
            fg_color=COLORS["bg_elevated"], hover_color=COLORS["bg_hover"],
            corner_radius=8, font=ctk.CTkFont(size=14),
            command=lambda r=row: self._toggle_expand(r)
        )
        expand_btn.pack(side="left", padx=2)
        ctk.CTkButton(
            btns, text="删重", width=60, height=36,
            fg_color=COLORS["accent_red"], hover_color="#dc2626",
            corner_radius=8, font=ctk.CTkFont(size=12),
            command=lambda g=group: self.quick_delete_group(g)
        ).pack(side="left", padx=2)
    
    def _toggle_expand(self, row):
        """切换展开/收起"""
        if row._expanded:
            self._collapse_row(row)
        else:
            self._expand_row(row)
    
    def _expand_row(self, row):
        """展开行 - 优化版：减少组件数量，使用轻量布局，分批懒加载"""
        import tkinter as tk
        row._expanded = True
        group = row._group

        # 直接在行下面插入详情
        detail = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        detail.pack(fill="x", pady=(0, 4), after=row)

        # 文件数太多时，限制一次显示的数量，提供滚动
        files = group['paths']

        if len(files) > 50:
            # 大量文件使用原生 Tkinter Listbox 更轻量，支持扩展多选
            import tkinter as tk
            list_frame = ctk.CTkFrame(detail, fg_color=COLORS["bg_dark"], corner_radius=6)
            list_frame.pack(fill="both", expand=True, padx=(60, 12))

            scrollbar = tk.Scrollbar(list_frame)
            scrollbar.pack(side="right", fill="y")

            listbox = tk.Listbox(
                list_frame,
                bg=COLORS["bg_dark"],
                fg=COLORS["text_secondary"],
                selectbackground=COLORS["accent_blue"],
                activestyle='dotbox',
                yscrollcommand=scrollbar.set,
                selectmode=tk.EXTENDED,  # 支持按住Ctrl/Shift多选
                height=min(10, len(files)),
                font=("Segoe UI", 11)
            )

            for filepath in files:
                display = f"  {os.path.basename(filepath)} - {os.path.dirname(filepath)}"
                listbox.insert(tk.END, display)

            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=listbox.yview)

            # 批量操作按钮栏
            btn_frame = ctk.CTkFrame(detail, fg_color="transparent")
            btn_frame.pack(fill="x", padx=(60, 12), pady=(8, 4))

            def select_all_except_first():
                """选中除第一个外的所有文件"""
                listbox.selection_clear(0, tk.END)
                if len(files) > 1:
                    listbox.selection_set(1, tk.END)

            def add_selected_to_global():
                """将选中的文件添加到全局选中集合"""
                selected_indices = listbox.curselection()
                if not selected_indices:
                    messagebox.showinfo("提示", "请先在列表中选中要删除的文件（按住Ctrl可多选，按住Shift可连选）")
                    return
                count = 0
                for idx in selected_indices:
                    filepath = files[idx]
                    if filepath not in self.selected_files:
                        self.selected_files.add(filepath)
                        count += 1
                self.update_stats()
                if count > 0:
                    self.add_log(f"✓ 已添加 {count} 个文件到选中列表")

            def delete_selected_here():
                """直接删除这里选中的文件"""
                selected_indices = listbox.curselection()
                if not selected_indices:
                    messagebox.showinfo("提示", "请先在列表中选中要删除的文件")
                    return
                if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_indices)} 个文件吗？"):
                    return

                # 从后往前删，避免索引变化
                for idx in sorted(selected_indices, reverse=True):
                    filepath = files[idx]
                    if not os.path.exists(filepath):
                        continue
                    try:
                        file_size = os.path.getsize(filepath)
                        send2trash.send2trash(filepath)
                        self.add_log(f"🗑️ 已删除: {os.path.basename(filepath)}")
                        if filepath in self.selected_files:
                            self.selected_files.discard(filepath)
                        # 从数据结构移除
                        for g in list(self.duplicates):
                            if filepath in g['paths']:
                                g['paths'].remove(filepath)
                                self.duplicate_files -= 1
                                self.wasted_space -= file_size
                                if len(g['paths']) <= 1 and g in self.duplicates:
                                    self.duplicates.remove(g)
                                    self.duplicate_groups -= 1
                                break
                        listbox.delete(idx)
                    except Exception as e:
                        self.add_log(f"❌ 删除失败: {os.path.basename(filepath)}")

                self.update_stats()
                self.render_results()

            ctk.CTkButton(
                btn_frame,
                text="全选除第一个",
                width=80,
                height=28,
                **get_button_secondary(),
                command=select_all_except_first
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_frame,
                text="添加到选中",
                width=80,
                height=28,
                **get_button_secondary(),
                command=add_selected_to_global
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_frame,
                text="删除选中",
                width=80,
                height=28,
                **get_button_danger(),
                command=delete_selected_here
            ).pack(side="left", padx=(0, 8))

            # 右键菜单操作
            def on_right_click(event):
                if not listbox.curselection():
                    return
                idx = listbox.curselection()[0]
                filepath = files[idx]
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label="📂 打开文件夹", command=lambda: self.open_folder(filepath))
                menu.add_command(label="🗑️ 删除文件", command=lambda: self.delete_single_file(filepath))
                menu.tk_popup(event.x_root, event.y_root)

            listbox.bind("<Button-3>", on_right_click)
            row._detail = detail
            row._listbox = listbox
            row._files = files
            return

        elif len(files) > 10:
            # 中等数量文件 (10-50)：分批懒加载，避免一次性创建大量组件导致卡顿
            import tkinter as tk
            # 先添加加载提示
            progress_label = ctk.CTkLabel(
                detail,
                text=f"正在加载 {len(files)} 个文件...",
                text_color=COLORS["text_muted"],
                font=ctk.CTkFont(size=12)
            )
            progress_label.pack(pady=8, padx=(60, 12))

            # 存储对detail的引用供分批加载使用
            row._detail = detail
            row._files = files
            row._file_detail_progress = progress_label

            # 开始分批加载
            self._batch_render_files(row, detail, files, 0)
            return

        # 文件很少时（<= 10），直接全部渲染
        for filepath in files:
            # 减少嵌套，直接使用一个 Frame，用 place 定位更高效
            file_item = ctk.CTkFrame(detail, fg_color=COLORS["bg_dark"], corner_radius=6, height=40)
            file_item.pack(fill="x", pady=2, padx=(60, 12))
            file_item.pack_propagate(False)

            var = tk.BooleanVar(value=filepath in self.selected_files)
            # 复选框靠左放置 - width/height 在构造函数
            cb = ctk.CTkCheckBox(
                file_item,
                text="",
                variable=var,
                width=24,
                checkbox_width=16,
                checkbox_height=16,
                command=lambda f=filepath, v=var: self.toggle_file(f, v.get())
            )
            cb.place(x=6, y=8)

            # 图标 + 路径文本靠左，占据剩余空间
            icon_label = ctk.CTkLabel(
                file_item,
                text=self.get_file_icon(filepath),
                font=ctk.CTkFont(size=14),
                width=20,
                height=20
            )
            icon_label.place(x=42, y=10)

            # 获取文件大小并格式化
            try:
                size = os.path.getsize(filepath)
                size_str = self.format_size(size)
            except:
                size_str = "未知"
            path_text = f"{os.path.basename(filepath)}  {os.path.dirname(filepath)}  [{size_str}]"
            text_label = ctk.CTkLabel(
                file_item,
                text=path_text,
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_secondary"],
                anchor="w",
                width=1  # width 在构造函数，已经有了
            )
            text_label.place(x=72, y=0, relwidth=1, relheight=1)

            # 打开文件、打开文件夹、删除 三个按钮靠右
            open_btn = ctk.CTkButton(
                file_item,
                text="▶",
                width=28,
                height=28,
                fg_color=COLORS["bg_elevated"],
                hover_color=COLORS["bg_hover"],
                corner_radius=6,
                command=lambda f=filepath: self.open_file(f)
            )
            open_btn.place(relx=1, y=6, x=-96)

            folder_btn = ctk.CTkButton(
                file_item,
                text="📂",
                width=28,
                height=28,
                fg_color=COLORS["bg_elevated"],
                hover_color=COLORS["bg_hover"],
                corner_radius=6,
                command=lambda f=filepath: self.open_folder(f)
            )
            folder_btn.place(relx=1, y=6, x=-62)

            del_btn = ctk.CTkButton(
                file_item,
                text="🗑️",
                width=28,
                height=28,
                fg_color=COLORS["accent_red"],
                hover_color="#dc2626",
                corner_radius=6,
                command=lambda f=filepath: self.delete_single_file(f)
            )
            del_btn.place(relx=1, y=6, x=-28)

        # 标记详情属于哪一行
        row._detail = detail

    def _batch_render_files(self, row, detail, files, start_idx):
        """分批渲染文件项，每批少量保持UI响应"""
        # 如果行已经收起，停止加载
        if not detail.winfo_exists():
            return

        batch_size = 5  # 每批5个文件
        end_idx = min(start_idx + batch_size, len(files))

        for i in range(start_idx, end_idx):
            filepath = files[i]
            self._create_single_file_item(detail, filepath)

        # 更新进度提示（如果存在）
        if hasattr(row, '_file_detail_progress') and row._file_detail_progress.winfo_exists():
            row._file_detail_progress.configure(text=f"已加载 {end_idx}/{len(files)} 个文件...")

        if end_idx < len(files):
            # 继续下一批，间隔16ms保持UI响应
            self.after(16, lambda: self._batch_render_files(row, detail, files, end_idx))
        else:
            # 加载完成，移除进度提示
            if hasattr(row, '_file_detail_progress') and row._file_detail_progress.winfo_exists():
                row._file_detail_progress.destroy()
                delattr(row, '_file_detail_progress')

    def _create_single_file_item(self, detail, filepath):
        """创建单个文件项 - 抽离出来供分批调用"""
        import tkinter as tk
        file_item = ctk.CTkFrame(detail, fg_color=COLORS["bg_dark"], corner_radius=6, height=40)
        file_item.pack(fill="x", pady=2, padx=(60, 12))
        file_item.pack_propagate(False)

        var = tk.BooleanVar(value=filepath in self.selected_files)
        # 复选框靠左放置 - width/height 在构造函数
        cb = ctk.CTkCheckBox(
            file_item,
            text="",
            variable=var,
            width=24,
            checkbox_width=16,
            checkbox_height=16,
            command=lambda f=filepath, v=var: self.toggle_file(f, v.get())
        )
        cb.place(x=6, y=8)

        # 图标 + 路径文本靠左，占据剩余空间
        icon_label = ctk.CTkLabel(
            file_item,
            text=self.get_file_icon(filepath),
            font=ctk.CTkFont(size=14),
            width=20,
            height=20
        )
        icon_label.place(x=42, y=10)

        # 获取文件大小并格式化
        try:
            size = os.path.getsize(filepath)
            size_str = self.format_size(size)
        except:
            size_str = "unknown"
        path_text = f"{os.path.basename(filepath)}  {os.path.dirname(filepath)}  [{size_str}]"
        text_label = ctk.CTkLabel(
            file_item,
            text=path_text,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            anchor="w",
            width=1  # width 在构造函数
        )
        text_label.place(x=72, y=0, relwidth=1, relheight=1)

        # 打开文件、打开文件夹、删除 三个按钮靠右
        open_btn = ctk.CTkButton(
            file_item,
            text="▶",
            width=28,
            height=28,
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["bg_hover"],
            corner_radius=6,
            command=lambda f=filepath: self.open_file(f)
        )
        open_btn.place(relx=1, y=6, x=-96)

        folder_btn = ctk.CTkButton(
            file_item,
            text="📂",
            width=28,
            height=28,
            fg_color=COLORS["bg_elevated"],
            hover_color=COLORS["bg_hover"],
            corner_radius=6,
            command=lambda f=filepath: self.open_folder(f)
        )
        folder_btn.place(relx=1, y=6, x=-62)

        del_btn = ctk.CTkButton(
            file_item,
            text="🗑️",
            width=28,
            height=28,
            fg_color=COLORS["accent_red"],
            hover_color="#dc2626",
            corner_radius=6,
            command=lambda f=filepath: self.delete_single_file(f)
        )
        del_btn.place(relx=1, y=6, x=-28)
        
    def _collapse_row(self, row):
        """收起行"""
        row._expanded = False
        if hasattr(row, '_detail') and row._detail.winfo_exists():
            row._detail.destroy()
        
    def _on_tree_select(self, event):
        """Treeview选中事件"""
        selection = self.tree.selection()
        if selection:
            idx = int(selection[0])
            if idx < len(self.duplicates):
                self._show_group_detail(idx)
                
    def _show_group_detail(self, idx: int):
        """显示组详情"""
        group = self.duplicates[idx]
        
        # 创建详情窗口
        detail_win = tk.Toplevel(self)
        detail_win.title(f"重复组 #{idx + 1}")
        detail_win.geometry("800x500")
        detail_win.configure(bg=COLORS["bg_dark"])
        
        # 详情内容
        header = tk.Frame(detail_win, bg=COLORS["bg_card"], height=50)
        header.pack(fill="x", padx=10, pady=10)
        
        tk.Label(header, text=f"MD5: {group['hash']}", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(side="left", padx=15, pady=10)
        tk.Label(header, text=f"大小: {self.format_size(group['size'])}", bg=COLORS["bg_card"], fg=COLORS["text_muted"], font=("微软雅黑", 10)).pack(side="right", padx=15, pady=10)
        
        # 文件列表
        list_frame = ctk.CTkScrollableFrame(detail_win, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        for file_idx, filepath in enumerate(group['paths']):
            file_row = ctk.CTkFrame(list_frame, fg_color=COLORS["bg_elevated"], corner_radius=8, height=50)
            file_row.pack(fill="x", pady=4)
            file_row.pack_propagate(False)
            
            var = ctk.BooleanVar(value=filepath in self.selected_files)
            ctk.CTkCheckBox(file_row, text="", variable=var, width=30).pack(side="left", padx=10)
            ctk.CTkLabel(file_row, text=self.get_file_icon(filepath), font=ctk.CTkFont(size=20)).pack(side="left")
            
            info = ctk.CTkFrame(file_row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, pady=6)
            tk.Label(info, text=os.path.basename(filepath), bg=COLORS["bg_elevated"], fg=COLORS["text_primary"], font=("微软雅黑", 11), anchor="w").pack(fill="x")
            tk.Label(info, text=filepath, bg=COLORS["bg_elevated"], fg=COLORS["text_muted"], font=("微软雅黑", 9), anchor="w").pack(fill="x")
            
            btn_f = ctk.CTkFrame(file_row, fg_color="transparent")
            btn_f.pack(side="right", padx=8)
            ctk.CTkButton(btn_f, text="📂", width=36, height=36, fg_color=COLORS["bg_hover"], corner_radius=8, command=lambda f=filepath: self.open_folder(f)).pack(side="left", padx=2)
            ctk.CTkButton(btn_f, text="🗑️", width=36, height=36, fg_color=COLORS["accent_red"], hover_color="#dc2626", corner_radius=8, command=lambda f=filepath: self.delete_single_file(f)).pack(side="left", padx=2)
        
        # 底部按钮
        bottom = tk.Frame(detail_win, bg=COLORS["bg_card"], height=50)
        bottom.pack(fill="x", padx=10, pady=(0, 10))
        bottom.pack_propagate(False)
        
        ctk.CTkButton(bottom, text="全选 (保留第一个)", width=150, height=36, fg_color=COLORS["accent_blue"], corner_radius=8, command=lambda: self.select_all_in_group(group)).pack(side="left", padx=15, pady=7)
        ctk.CTkButton(bottom, text="删除选中", width=150, height=36, fg_color=COLORS["accent_red"], hover_color="#dc2626", corner_radius=8, command=self.delete_selected).pack(side="right", padx=15, pady=7)
            
    def create_group_card(self, idx: int, group: dict):
        """创建重复组卡片 - 现代化设计"""
        # 主卡片
        card = ModernCard(
            self.result_frame,
            hover=True,
            fg_color=(COLORS["bg_card"], COLORS["bg_card"]),
            corner_radius=16,
            border_width=1,
            border_color=(COLORS["border"], COLORS["border"])
        )
        card.pack(fill="x", pady=(0, 16))
        
        # 卡片头部
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 12))
        
        # 左侧信息
        info = ctk.CTkFrame(header, fg_color="transparent")
        info.pack(side="left")
        
        # 组号 + 文件数
        group_header = ctk.CTkFrame(info, fg_color="transparent")
        group_header.pack(anchor="w")
        
        # 组号标签 - 带渐变背景
        group_badge = ctk.CTkFrame(
            group_header,
            fg_color=(COLORS["accent_blue"], COLORS["accent_purple"]),
            corner_radius=6,
            height=24
        )
        group_badge.pack(side="left", padx=(0, 10))
        group_badge.pack_propagate(False)
        
        ctk.CTkLabel(
            group_badge,
            text=f"  重复组 #{idx + 1}  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        # 元信息
        meta_text = f"📦 {len(group['paths'])} 个文件  ·  {self.format_size(group['size'])}  ·  MD5: {group['hash'][:10]}..."
        ctk.CTkLabel(
            info, 
            text=meta_text, 
            text_color=COLORS["text_muted"], 
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", pady=(6, 0))
        
        # 右侧操作按钮
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right")
        
        select_all_btn = ctk.CTkButton(
            actions, 
            text="全选", 
            width=70, 
            height=30, 
            fg_color=COLORS["accent_blue"],
            hover_color="#2563eb",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.select_all_in_group(group)
        )
        select_all_btn.pack(side="left", padx=(0, 6))
        
        delete_group_btn = ctk.CTkButton(
            actions, 
            text="删重", 
            width=70, 
            height=30, 
            fg_color=COLORS["accent_red"], 
            hover_color="#dc2626",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.quick_delete_group(group)
        )
        delete_group_btn.pack(side="left")
        
        # 文件列表容器
        files_frame = ModernCard(
            card,
            hover=False,
            fg_color=(COLORS["bg_dark"], COLORS["bg_dark"]),
            corner_radius=12,
            border_width=0
        )
        files_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        
        # 文件列表内边距容器
        files_inner = ctk.CTkFrame(files_frame, fg_color="transparent")
        files_inner.pack(fill="both", expand=True, padx=12, pady=10)
        
        for file_idx, filepath in enumerate(group['paths']):
            # 文件行 - 使用实色而非透明
            is_even = file_idx % 2 == 0
            row_color = COLORS["bg_elevated"] if is_even else COLORS["bg_dark"]
            file_row = ctk.CTkFrame(
                files_inner, 
                fg_color=row_color,
                corner_radius=8,
                height=56
            )
            file_row.pack(fill="x", pady=3)
            file_row.pack_propagate(False)
            
            # 悬停效果
            def on_row_hover(e, row=file_row):
                row.configure(fg_color=COLORS["bg_hover"])
            def on_row_leave(e, row=file_row, is_e=is_even):
                row.configure(fg_color=COLORS["bg_elevated"] if is_e else COLORS["bg_dark"])
            
            file_row.bind("<Enter>", on_row_hover)
            file_row.bind("<Leave>", on_row_leave)
            
            # 左侧：复选框
            var = ctk.BooleanVar(value=filepath in self.selected_files)
            cb = ctk.CTkCheckBox(
                file_row, 
                text="", 
                variable=var, 
                width=32, 
                checkbox_width=20,
                checkbox_height=20,
                corner_radius=4,
                command=lambda f=filepath, v=var: self.toggle_file(f, v.get())
            )
            cb.pack(side="left", padx=(10, 8))
            
            # 文件图标
            icon_label = ctk.CTkLabel(
                file_row, 
                text=self.get_file_icon(filepath), 
                font=ctk.CTkFont(size=20)
            )
            icon_label.pack(side="left", padx=(0, 10))
            
            # 文件信息
            file_info = ctk.CTkFrame(file_row, fg_color="transparent")
            file_info.pack(side="left", fill="both", expand=True, pady=8)
            
            # 文件名
            name_label = ctk.CTkLabel(
                file_info, 
                text=os.path.basename(filepath), 
                font=ctk.CTkFont(size=13, weight="bold"), 
                anchor="w", 
                text_color=COLORS["text_primary"]
            )
            name_label.pack(anchor="w", fill="x")
            
            # 路径
            path_label = ctk.CTkLabel(
                file_info, 
                text=os.path.dirname(filepath), 
                text_color=COLORS["text_muted"], 
                font=ctk.CTkFont(size=10), 
                anchor="w"
            )
            path_label.pack(anchor="w", fill="x")
            
            # 右侧操作按钮组
            btn_frame = ctk.CTkFrame(file_row, fg_color="transparent")
            btn_frame.pack(side="right", padx=(8, 10))
            
            # 打开文件
            open_btn = ctk.CTkButton(
                btn_frame, 
                text="▶", 
                width=32, 
                height=32, 
                fg_color=COLORS["accent_green"], 
                hover_color="#16a34a",
                corner_radius=8,
                text_color="white",
                font=ctk.CTkFont(size=14),
                command=lambda f=filepath: self.open_file(f)
            )
            open_btn.pack(side="left", padx=2)
            
            # 打开文件夹
            folder_btn = ctk.CTkButton(
                btn_frame, 
                text="📂", 
                width=32, 
                height=32, 
                fg_color=COLORS["bg_elevated"], 
                hover_color=COLORS["bg_hover"],
                corner_radius=8,
                border_color=COLORS["border"],
                border_width=1,
                command=lambda f=filepath: self.open_folder(f)
            )
            folder_btn.pack(side="left", padx=2)
            
            # 删除文件
            delete_btn = ctk.CTkButton(
                btn_frame, 
                text="🗑️", 
                width=32, 
                height=32, 
                fg_color=COLORS["accent_red"], 
                hover_color="#dc2626",
                corner_radius=8,
                text_color="white",
                command=lambda f=filepath: self.delete_single_file(f)
            )
            delete_btn.pack(side="left", padx=2)
            
    def get_file_icon(self, filepath: str) -> str:
        """获取文件图标"""
        icons = {
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬',
            '.mp3': '🎵', '.wav': '🎵',
            '.pdf': '📕', '.doc': '📘', '.docx': '📘',
            '.zip': '📦', '.rar': '📦',
            '.txt': '📝', '.log': '📝',
        }
        return icons.get(os.path.splitext(filepath)[1].lower(), '📄')
        
    def toggle_file(self, filepath: str, selected: bool):
        """切换文件选中状态"""
        if selected:
            self.selected_files.add(filepath)
        else:
            self.selected_files.discard(filepath)
        self.update_stats()
        
    def open_folder(self, filepath: str):
        """打开文件所在文件夹"""
        folder = os.path.dirname(filepath)
        if os.path.exists(folder):
            os.startfile(folder)
            self.add_log(f"📂 已打开: {folder}")
        else:
            messagebox.showerror("错误", "文件夹不存在")
            
    def open_file(self, filepath: str):
        """直接打开文件"""
        if os.path.exists(filepath):
            os.startfile(filepath)
            self.add_log(f"▶ 已打开: {filepath}")
        else:
            messagebox.showerror("错误", "文件不存在")
            
    def delete_single_file(self, filepath: str):
        """删除单个文件到回收站 - 增量更新，不重新扫描"""
        if messagebox.askyesno("确认删除", f"确定要将此文件移到回收站？\n\n{filepath}"):
            try:
                if os.path.exists(filepath):
                    # 在删除前获取文件大小
                    file_size = os.path.getsize(filepath)
                    send2trash.send2trash(filepath)
                    self.add_log(f"🗑️ 已移到回收站: {os.path.basename(filepath)}")

                    # 从选中集合移除
                    if filepath in self.selected_files:
                        self.selected_files.discard(filepath)

                    # 从 duplicates 中移除这个文件
                    need_rerender = False
                    # 遍历原列表，找到正确的组（从后往前遍历避免删除影响索引）
                    for i in range(len(self.duplicates) - 1, -1, -1):
                        group = self.duplicates[i]
                        if filepath in group['paths']:
                            group['paths'].remove(filepath)
                            self.duplicate_files -= 1
                            self.wasted_space -= file_size

                            # 如果组内只剩 <=1 个文件，整个组删掉
                            if len(group['paths']) <= 1:
                                del self.duplicates[i]
                                self.duplicate_groups -= 1

                            need_rerender = True
                            break

                    self.update_stats()
                    if need_rerender:
                        self.render_results()
                else:
                    messagebox.showerror("错误", "文件不存在")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {str(e)}")
        
    def select_all_in_group(self, group: dict):
        """选中组内除第一个外的所有文件"""
        for filepath in group['paths'][1:]:
            self.selected_files.add(filepath)
        self.update_stats()
        self.render_results()
        
    def quick_delete_group(self, group: dict):
        """快速删除组内除第一个外的所有文件到回收站 - 增量更新，不重新扫描"""
        if len(group['paths']) < 2:
            return
        if messagebox.askyesno("确认删除", f"确定要将这 {len(group['paths']) - 1} 个重复文件移到回收站？\n\n保留: {os.path.basename(group['paths'][0])}"):
            deleted_count = 0
            total_wasted = 0

            # 删除每个文件
            for filepath in list(group['paths'][1:]):
                try:
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        send2trash.send2trash(filepath)
                        deleted_count += 1
                        total_wasted += size
                        self.add_log(f"🗑️ 已删除: {os.path.basename(filepath)}")
                        group['paths'].remove(filepath)
                        if filepath in self.selected_files:
                            self.selected_files.discard(filepath)
                except Exception as e:
                    self.add_log(f"❌ 删除失败: {filepath}")

            # 更新统计
            self.duplicate_files -= deleted_count
            self.wasted_space -= total_wasted

            # 如果组内只剩 <=1 个文件，整个组删掉
            if len(group['paths']) <= 1:
                self.duplicates.remove(group)
                self.duplicate_groups -= 1

            self.update_stats()
            self.render_results()

    def batch_quick_delete(self):
        """批量快速删重 - 所有重复组各保留第一个，删除其余"""
        if not self.duplicates:
            messagebox.showinfo("提示", "没有可删除的重复文件")
            return

        # 计算总共要删除多少文件
        total_to_delete = sum(len(group['paths']) - 1 for group in self.duplicates if len(group['paths']) > 1)
        if total_to_delete == 0:
            messagebox.showinfo("提示", "没有可删除的重复文件")
            return

        if messagebox.askyesno("确认批量删重",
            f"确定要对所有 {len(self.duplicates)} 个重复组执行批量删重吗？\n\n"
            f"每个重复组将保留第一个文件，其余 {total_to_delete} 个文件将移到回收站。\n\n"
            "此操作不可撤销，但文件可以从回收站恢复。"):

            deleted_count = 0
            total_wasted = 0

            # 遍历所有重复组，从后往前删除（避免列表遍历时修改导致问题）
            for group in list(reversed(self.duplicates)):
                if len(group['paths']) < 2:
                    continue

                # 删除每个文件（从第二个开始）
                for filepath in list(group['paths'][1:]):
                    try:
                        if os.path.exists(filepath):
                            size = os.path.getsize(filepath)
                            send2trash.send2trash(filepath)
                            deleted_count += 1
                            total_wasted += size
                            self.add_log(f"🗑️ 已删除: {os.path.basename(filepath)}")
                            group['paths'].remove(filepath)
                            if filepath in self.selected_files:
                                self.selected_files.discard(filepath)
                    except Exception as e:
                        self.add_log(f"❌ 删除失败: {filepath}")

                # 如果组内只剩 <=1 个文件，整个组删掉
                if len(group['paths']) <= 1:
                    self.duplicates.remove(group)
                    self.duplicate_groups -= 1

            # 更新统计
            self.duplicate_files -= deleted_count
            self.wasted_space -= total_wasted
            self.update_stats()
            self.render_results()

            self.add_log(f"✅ 批量删重完成，共删除 {deleted_count} 个文件，可节省 {self.format_size(total_wasted)}")

    def show_smart_select_menu(self):
        """显示智能选择菜单，弹出对话框让用户选择规则"""
        if not self.duplicates:
            messagebox.showinfo("提示", "请先扫描获取重复文件")
            return

        # 创建弹出菜单
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="✅ 每个组保留第一个文件 (选择其余)",
                         command=lambda: self.smart_select_keep("first"))
        menu.add_command(label="📅 保留最新修改的文件",
                         command=lambda: self.smart_select_keep("newest"))
        menu.add_command(label="📅 保留最早修改的文件",
                         command=lambda: self.smart_select_keep("oldest"))
        menu.add_command(label="📂 保留路径最短的文件",
                         command=lambda: self.smart_select_keep("shortest_path"))

        # 在按钮位置弹出
        x = self.smart_select_btn.winfo_rootx()
        y = self.smart_select_btn.winfo_rooty() + self.smart_select_btn.winfo_height()
        menu.tk_popup(x, y)

    def smart_select_keep(self, rule: str):
        """根据规则智能选择要删除的文件（保留一个，选中其余）"""
        if not self.duplicates:
            return

        # 清空之前的选择
        self.selected_files.clear()
        total_selected = 0

        for group in self.duplicates:
            paths = group['paths']
            if len(paths) < 2:
                continue

            if rule == "first":
                # 保留第一个，选后面所有
                to_select = paths[1:]

            elif rule == "newest":
                # 保留最新修改的，选其余
                # 获取每个文件修改时间
                path_mtimes = []
                for p in paths:
                    try:
                        mtime = os.path.getmtime(p)
                    except:
                        mtime = 0
                    path_mtimes.append((mtime, p))
                # 按修改时间排序，最新排最后
                path_mtimes.sort()
                keep_path = path_mtimes[-1][1]
                to_select = [p for _, p in path_mtimes if p != keep_path]

            elif rule == "oldest":
                # 保留最早修改的，选其余
                path_mtimes = []
                for p in paths:
                    try:
                        mtime = os.path.getmtime(p)
                    except:
                        mtime = 0
                    path_mtimes.append((mtime, p))
                path_mtimes.sort()
                keep_path = path_mtimes[0][1]
                to_select = [p for _, p in path_mtimes if p != keep_path]

            elif rule == "shortest_path":
                # 保留路径最短的（通常在更上层目录），选其余
                path_lengths = [(len(p.split(os.sep)), p) for p in paths]
                path_lengths.sort()
                keep_path = path_lengths[0][1]
                to_select = [p for _, p in path_lengths if p != keep_path]

            else:
                to_select = paths[1:]

            # 添加到选中集合
            for filepath in to_select:
                if os.path.exists(filepath):
                    self.selected_files.add(filepath)
                    total_selected += 1

        self.update_stats()
        self.render_results()
        self.add_log(f"✅ 智能选择完成: {total_selected} 个文件已选中")

        if total_selected > 0:
            messagebox.showinfo("完成", f"已按规则选中 {total_selected} 个文件\n\n点击左侧「删除选中文件」进行删除")

    def delete_selected(self):
        """删除选中的文件到回收站 - 增量更新，不重新扫描"""
        if not self.selected_files:
            return
        if messagebox.askyesno("确认删除", f"确定要将这 {len(self.selected_files)} 个文件移到回收站？"):
            deleted_count = 0
            total_wasted = 0

            for filepath in list(self.selected_files):
                try:
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        send2trash.send2trash(filepath)
                        self.selected_files.discard(filepath)
                        deleted_count += 1
                        total_wasted += size
                        self.add_log(f"🗑️ 已删除: {os.path.basename(filepath)}")

                        # 从 duplicates 中移除这个文件
                        for group in list(self.duplicates):
                            if filepath in group['paths']:
                                group['paths'].remove(filepath)
                                # 如果组内只剩 <=1 个文件，整个组删掉
                                if len(group['paths']) <= 1:
                                    self.duplicates.remove(group)
                                    self.duplicate_groups -= 1
                                break
                except Exception as e:
                    self.add_log(f"❌ 删除失败: {filepath}")

            # 更新统计
            self.duplicate_files -= deleted_count
            self.wasted_space -= total_wasted
            self.update_stats()
            self.render_results()
                
    def export_report(self):
        """导出检测报告"""
        if not self.duplicates:
            messagebox.showinfo("提示", "没有可导出的数据")
            return
            
        filepath = filedialog.asksaveasfilename(title="导出报告", defaultextension=".json", filetypes=[("JSON 文件", "*.json")], initialfile=f"duplicate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        if filepath:
            report = {
                "scan_paths": self.scan_paths,
                "scan_time": datetime.now().isoformat(),
                "stats": {"total_files": self.total_files, "duplicate_groups": self.duplicate_groups, "duplicate_files": self.duplicate_files, "wasted_space_bytes": self.wasted_space},
                "groups": [{"hash": g["hash"], "size": g["size"], "files": g["paths"]} for g in self.duplicates]
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.add_log(f"📊 报告已导出: {filepath}")
            messagebox.showinfo("成功", f"报告已导出到:\n{filepath}")

    def _toggle_theme(self):
        """切换主题 - 实时更新，不需要重启"""
        global COLORS, current_theme

        is_dark = self.theme_switch.get()
        if is_dark:
            current_theme = "dark"
            COLORS.clear()
            COLORS.update(DARK_COLORS)
            ctk.set_appearance_mode("dark")
            self.theme_switch.configure(text="深色")
            self.add_log("🌙 已切换到深色主题")
        else:
            current_theme = "light"
            COLORS.clear()
            COLORS.update(LIGHT_COLORS)
            ctk.set_appearance_mode("light")
            self.theme_switch.configure(text="浅色")
            self.add_log("☀️ 已切换到浅色主题")

        # 重建整个UI，完整应用新主题
        for widget in self.winfo_children():
            widget.destroy()

        self.setup_ui()

        # 恢复状态
        if self.duplicates:
            self.update_stats()
            self.render_results()
        else:
            self.show_empty_state()

        messagebox.showinfo("提示", "主题切换完成，已实时应用")


if __name__ == "__main__":
    app = DuplicateFinderApp()
    app.mainloop()
