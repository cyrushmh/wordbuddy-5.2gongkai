/*
 * PE Viewer —— 原生 Win32 API 图形界面（C11，无第三方依赖）。
 * 交叉编译为 Windows GUI 子系统（subsystem=windows）的 .exe。
 */
#include <windows.h>
#include <commdlg.h>
#include <stdio.h>
#include <string.h>

#define IDC_EDIT 100
#define IDC_OPEN 101

static HWND g_edit;

static DWORD rd32(const unsigned char *p) {
    return (DWORD)p[0] | ((DWORD)p[1] << 8) | ((DWORD)p[2] << 16) | ((DWORD)p[3] << 24);
}
static WORD rd16(const unsigned char *p) {
    return (WORD)(p[0] | (p[1] << 8));
}

static void ParseAndShow(const char *path) {
    HANDLE f = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (f == INVALID_HANDLE_VALUE) { SetWindowTextA(g_edit, "无法打开文件"); return; }
    DWORD sz = GetFileSize(f, NULL);
    unsigned char *buf = (unsigned char *)HeapAlloc(GetProcessHeap(), 0, sz ? sz : 1);
    DWORD rd = 0;
    ReadFile(f, buf, sz, &rd, NULL);
    CloseHandle(f);

    char out[8192];
    out[0] = 0;

    if (sz < 0x40 || buf[0] != 'M' || buf[1] != 'Z') {
        strcat(out, "不是合法 PE（缺少 MZ 头）\n");
    } else {
        DWORD e_lfanew = rd32(buf + 0x3C);
        if (e_lfanew + 4 > sz || memcmp(buf + e_lfanew, "PE\0\0", 4) != 0) {
            strcat(out, "缺少 PE 签名\n");
        } else {
            WORD machine = rd16(buf + e_lfanew + 4);
            WORD nsec = rd16(buf + e_lfanew + 6);
            WORD optsize = rd16(buf + e_lfanew + 20);
            WORD magic = rd16(buf + e_lfanew + 24);
            int pe32plus = (magic == 0x20B);
            DWORD entry = rd32(buf + e_lfanew + 24 + 16);
            DWORD ib = pe32plus ? rd32(buf + e_lfanew + 24 + 24) : rd32(buf + e_lfanew + 24 + 28);
            WORD subsys = rd16(buf + e_lfanew + 24 + 68);
            const char *arch = machine == 0x8664 ? "x64" : (machine == 0x14c ? "x86" : "其它");
            sprintf(out + strlen(out),
                "文件: %s\n架构: %s (machine=%04X)\n节数: %d\nMagic: %s\n入口点: %08X\nImageBase: %08X\n子系统: %d\n",
                path, arch, machine, nsec, pe32plus ? "PE32+" : "PE32", entry, ib, subsys);
            DWORD sec = e_lfanew + 24 + optsize;
            char nm[9];
            for (int i = 0; i < nsec; i++) {
                DWORD s = sec + (DWORD)(i * 40);
                if (s + 40 > sz) break;
                memset(nm, 0, 9);
                memcpy(nm, buf + s, 8);
                DWORD vaddr = rd32(buf + s + 12);
                DWORD vsize = rd32(buf + s + 8);
                DWORD rawptr = rd32(buf + s + 20);
                DWORD rawsize = rd32(buf + s + 16);
                sprintf(out + strlen(out), "  节 %d: %-8s VA=%08X VSize=%08X Raw=%08X/%08X\n",
                        i, nm, vaddr, vsize, rawptr, rawsize);
            }
        }
    }
    HeapFree(GetProcessHeap(), 0, buf);
    SetWindowTextA(g_edit, out);
}

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE:
        g_edit = CreateWindowExA(WS_EX_CLIENTEDGE, "EDIT", "",
            WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_HSCROLL | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL,
            10, 10, 560, 360, hwnd, (HMENU)IDC_EDIT, NULL, NULL);
        CreateWindowExA(0, "BUTTON", "打开 PE 文件...", WS_CHILD | WS_VISIBLE,
            10, 384, 180, 28, hwnd, (HMENU)IDC_OPEN, NULL, NULL);
        SetWindowTextA(g_edit, "点击「打开 PE 文件...」选择一个 .exe/.dll 查看 PE 头信息。\n本程序自身即合法 PE。");
        break;
    case WM_COMMAND:
        if (LOWORD(wp) == IDC_OPEN) {
            char file[MAX_PATH] = {0};
            OPENFILENAMEA ofn = {0};
            ofn.lStructSize = sizeof(ofn);
            ofn.hwndOwner = hwnd;
            ofn.lpstrFile = file;
            ofn.nMaxFile = MAX_PATH;
            ofn.lpstrFilter = "PE 文件\0*.exe;*.dll;*.sys;*.ocx\0所有文件\0*.*\0";
            ofn.Flags = OFN_FILEMUSTEXIST;
            if (GetOpenFileNameA(&ofn)) ParseAndShow(file);
        }
        break;
    case WM_DESTROY:
        PostQuitMessage(0);
        break;
    default:
        return DefWindowProcA(hwnd, msg, wp, lp);
    }
    return 0;
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmd, int nshow) {
    (void)hPrev; (void)cmd;
    WNDCLASSEXA wc = {0};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInst;
    wc.lpszClassName = "PeViewCls";
    wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    RegisterClassExA(&wc);

    HWND w = CreateWindowExA(0, "PeViewCls", "PE Viewer (Win32 API)",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 600, 460,
        NULL, NULL, hInst, NULL);
    ShowWindow(w, nshow);
    UpdateWindow(w);

    MSG m;
    while (GetMessageA(&m, NULL, 0, 0)) {
        TranslateMessage(&m);
        DispatchMessageA(&m);
    }
    return 0;
}
