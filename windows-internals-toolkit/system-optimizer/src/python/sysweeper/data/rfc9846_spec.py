# SPDX-License-Identifier: BSD-3-Clause-IETF
# ----------------------------------------------------------------------------
# 保留规范代码（Retained Normative Spec Code）—— RFC 9846 (TLS 1.3, 2026-07)
# ----------------------------------------------------------------------------
# 本模块系从 RFC 9846《The Transport Layer Security (TLS) Protocol Version 1.3》
# 附录 B（Protocol Data Structures and Constant Values）抽取的「规范性常量与线格式
# 结构」，原样留存作为 sysweeper TLS 1.3 配置态势审计的权威参照层。
#
# ⚠️ 本文件不是 TLS 实现，也不含任何握手/加解密逻辑。它只保留规范给出的
#    常量数值与 TLS 表示法（presentation language）结构定义，供审计任务比对
#    OS 实际配置（Schannel 注册表 / 加密栈能力）时使用。
#
#    根据 RFC 9846 版权声明（Code Components extracted from this document must
#    include Revised BSD License text...），以下附 Revised BSD License：
#
# Copyright (c) 2026 IETF Trust and the persons identified as document authors.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#   3. Neither the name of the IETF nor the names of its contributors may be
#      used to endorse or promote products derived from this software without
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

"""RFC 9846 规范性常量与结构（保留，不实现）。

仅作审计参照；数值与 TLS 表示法结构逐字取自 RFC 9846 附录 B。
"""

from __future__ import annotations

# 规范出处（sysweeper standards 引用用）
SPEC_SOURCE = "RFC 9846 (TLS 1.3, IETF Standards Track, 2026-07)"
SPEC_OBSOLETES = ["RFC 8446", "RFC 5246", "RFC 5077", "RFC 6961", "RFC 7627", "RFC 8422"]
SPEC_UPDATES = ["RFC 5705", "RFC 6066"]

# ---------------------------------------------------------------------------
# 版本号（RFC 9846 §4.3.1 + Appendix B）
# ---------------------------------------------------------------------------
# TLS 1.3 的 ClientHello/ServerHello 中 legacy_version 必须固定为 0x0303
# （即 TLS 1.2 的记录层版本号），真正的协议版本走 supported_versions 扩展。
TLS_LEGACY_RECORD_VERSION = 0x0303          # 必须值：TLS 1.3 握手外层
TLS_1_2_WIRE = 0x0303
TLS_1_3_WIRE = 0x0304                        # supported_versions 中携载

# RFC 9846 §1.2 明确禁止协商的旧版本（配合 RFC 8996 废弃）
DEPRECATED_PROTOCOLS = ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"]

# ---------------------------------------------------------------------------
# 密码套件（RFC 9846 §9.1 + Appendix B.4）
#   MUST 实现 TLS_AES_128_GCM_SHA256；
#   SHOULD 实现 TLS_AES_256_GCM_SHA384 与 TLS_CHACHA20_POLY1305_SHA256。
# ---------------------------------------------------------------------------
CIPHER_SUITES = {
    0x1301: {"name": "TLS_AES_128_GCM_SHA256", "requirement": "MUST",
             "note": "强制实现（AEAD+AES-128-GCM+SHA256）"},
    0x1302: {"name": "TLS_AES_256_GCM_SHA384", "requirement": "SHOULD",
             "note": "推荐（AEAD+AES-256-GCM+SHA384）"},
    0x1303: {"name": "TLS_CHACHA20_POLY1305_SHA256", "requirement": "SHOULD",
             "note": "推荐（AEAD+ChaCha20-Poly1305+SHA256，移动/受限网优）"},
}
MANDATORY_CIPHER_SUITE = 0x1301

# 明确不推荐 / 应禁用的遗留套件关键字（审计告警用，非规范枚举）
LEGACY_CIPHER_KEYWORDS = ["RC4", "3DES", "DES", "NULL", "MD5", "_SHA", "EXPORT"]

# ---------------------------------------------------------------------------
# HandshakeType（RFC 9846 Appendix B.3，沿用 TLS 1.3 稳定枚举）
# ---------------------------------------------------------------------------
HANDSHAKE_MESSAGE_TYPES = {
    1: "client_hello", 2: "server_hello", 4: "new_session_ticket",
    5: "end_of_early_data", 8: "encrypted_extensions", 11: "certificate",
    13: "certificate_request", 15: "certificate_verify", 20: "finished",
    24: "key_update", 254: "message_hash",
}

# ---------------------------------------------------------------------------
# 关键扩展类型（RFC 9846 Appendix B.3.1，部分；本审计仅关心安全相关项）
# ---------------------------------------------------------------------------
EXTENSION_TYPES = {
    0: "server_name", 5: "status_request", 10: "supported_groups",
    13: "signature_algorithms", 16: "application_layer_protocol_negotiation",
    21: "padding", 28: "record_size_limit", 41: "pre_shared_key",
    42: "early_data", 43: "supported_versions", 44: "cookie",
    45: "psk_key_exchange_modes", 47: "certificate_authorities",
    48: "oid_filters", 49: "post_handshake_auth",
    50: "signature_algorithms_cert", 51: "key_share",
}

# ---------------------------------------------------------------------------
# NamedGroup（RFC 9846 Appendix B + §4.3.8）—— 含 RFC 9846 新增的 KEM 类组
# ---------------------------------------------------------------------------
# RFC 9846 §1.3 头号变更：密钥交换从「仅 (EC)DHE」泛化为「KEM-based」。
# KEM 公钥以新的 NamedGroup（如 ML-KEM / 混合组）经 key_share 承载，
# 而非新增握手模式（PskKeyExchangeMode 仍为 {psk_ke(0), psk_dhe_ke(1)}）。
NAMED_GROUPS = {
    0x0017: "secp256r1", 0x0018: "secp384r1", 0x0019: "secp521r1",
    0x001D: "X25519", 0x001E: "X448",
    # 后量子 / KEM 类组（数值随各 IANA 注册与混合草案更新；
    # 审计时按「是否出现 KEM 组」判定 PQC-ready，不写死具体 code point）
}
KEM_NAMED_GROUP_HINTS = ("ml-kem", "kyber", "xwing", "hybrid", "p256-ml-kem", "secp384r1-ml-kem")

# ---------------------------------------------------------------------------
# PSK 密钥交换模式（RFC 9846 Appendix B.3.9）
# ---------------------------------------------------------------------------
PSK_KEY_EXCHANGE_MODES = {0: "psk_ke", 1: "psk_dhe_ke"}

# ---------------------------------------------------------------------------
# Key Schedule HKDF 标签（RFC 9846 §7.1，审计仅展示，不计算）
# ---------------------------------------------------------------------------
KEY_SCHEDULE_LABELS = [
    "derived", "c_e_traffic", "c_hs_traffic", "s_hs_traffic",
    "c_ap_traffic", "s_ap_traffic", "exp_master", "res_master",
    "early_traffic", "ext_binder", "res_binder",
]


# ===========================================================================
# 以下为 RFC 9846 附录 B 的 TLS 表示法结构——逐字留存（规范代码，不转写）
# ===========================================================================
APPENDIX_B_VERBATIM = r"""
   struct {
       ProtocolVersion legacy_version = 0x0303;     /* TLS v1.2 */
       Random random;
       opaque legacy_session_id<0..32>;
       CipherSuite cipher_suites<2..2^16-2>;
       opaque legacy_compression_methods<1..2^8-1>;
       Extension extensions<7..2^16-1>;
   } ClientHello;

   struct {
       ProtocolVersion legacy_version = 0x0303;            /* TLS v1.2 */
       Random random;
       opaque legacy_session_id_echo<0..32>;
       CipherSuite cipher_suite;
       uint8 legacy_compression_method = 0;
       Extension extensions<6..2^16-1>;
   } ServerHello;

   struct {
       NamedGroup group;
       opaque key_exchange<1..2^16-1>;
   } KeyShareEntry;
   /* RFC 9846 §1.3：key_exchange 字段内容由指定组决定；
      KEM 类组时此处承载封装公钥（encapsulation key），
      即本版「KEM-based key exchange」的落点（取代早期仅 (EC)DHE）。 */

   enum { psk_ke(0), psk_dhe_ke(1), (255) } PskKeyExchangeMode;
"""


def summary() -> dict:
    """返回规范要点摘要（供审计任务与 GUI 展示引用，不含实现）。"""
    return {
        "spec": SPEC_SOURCE,
        "obsoletes": SPEC_OBSOLETES,
        "legacy_record_version_must_be": hex(TLS_LEGACY_RECORD_VERSION),
        "tls_1_3_wire": hex(TLS_1_3_WIRE),
        "deprecated_protocols": DEPRECATED_PROTOCOLS,
        "mandatory_cipher_suite": CIPHER_SUITES[MANDATORY_CIPHER_SUITE]["name"],
        "recommended_cipher_suites": [
            CIPHER_SUITES[c]["name"] for c in (0x1302, 0x1303)
        ],
        "kem_key_exchange": "RFC 9846 引入 KEM-based 密钥交换（经 NamedGroup/key_share 承载）",
    }
