param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = 'Stop'
$bytes = [IO.File]::ReadAllBytes($Path)

function RU16([byte[]]$b, [int]$o) { return [BitConverter]::ToUInt16($b, $o) }
function RU32([byte[]]$b, [int]$o) { return [BitConverter]::ToUInt32($b, $o) }

$FREE = 4294967295L
$LIMIT = 4294967290L  # >= this means special (DIFSECT/FATSECT/ENDOFCHAIN/FREESECT)

$secShift  = RU16 $bytes 30
$secSize   = 1 -shl $secShift
$miniShift = RU16 $bytes 32
$miniSize  = 1 -shl $miniShift
$numFat    = RU32 $bytes 44
$firstDir  = RU32 $bytes 48
$cutoff    = RU32 $bytes 56
$firstMini = RU32 $bytes 60
$firstDifat= RU32 $bytes 68

function SecOff([long]$s) { return 512 + ([long]$s * $secSize) }

# ---- DIFAT ----
$difat = New-Object System.Collections.Generic.List[long]
for ($i = 0; $i -lt 109; $i++) {
    $v = [long](RU32 $bytes (76 + $i * 4))
    if ($v -lt $LIMIT) { $difat.Add($v) }
}
$ds = [long]$firstDifat
$per = [int]($secSize / 4) - 1
while ($ds -lt $LIMIT -and $difat.Count -lt $numFat) {
    $off = SecOff $ds
    for ($i = 0; $i -lt $per; $i++) {
        $v = [long](RU32 $bytes ($off + $i * 4))
        if ($v -lt $LIMIT) { $difat.Add($v) }
    }
    $ds = [long](RU32 $bytes ($off + $per * 4))
}

# ---- FAT ----
$fat = New-Object System.Collections.Generic.List[long]
foreach ($fs in $difat) {
    $off = SecOff $fs
    for ($i = 0; $i -lt ($secSize / 4); $i++) { $fat.Add([long](RU32 $bytes ($off + $i * 4))) }
}

function ChainSectors([long]$start, $table) {
    $out = New-Object System.Collections.Generic.List[long]
    $cur = $start
    $guard = 0
    while ($cur -lt $LIMIT -and $cur -ge 0 -and $guard -lt 1000000) {
        $out.Add($cur)
        if ($cur -ge $table.Count) { break }
        $cur = $table[[int]$cur]
        $guard++
    }
    return $out
}

function ReadChain([long]$start, [long]$size) {
    $secs = ChainSectors $start $fat
    $buf = New-Object byte[] ($secs.Count * $secSize)
    $p = 0
    foreach ($s in $secs) {
        [Array]::Copy($bytes, (SecOff $s), $buf, $p, $secSize)
        $p += $secSize
    }
    if ($size -gt 0 -and $size -lt $buf.Length) {
        $r = New-Object byte[] $size; [Array]::Copy($buf, 0, $r, 0, $size); return $r
    }
    return $buf
}

# ---- Directory (linear scan over all dir sectors) ----
$dirBytes = ReadChain ([long]$firstDir) 0
$entries = @()
for ($o = 0; $o + 128 -le $dirBytes.Length; $o += 128) {
    $nameLen = RU16 $dirBytes ($o + 64)
    if ($nameLen -lt 2 -or $nameLen -gt 64) { continue }
    $name = [Text.Encoding]::Unicode.GetString($dirBytes, $o, $nameLen - 2)
    $type = $dirBytes[$o + 66]
    $start = [long](RU32 $dirBytes ($o + 116))
    $size = [long][BitConverter]::ToInt64($dirBytes, $o + 120)
    $entries += [pscustomobject]@{ Name = $name; Type = $type; Start = $start; Size = $size }
}

# ---- Mini stream ----
$root = $entries | Where-Object { $_.Type -eq 5 } | Select-Object -First 1
$miniStream = $null
$miniFat = $null
if ($root) {
    $miniStream = ReadChain $root.Start 0
    $mfBytes = ReadChain ([long]$firstMini) 0
    $miniFat = New-Object System.Collections.Generic.List[long]
    for ($i = 0; $i -lt ($mfBytes.Length / 4); $i++) { $miniFat.Add([long](RU32 $mfBytes ($i * 4))) }
}

function ReadStream($e) {
    if ($e.Size -lt $cutoff -and $miniStream) {
        $secs = ChainSectors $e.Start $miniFat
        $buf = New-Object byte[] ($secs.Count * $miniSize)
        $p = 0
        foreach ($s in $secs) {
            $src = [int]$s * $miniSize
            if ($src + $miniSize -le $miniStream.Length) { [Array]::Copy($miniStream, $src, $buf, $p, $miniSize) }
            $p += $miniSize
        }
        $n = [Math]::Min([long]$buf.Length, $e.Size)
        $r = New-Object byte[] $n; [Array]::Copy($buf, 0, $r, 0, $n); return $r
    }
    return ReadChain $e.Start $e.Size
}

function Inflate([byte[]]$data) {
    $ms = New-Object IO.MemoryStream(, $data)
    $ds = New-Object IO.Compression.DeflateStream($ms, [IO.Compression.CompressionMode]::Decompress)
    $out = New-Object IO.MemoryStream
    try { $ds.CopyTo($out) } catch { }
    return $out.ToArray()
}

# ---- FileHeader: compressed flag ----
$fh = $entries | Where-Object { $_.Name -eq 'FileHeader' } | Select-Object -First 1
$compressed = $true
if ($fh) {
    $fhb = ReadStream $fh
    $flags = RU32 $fhb 36
    $compressed = (($flags -band 1) -ne 0)
    if (($flags -band 2) -ne 0) { Write-Host '### WARNING: file is encrypted' }
}

# ---- Extract text from BodyText sections ----
$charCtrl = @(0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31)
$sections = $entries | Where-Object { $_.Type -eq 2 -and $_.Name -match '^Section\d+$' } | Sort-Object Name
$sb = New-Object Text.StringBuilder

foreach ($sec in $sections) {
    $raw = ReadStream $sec
    if ($compressed) { $raw = Inflate $raw }
    $p = 0
    while ($p + 4 -le $raw.Length) {
        $hdr = RU32 $raw $p; $p += 4
        $tag = [int]($hdr -band 0x3FF)
        $size = [int](($hdr -shr 20) -band 0xFFF)
        if ($size -eq 0xFFF) { $size = [int](RU32 $raw $p); $p += 4 }
        if ($p + $size -gt $raw.Length) { break }
        if ($tag -eq 67) {
            # HWPTAG_PARA_TEXT
            $i = 0
            while ($i + 1 -lt $size) {
                $c = [int](RU16 $raw ($p + $i))
                if ($c -lt 32) {
                    if ($charCtrl -contains $c) {
                        if ($c -eq 13 -or $c -eq 10) { [void]$sb.Append("`n") }
                        $i += 2
                    } else { $i += 16 }
                } else {
                    [void]$sb.Append([char]$c); $i += 2
                }
            }
            [void]$sb.Append("`n")
        }
        $p += $size
    }
}

$sb.ToString()
