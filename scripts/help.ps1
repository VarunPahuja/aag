# PowerShell equivalent of `make help`, for a `make` that shells out to cmd.exe
# instead of sh (the Makefile's own `help` target uses grep/sed).
# Usage: .\scripts\help.ps1

Get-Content Makefile | Select-String '^([a-zA-Z_-]+):.*?## (.*)$' | ForEach-Object {
    $name = $_.Matches[0].Groups[1].Value
    $desc = $_.Matches[0].Groups[2].Value
    "{0,-12} - {1}" -f $name, $desc
}
