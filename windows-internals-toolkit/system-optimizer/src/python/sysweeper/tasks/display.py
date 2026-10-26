"""现代设备显示与 GPU 任务（display，platform=any，跨平台）。

只读观测显示服务器（X11/Wayland/Tty）、GPU 与渲染后端、当前分辨率，并显式保留控制台/终端/远程终端
入口；绝不装 GPU 驱动、绝不切 Wayland、绝不改显示配置——严守只读红线。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="display_report",
        platform="any",
        title="现代设备显示与 GPU 只读报告（保留控制台/终端/远程终端）",
        category="maintenance",
        risk="low",
        desc="只读观测显示服务器（XDG_SESSION_TYPE 判 X11/Wayland/Tty）、GPU 与渲染后端"
             "（lspci/glxinfo/vulkaninfo）、当前分辨率（xrandr）；显式确认控制台/终端/远程终端入口"
             "始终保留。推进图形化不移除这些入口。绝不装驱动、绝不切 Wayland。",
        actions=[
            N("display.display_report", "端到端生成现代设备显示与 GPU 报告（显示服务器→GPU→分辨率→终端保留）"),
        ],
        notes=["display 只读观测：只观测、只给指引、绝不写显示配置；控制台/终端/远程终端始终保留。"],
        standards=["[国际] freedesktop XDG_SESSION_TYPE（会话类型）",
                  "[国际] Vulkan（Khronos）/ OpenGL（glxinfo）渲染后端",
                  "[国际] RandR（xrandr 分辨率）/ Wayland 合成器"],
    ),
    Task(
        id="display_gpu_guidance",
        platform="any",
        title="GPU 驱动安装（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出 GPU 驱动安装的规范指引（开源栈优先：Mesa + 对应内核驱动），绝不自动装驱动。",
        actions=[
            M("lspci 确认 GPU 厂商；开源栈优先（amdgpu/i915/nouveau + Mesa）；"
              "远程/服务器无显示需求可保持 headless。",
              "GPU 驱动安装（规范指引，不代执行）"),
            N("display.guide_gpu_driver", "输出 GPU 驱动安装指引（只给步骤，不装驱动/不改配置）"),
        ],
        notes=["装驱动属于写操作，一律只给规范指引；是否施工由用户在系统设置或厂商工具确认。"],
        standards=["[国际] Mesa 开源图形栈 / 各厂商 GPU 内核驱动（amdgpu/i915/nouveau）"],
    ),
]
