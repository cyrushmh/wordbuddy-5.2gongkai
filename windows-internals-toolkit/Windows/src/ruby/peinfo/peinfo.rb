#!/usr/bin/env ruby
# peinfo.rb — 纯 Ruby 标准库的 PE(Portable Executable) 结构解析器
#
# 与仓库内 C / Rust / Python / .NET / VBA / Java 同源同义，机器可读 JSON
# 输出（--json）字段与 tests/parity_test.py 的对比口径完全一致。
# 零第三方依赖，仅需 Ruby（脚本面向 Ruby 3.x 稳定版）。
#
# 用法:
#   ruby peinfo.rb file.exe          # 打印文本头信息
#   ruby peinfo.rb file.exe --json   # 输出机器可读 JSON
#   ruby peinfo.rb self              # 解析本脚本自身（非 PE 会提示）
require "json"

MACHINES = {
  0x14C => "x86 (Intel 386+)", 0x8664 => "x64 (AMD64)", 0xAA64 => "ARM64",
  0x1C0 => "ARM (32-bit)", 0x14D => "ARM (Thumb/Thumb-2)", 0x200 => "IA64",
  0x9041 => "ARM64X",
}.freeze

SUBSYSTEMS = {
  1 => "Native (驱动/系统)", 2 => "Windows GUI", 3 => "Windows CUI (控制台)",
  7 => "POSIX", 9 => "Windows CE", 10 => "EFI 应用程序", 12 => "EFI ROM",
}.freeze

CHAR_FLAGS = {
  0x0002 => "EXECUTABLE_IMAGE", 0x2000 => "DLL", 0x0100 => "32BIT_MACHINE",
  0x0020 => "LARGE_ADDRESS_AWARE", 0x0001 => "RELOCS_STRIPPED",
  0x0080 => "BYTES_REVERSED_LO", 0x0200 => "DEBUG_STRIPPED",
}.freeze

SEC_FLAGS = {
  0x00000020 => "CNT_CODE", 0x00000040 => "CNT_INITIALIZED_DATA",
  0x00000080 => "CNT_UNINITIALIZED_DATA", 0x20000000 => "MEM_EXECUTE",
  0x40000000 => "MEM_READ", 0x80000000 => "MEM_WRITE", 0x10000000 => "MEM_SHARED",
}.freeze

DATA_DIR_NAMES = %w[
  导出表 导入表 资源表 异常表 安全表 重定位表 调试表
  版权表 全局指针 TLS表 加载配置 绑定导入 IAT
  延迟导入 COM描述符 保留
].freeze

def u16(b, off)
  b[off, 2].unpack1("v")
end

def u32(b, off)
  b[off, 4].unpack1("V")
end

def u64(b, off)
  b[off, 8].unpack1("Q<")
end

def parse(data)
  return [nil, "不是有效 PE：缺少 MZ 头"] unless data[0, 2] == "MZ"
  e_lfanew = u32(data, 0x3C)
  return [nil, format("不是有效 PE：偏移 0x%X 处缺少 PE\\0\\0 签名", e_lfanew)] \
    unless data[e_lfanew, 4] == "PE\x00\x00"
  off = e_lfanew + 4

  # COFF 文件头: <HHIIIHH
  machine, nsec, tds, _psym, _nsym, size_opt, chars = data[off, 20].unpack("vvVVVvv")
  opt_off = off + 20
  magic = u16(data, opt_off)
  is_pe32plus = (magic == 0x20B)
  entry = u32(data, opt_off + 16)
  num_rva = u32(data, opt_off + (is_pe32plus ? 108 : 92))
  if is_pe32plus
    image_base = u64(data, opt_off + 24)
    sec_align = u32(data, opt_off + 32)
    file_align = u32(data, opt_off + 36)
    subsystem = u16(data, opt_off + 68)
    img_size = u32(data, opt_off + 56)
    hdr_size = u32(data, opt_off + 60)
    dd_off = opt_off + 112
  else
    image_base = u32(data, opt_off + 28)
    sec_align = u32(data, opt_off + 32)
    file_align = u32(data, opt_off + 36)
    subsystem = u16(data, opt_off + 68)
    img_size = u32(data, opt_off + 56)
    hdr_size = u32(data, opt_off + 60)
    dd_off = opt_off + 96
  end

  data_dirs = []
  [num_rva, 16].min.times do |i|
    rva = u32(data, dd_off + i * 8)
    size = u32(data, dd_off + i * 8 + 4)
    nm = i < DATA_DIR_NAMES.length ? DATA_DIR_NAMES[i] : "##{i}"
    data_dirs << { "index" => i, "name" => nm, "rva" => rva, "size" => size }
  end

  sec_tbl = opt_off + size_opt
  sections = []
  nsec.times do |i|
    s = sec_tbl + i * 40
    break if s + 40 > data.bytesize

    name = data[s, 8].unpack1("Z8")
    sections << {
      "index" => i,
      "name" => name,
      "virtual_size" => u32(data, s + 8),
      "virtual_address" => u32(data, s + 12),
      "size_of_raw_data" => u32(data, s + 16),
      "pointer_to_raw_data" => u32(data, s + 20),
      "characteristics" => u32(data, s + 36),
    }
  end

  result = {
    "e_lfanew" => e_lfanew,
    "machine" => machine,
    "machine_name" => MACHINES.fetch(machine, "未知"),
    "number_of_sections" => nsec,
    "time_date_stamp" => tds,
    "size_of_optional_header" => size_opt,
    "characteristics" => chars,
    "optional" => {
      "magic" => magic,
      "magic_name" => (is_pe32plus ? "PE32+ (64位)" : "PE32 (32位)"),
      "entry_point" => entry,
      "image_base" => image_base,
      "section_alignment" => sec_align,
      "file_alignment" => file_align,
      "size_of_image" => img_size,
      "size_of_headers" => hdr_size,
      "subsystem" => subsystem,
      "subsystem_name" => SUBSYSTEMS.fetch(subsystem, "未知"),
      "number_of_rva_and_sizes" => num_rva,
    },
    "data_directories" => data_dirs,
    "sections" => sections,
  }
  [result, nil]
end

def to_text(d)
  o = d["optional"]
  lines = []
  lines << "=" * 52
  lines << " PE 结构解析 (Ruby 版)"
  lines << "=" * 52
  lines << "[DOS 头]"
  lines << "  e_magic  = MZ (0x5A4D)"
  lines << format("  e_lfanew = 0x%X  -> NT 头位置", d["e_lfanew"])
  lines << "[COFF 文件头]"
  lines << format("  Machine           = 0x%04X  (%s)", d["machine"], d["machine_name"])
  lines << format("  NumberOfSections  = %d", d["number_of_sections"])
  lines << format("  TimeDateStamp      = 0x%X", d["time_date_stamp"])
  lines << format("  SizeOfOptionalHdr = %d", d["size_of_optional_header"])
  lines << format("  Characteristics   = 0x%04X", d["characteristics"])
  CHAR_FLAGS.each do |bit, nm|
    lines << "      #{nm}" if d["characteristics"] & bit != 0
  end
  lines << "[可选头]"
  lines << format("  Magic             = 0x%04X  (%s)", o["magic"], o["magic_name"])
  lines << format("  EntryPoint (RVA)  = 0x%X", o["entry_point"])
  lines << format("  ImageBase         = 0x%X", o["image_base"])
  lines << format("  SectionAlignment  = 0x%X", o["section_alignment"])
  lines << format("  FileAlignment     = 0x%X", o["file_alignment"])
  lines << format("  SizeOfImage       = 0x%X", o["size_of_image"])
  lines << format("  SizeOfHeaders     = 0x%X", o["size_of_headers"])
  lines << format("  Subsystem         = %d  (%s)", o["subsystem"], o["subsystem_name"])
  lines << "[数据目录]"
  d["data_directories"].each do |dd|
    lines << format("  [%2d] %-12s RVA=0x%X Size=0x%X", dd["index"], dd["name"], dd["rva"], dd["size"])
  end
  lines << "[节表]  共 #{d['number_of_sections']} 节"
  d["sections"].each do |sec|
    lines << format(
      "  #%2d  %-8s  VSize=0x%05X VAddr=0x%05X Raw=0x%05X@%05X",
      sec["index"], sec["name"], sec["virtual_size"], sec["virtual_address"],
      sec["size_of_raw_data"], sec["pointer_to_raw_data"]
    )
  end
  lines << "=" * 52
  lines << "  ✅ 这是一个结构合法的 PE 文件。"
  lines.join("\n")
end

def main
  path = ARGV[0]
  json_mode = ARGV.include?("--json")
  unless path
    warn "用法: ruby peinfo.rb <file.exe|self> [--json]"
    exit 1
  end

  data =
    if path == "self"
      File.binread(__FILE__)
    else
      begin
        File.binread(path)
      rescue SystemCallError => e
        warn "无法读取文件: #{e.message}"
        exit 1
      end
    end

  d, err = parse(data)
  if err
    warn err
    exit 1
  end
  puts(json_mode ? JSON.generate(d) : to_text(d))
end

main if __FILE__ == $PROGRAM_NAME
