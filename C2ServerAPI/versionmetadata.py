import os
import re

full_version = None

_version_line_re = re.compile(r"^\s*version\s*=\s*['\"]([^'\"]+)['\"]\s*$")

with open("pyproject.toml", "r", encoding="utf-8") as f:
    in_poetry = False
    for line in f:
        s = line.strip()
        if s == "[tool.poetry]":
            in_poetry = True
            continue
        if s.startswith("[") and s.endswith("]") and s != "[tool.poetry]":
            in_poetry = False
        if not in_poetry:
            continue
        m = _version_line_re.match(line)
        if m:
            full_version = m.group(1)
            break

if full_version is None:
    raise RuntimeError("Could not find [tool.poetry].version in pyproject.toml")

semver_match = re.search(r"(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?", full_version)
if not semver_match:
    raise RuntimeError(f"Version '{full_version}' is not in a supported format (expected X.Y.Z or X.Y.Z.W)")

a, b, c, d = semver_match.groups()
file_version = f"{int(a)}.{int(b)}.{int(c)}.{int(d or 0)}"

print(f"Building version metadata for {file_version}")

if not os.path.exists("build"):
    os.mkdir("build")

company_name = "OVA"
file_description = "Chivalry 2 Admin Dashboard"
internal_name = "AdminDashboard"
original_filename = "AdminDashboard.exe"
product_name = "Chiv2 Admin Dashboard"

version_info_path = os.path.join("build", "versionfile.txt")
version_info_content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({int(a)}, {int(b)}, {int(c)}, {int(d or 0)}),
    prodvers=({int(a)}, {int(b)}, {int(c)}, {int(d or 0)}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{company_name}'),
            StringStruct('FileDescription', '{file_description}'),
            StringStruct('FileVersion', '{file_version}'),
            StringStruct('InternalName', '{internal_name}'),
            StringStruct('OriginalFilename', '{original_filename}'),
            StringStruct('ProductName', '{product_name}'),
            StringStruct('ProductVersion', '{file_version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

with open(version_info_path, "w", encoding="utf-8") as f:
    f.write(version_info_content)

print(f"Wrote PyInstaller version file: {version_info_path}")