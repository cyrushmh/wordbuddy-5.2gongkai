#ifndef CLASSICS_H
#define CLASSICS_H

#ifdef __cplusplus
extern "C" {
#endif

/* 版本字符串（如 "1.0.0"）。返回指针由库分配，需配对调用 classics_free_string。 */
char *classics_version(void);

/* 乱码安全解码：输入字节指针 + 长度，返回 UTF-8 文本（C 串）。
 * 失败时返回空串。返回指针需配对调用 classics_free_string。 */
char *classics_decode(const unsigned char *ptr, unsigned long len);

/* 释放本库返回的 C 字符串。ptr 可为 NULL。 */
void classics_free_string(char *ptr);

#ifdef __cplusplus
}
#endif

#endif /* CLASSICS_H */
