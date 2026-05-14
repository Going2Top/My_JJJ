# fix-telepresence-symlinks.ps1
# 修复 Telepresence mount 后远程 Linux symlink 在 Windows 上失效的问题
#
# 问题: Telepresence 通过 WinFsp 把远程文件系统挂载到 T 盘后，
#       远程 Linux symlink 被呈现为普通文本文件（内容是目标路径字符串），
#       Windows 程序无法自动跟随这些"伪 symlink"。
#
# 解决: 删除旧的 D:\appfile symlink，重建为实体目录。把 T 盘实体文件复制过来，
#       把"伪 symlink"替换为真正的 Windows symlink，指向 T 盘中对应的实体文件。
#       运行时 Windows 会跟随这些链接到 T 盘读取数据。
#
# 用法:
#   .\fix-telepresence-symlinks.ps1 -MountPath "T:\appfile" -OutputPath "D:\appfile"
#   .\fix-telepresence-symlinks.ps1 -MountPath "T:\appfile" -OutputPath "D:\appfile" -WhatIf
#   .\fix-telepresence-symlinks.ps1 -MountPath "T:\appfile" -RemoteRoot "/etc/config" -OutputPath "D:\appfile"

param(
    [Parameter(Mandatory=$true)]
    [string]$MountPath,          # Telepresence mount 在本地的路径，如 "T:\appfile"

    [Parameter(Mandatory=$false)]
    [string]$RemoteRoot = "/",   # MountPath 对应的远程根路径，如 "/" 或 "/etc/config"

    [Parameter(Mandatory=$true)]
    [string]$OutputPath,         # 输出路径（与原名保持一致），如 "D:\appfile"

    [switch]$Force,              # 跳过确认提示

    [switch]$WhatIf              # 仅预览，不做任何修改
)

$ErrorActionPreference = "Stop"

# ============================================================
# 工具函数
# ============================================================

function Write-Info([string]$Msg) {
    Write-Host "[INFO]  $Msg" -ForegroundColor Cyan
}

function Write-Warn([string]$Msg) {
    Write-Host "[WARN]  $Msg" -ForegroundColor Yellow
}

function Write-Error2([string]$Msg) {
    Write-Host "[ERROR] $Msg" -ForegroundColor Red
}

function Write-Success([string]$Msg) {
    Write-Host "[OK]    $Msg" -ForegroundColor Green
}

function Write-Detail([string]$Msg) {
    Write-Host "        $Msg" -ForegroundColor Gray
}

# 判断一个文件是否是 Telepresence 产生的"伪 symlink"（内容为 Linux 路径的普通文本文件）
function Test-IsFakeSymlink([string]$FilePath) {
    if (-not (Test-Path $FilePath -PathType Leaf)) { return $false }
    try { $size = (Get-Item $FilePath).Length } catch { return $false }
    if ($size -eq 0 -or $size -gt 4096) { return $false }
    try { $content = Get-Content -Path $FilePath -Raw -ErrorAction Stop } catch { return $false }
    if ([string]::IsNullOrWhiteSpace($content)) { return $false }
    $content = $content.Trim()
    # Linux 绝对路径或以 ../ ./ 开头的相对路径
    if ($content -match '^/[^\0\r\n]*$') { return $true }
    if ($content -match '^\.\.?/[^\0\r\n]*$') { return $true }
    return $false
}

# 将远程 Linux 绝对路径映射到 T 盘挂载路径
function Convert-AbsoluteLinuxPath([string]$LinuxPath) {
    $linuxPath = $LinuxPath.Trim()
    $normalizedRoot = '/' + $RemoteRoot.TrimStart('/').TrimEnd('/')
    $normalizedRoot = $normalizedRoot.TrimEnd('/')
    if ($normalizedRoot -eq '/' -or $normalizedRoot -eq '') {
        $relative = $linuxPath.TrimStart('/')
    } elseif ($linuxPath.StartsWith($normalizedRoot)) {
        $relative = $linuxPath.Substring($normalizedRoot.Length).TrimStart('/')
    } else {
        return $null
    }
    $mountRoot = $MountPath.TrimEnd('\')
    if ($relative -eq '') { return $mountRoot }
    return $mountRoot + '\' + $relative.Replace('/', '\')
}

# 递归解析"伪 symlink"链，直到找到实体文件
function Resolve-Chain([string]$StartPath) {
    $visited = @{}
    $chain = @()
    $current = $StartPath
    while ($true) {
        if ($visited.ContainsKey($current)) {
            return @{ RealPath = $null; Chain = $chain; Error = "循环引用: $current" }
        }
        $visited[$current] = $true
        if (-not (Test-Path $current)) {
            return @{ RealPath = $null; Chain = $chain; Error = "文件不存在: $current" }
        }
        if (-not (Test-IsFakeSymlink $current)) {
            return @{ RealPath = $current; Chain = $chain; Error = $null }
        }
        $targetContent = (Get-Content -Path $current -Raw).Trim()
        $chain += "$current  ->  $targetContent"
        if ($targetContent.StartsWith('/')) {
            $next = Convert-AbsoluteLinuxPath -LinuxPath $targetContent
            if ($null -eq $next) {
                $next = $MountPath.TrimEnd('\') + '\' + $targetContent.TrimStart('/').Replace('/', '\')
            }
        } else {
            $currentDir = [System.IO.Path]::GetDirectoryName($current)
            $combined = $currentDir + '\' + $targetContent.Replace('/', '\')
            $next = [System.IO.Path]::GetFullPath($combined)
        }
        $current = $next
    }
}

# ============================================================
# 主流程
# ============================================================

function Main {
    $mt = [System.IO.Path]::GetFullPath($MountPath).TrimEnd('\')
    $out = [System.IO.Path]::GetFullPath($OutputPath).TrimEnd('\')

    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Magenta
    Write-Host "  Telepresence 远程 Symlink 修复工具" -ForegroundColor Magenta
    Write-Host "=============================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Info "挂载路径 (T盘):   $mt"
    Write-Info "远程根路径:        $RemoteRoot"
    Write-Info "输出路径:          $out"
    Write-Info "模式:              $(if ($WhatIf) { '预览 (不修改)' } else { '执行' })"
    Write-Host ""

    # --- 0. 校验 ---
    if (-not (Test-Path $mt)) {
        Write-Error2 "挂载路径不存在: $mt。请确认 Telepresence 已 connect 且 mount 已生效。"
        exit 1
    }
    if ($out -eq $mt) {
        Write-Error2 "输出路径不能与挂载路径相同。"
        exit 1
    }

    # --- 0.5 处理已存在的 OutputPath ---
    if (Test-Path $out) {
        $isReparse = $false
        try {
            $item = Get-Item $out -Force -ErrorAction Stop
            $isReparse = ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq [System.IO.FileAttributes]::ReparsePoint
        } catch { }

        if ($isReparse) {
            Write-Warn "$out 当前是一个符号链接/联接，将被删除并重建为实体目录。"
        } else {
            Write-Warn "$out 已存在，将合并/覆盖其中的文件。"
        }

        if (-not $Force -and -not $WhatIf) {
            $confirm = Read-Host "是否继续？(y/N)"
            if ($confirm -ne 'y' -and $confirm -ne 'Y') {
                Write-Info "已取消。"
                exit 0
            }
        }

        if (-not $WhatIf) {
            Write-Info "正在删除旧的 $out ..."
            if ($isReparse) {
                # symlink / junction → 直接删
                (Get-Item $out -Force).Delete()
            } else {
                Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }

    # 创建输出目录
    if (-not $WhatIf) {
        New-Item -ItemType Directory -Path $out -Force | Out-Null
    }

    # --- 1. 扫描伪 symlink ---
    Write-Info "正在扫描 $mt 中的远程 symlink ..."
    $fakeSymlinks = @()
    $allFiles = Get-ChildItem -Path $mt -Recurse -File -ErrorAction SilentlyContinue
    $totalFiles = $allFiles.Count
    Write-Detail "共 $totalFiles 个文件，逐个检测中..."
    $processed = 0
    foreach ($f in $allFiles) {
        $processed++
        if ($processed % 500 -eq 0) { Write-Detail "  已检测 $processed / $totalFiles ..." }
        if (Test-IsFakeSymlink $f.FullName) {
            $fakeSymlinks += $f
        }
    }
    Write-Host ""
    if ($fakeSymlinks.Count -eq 0) {
        Write-Success "未发现任何远程 symlink。直接使用 T 盘挂载即可，无需修复。"
        exit 0
    }
    Write-Info "发现 $($fakeSymlinks.Count) 个远程 symlink:"
    foreach ($fs in $fakeSymlinks) {
        $c = (Get-Content $fs.FullName -Raw).Trim()
        Write-Detail "$($fs.FullName)  ->  $c"
    }
    Write-Host ""

    # --- 2. 递归解析 ---
    Write-Info "递归解析每个 symlink，寻找最终实体文件..."
    $resolutionMap = @{}
    $failedList = @()
    foreach ($fs in $fakeSymlinks) {
        $result = Resolve-Chain -StartPath $fs.FullName
        if ($result.RealPath -and -not $result.Error) {
            $resolutionMap[$fs.FullName] = @{
                RealPath = $result.RealPath
                Chain    = $result.Chain
                IsDir    = (Test-Path $result.RealPath -PathType Container)
            }
            Write-Detail "OK  $($fs.Name)  ->  $($result.RealPath)"
            foreach ($hop in $result.Chain) { Write-Detail "      $hop" }
        } else {
            $failedList += @{ Path = $fs.FullName; Error = $result.Error }
            Write-Warn "FAIL $($fs.Name): $($result.Error)"
        }
    }
    Write-Host ""
    Write-Info "解析结果: 成功 $($resolutionMap.Count) / 失败 $($failedList.Count)"
    if ($failedList.Count -gt 0) {
        Write-Warn "以下 symlink 无法解析，将保留为原始文件（运行时可能仍然找不到）:"
        foreach ($f in $failedList) { Write-Detail "$($f.Path)  —  $($f.Error)" }
    }
    Write-Host ""

    # --- 3. 复制 ---
    Write-Info "正在从 $mt 复制实体文件到 $out ..."
    if (-not $WhatIf) {
        & robocopy $mt $out /E /COPYALL /R:1 /W:1 /NP /NFL /NDL 2>&1 | Out-Null
        $rc = $LASTEXITCODE
        if ($rc -ge 8) {
            Write-Warn "robocopy 部分文件复制失败 (exit $rc)，将继续处理。"
        } else {
            Write-Success "文件复制完成。"
        }
    }

    # --- 4. 替换伪 symlink 为真正的 Windows symlink ---
    Write-Info "将伪 symlink 替换为真正的 Windows 符号链接..."
    $replaced = 0
    $skipped = 0
    foreach ($tPath in $resolutionMap.Keys) {
        $info = $resolutionMap[$tPath]
        $relative = $tPath.Substring($mt.Length).TrimStart('\')
        $linkPath = Join-Path $out $relative
        $target = $info.RealPath
        Write-Detail "$linkPath  ->  $target"
        if (-not $WhatIf) {
            try {
                # 确保父目录存在
                $parent = [System.IO.Path]::GetDirectoryName($linkPath)
                if (-not (Test-Path $parent)) {
                    New-Item -ItemType Directory -Path $parent -Force | Out-Null
                }
                # 删除 robocopy 复制过来的伪 symlink 实体文件
                if (Test-Path $linkPath) {
                    Remove-Item $linkPath -Force -ErrorAction SilentlyContinue
                }
                if ($info.IsDir) {
                    cmd /c mklink /D "`"$linkPath`" `"$target`"" 2>&1 | Out-Null
                } else {
                    New-Item -ItemType SymbolicLink -Path $linkPath -Target $target -Force | Out-Null
                }
                $replaced++
            } catch {
                Write-Warn "创建失败: $linkPath — $_"
                $skipped++
            }
        } else {
            $replaced++
        }
    }
    Write-Host ""
    Write-Success "完成: 创建 $replaced 个符号链接"
    if ($skipped -gt 0) { Write-Warn "跳过 $skipped 个" }
    if ($failedList.Count -gt 0) { Write-Warn "$($failedList.Count) 个无法解析，保留为原始文件" }

    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Magenta
    if ($WhatIf) {
        Write-Info "预览完成。去掉 -WhatIf 以实际执行。"
    } else {
        Write-Success "修复完成！$out 已可用，程序直接读取即可。"
    }
    Write-Host "=============================================" -ForegroundColor Magenta
    Write-Host ""
}

Main
